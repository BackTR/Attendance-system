"""Attendance analysis service.

Owns ALL business rules for lateness, early leave, work duration, and
daily attendance status, per PROJECT_CONTEXT.md Section 9. Repositories
only fetch/persist data; this Service decides what the numbers mean
(AI_RULES.md Rule 4: business logic only lives in Service).

Day-status model (status_hari): every attendance record gets exactly
one high-level label so reports don't require manual cross-checking:
  - PRESENT    : work day, employee attended (may still be late/early)
  - ABSENT     : work day, no check-in and no check-out at all
  - INCOMPLETE : work day, only one of check-in/check-out recorded
  - LIBUR      : weekend or declared holiday, employee did not attend
  - LEMBUR     : weekend or declared holiday, employee DID attend
    (no lateness/early-leave penalty applies, since there's no official
    schedule on a day off)
"""

from datetime import date, datetime, time

from config.constants import FRIDAY_WEEKDAY_INDEX, WEEKEND_WEEKDAY_INDEXES
from core.enums.attendance import AttendanceStatus, CheckInStatus, CheckOutStatus
from core.logger import logger
from models.app_settings import AppSettingsModel
from models.attendance import AttendanceModel
from repositories.attendance_repository import AttendanceRepository
from repositories.holiday_repository import HolidayRepository
from repositories.settings_repository import SettingsRepository

_TIME_DIFF_ANCHOR_DATE = date(2000, 1, 1)


class AttendanceService:
    """Calculates lateness, early leave, work duration, and day status."""

    def __init__(
        self,
        attendance_repo: AttendanceRepository,
        settings_repo: SettingsRepository,
        holiday_repo: HolidayRepository | None = None,
    ) -> None:
        """Initialize the service with required repositories.

        Args:
            attendance_repo: Repository for reading/writing attendance rows.
            settings_repo: Repository for reading working-hour settings.
            holiday_repo: Repository for reading declared holidays. Only
                needed for analyze_pending()/reanalyze_all(); the pure
                calculate_* methods don't use it, so it may be omitted
                (e.g. in unit tests) when analysis isn't being run.
        """
        self.attendance_repo = attendance_repo
        self.settings_repo = settings_repo
        self.holiday_repo = holiday_repo

    def analyze_pending(self) -> int:
        """Analyze every attendance record that hasn't been analyzed yet.

        Returns:
            Number of records analyzed.
        """
        pending = self.attendance_repo.get_unanalyzed()
        return self._analyze_records(pending, log_label="dianalisis")

    def reanalyze_all(self) -> int:
        """Force re-analysis of every attendance record.

        Use this after declaring/removing holidays or changing working-hour
        settings, since analyze_pending() only touches never-analyzed rows.

        Returns:
            Number of records re-analyzed.
        """
        all_records = self.attendance_repo.get_all()
        return self._analyze_records(all_records, log_label="dianalisis ulang")

    def _analyze_records(
        self, records: list[AttendanceModel], log_label: str
    ) -> int:
        """Shared analysis loop used by both analyze_pending and reanalyze_all."""
        if not records:
            return 0

        settings = self._get_or_create_settings()
        holiday_dates = self._get_holiday_dates(records)

        for attendance in records:
            self._analyze_one(attendance, settings, holiday_dates)

        logger.info(f"{len(records)} data absensi berhasil {log_label}")
        return len(records)

    def _analyze_one(
        self,
        attendance: AttendanceModel,
        settings: AppSettingsModel,
        holiday_dates: set[date],
    ) -> AttendanceModel:
        """Calculate and store status/lateness/duration for one record."""
        has_data = attendance.jam_masuk is not None or attendance.jam_keluar is not None
        is_libur = self._is_libur(attendance.tanggal, holiday_dates)

        if is_libur:
            self._apply_libur_or_lembur(attendance, has_data)
        elif not has_data:
            self._apply_absent(attendance)
        else:
            self._apply_present(attendance, settings)

        return self.attendance_repo.update(attendance)

    def _apply_libur_or_lembur(
        self, attendance: AttendanceModel, has_data: bool
    ) -> None:
        """Mark a weekend/holiday record as LIBUR (no attendance) or LEMBUR."""
        attendance.status_masuk = None
        attendance.status_keluar = None
        attendance.menit_telat = 0
        attendance.menit_pulang_cepat = 0

        if has_data:
            attendance.status_hari = AttendanceStatus.LEMBUR.value
            attendance.durasi_kerja = self.calculate_work_duration(
                attendance.jam_masuk, attendance.jam_keluar
            )
        else:
            attendance.status_hari = AttendanceStatus.LIBUR.value
            attendance.durasi_kerja = None

    def _apply_absent(self, attendance: AttendanceModel) -> None:
        """Mark a work-day record with no check-in/out at all as ABSENT."""
        attendance.status_hari = AttendanceStatus.ABSENT.value
        attendance.status_masuk = CheckInStatus.MISSING.value
        attendance.status_keluar = CheckOutStatus.MISSING.value
        attendance.menit_telat = 0
        attendance.menit_pulang_cepat = 0
        attendance.durasi_kerja = None

    def _apply_present(
        self, attendance: AttendanceModel, settings: AppSettingsModel
    ) -> None:
        """Calculate lateness/early-leave/duration for a normal work day."""
        work_end = self.resolve_work_end(
            attendance.tanggal, settings.work_end, settings.friday_end
        )

        menit_telat, status_masuk = self.calculate_late(
            attendance.jam_masuk, settings.work_start, settings.tolerance_late
        )
        menit_pulang_cepat, status_keluar = self.calculate_early_leave(
            attendance.jam_keluar, work_end, settings.tolerance_leave
        )

        attendance.status_masuk = status_masuk.value
        attendance.status_keluar = status_keluar.value
        attendance.menit_telat = menit_telat
        attendance.menit_pulang_cepat = menit_pulang_cepat
        attendance.durasi_kerja = self.calculate_work_duration(
            attendance.jam_masuk, attendance.jam_keluar
        )
        attendance.status_hari = (
            AttendanceStatus.INCOMPLETE.value
            if attendance.jam_masuk is None or attendance.jam_keluar is None
            else AttendanceStatus.PRESENT.value
        )

    def calculate_late(
        self, check_in: time | None, work_start: time, tolerance_minutes: int
    ) -> tuple[int, CheckInStatus]:
        """Calculate late minutes and check-in status.

        Args:
            check_in: Employee's actual check-in time (None if absent).
            work_start: Official work start time.
            tolerance_minutes: Grace period before LATE is triggered.

        Returns:
            Tuple of (late_minutes, CheckInStatus).
        """
        if check_in is None:
            return 0, CheckInStatus.MISSING

        diff_minutes = self._time_diff_minutes(check_in, work_start)
        if diff_minutes > tolerance_minutes:
            return diff_minutes, CheckInStatus.LATE
        return 0, CheckInStatus.ON_TIME

    def calculate_early_leave(
        self, check_out: time | None, work_end: time, tolerance_minutes: int
    ) -> tuple[int, CheckOutStatus]:
        """Calculate early-leave minutes and check-out status.

        Args:
            check_out: Employee's actual check-out time (None if absent).
            work_end: Official work end time for that day (weekday/Friday).
            tolerance_minutes: Grace period before EARLY is triggered.

        Returns:
            Tuple of (early_leave_minutes, CheckOutStatus).
        """
        if check_out is None:
            return 0, CheckOutStatus.MISSING

        diff_minutes = self._time_diff_minutes(work_end, check_out)
        if diff_minutes > tolerance_minutes:
            return diff_minutes, CheckOutStatus.EARLY
        return 0, CheckOutStatus.NORMAL

    def calculate_work_duration(
        self, check_in: time | None, check_out: time | None
    ) -> int | None:
        """Calculate total worked minutes between check-in and check-out.

        Args:
            check_in: Employee's actual check-in time.
            check_out: Employee's actual check-out time.

        Returns:
            Worked minutes, or None if either time is missing.
        """
        if check_in is None or check_out is None:
            return None
        return self._time_diff_minutes(check_out, check_in)

    def resolve_work_end(
        self, tanggal: date, work_end: time, friday_end: time
    ) -> time:
        """Resolve the applicable work-end time based on weekday.

        Args:
            tanggal: The attendance date.
            work_end: Standard (Mon-Thu) work end time.
            friday_end: Friday-specific work end time.

        Returns:
            The applicable work-end time for that date.
        """
        if tanggal.weekday() == FRIDAY_WEEKDAY_INDEX:
            return friday_end
        return work_end

    def _is_libur(self, tanggal: date, holiday_dates: set[date]) -> bool:
        """Check whether a date is a weekend or a declared holiday."""
        return tanggal.weekday() in WEEKEND_WEEKDAY_INDEXES or tanggal in holiday_dates

    def _get_holiday_dates(self, records: list[AttendanceModel]) -> set[date]:
        """Fetch declared holidays covering the date range of these records."""
        if self.holiday_repo is None or not records:
            return set()
        dates = [r.tanggal for r in records]
        holidays = self.holiday_repo.get_by_period(min(dates), max(dates))
        return {h.tanggal for h in holidays}

    def _get_or_create_settings(self) -> AppSettingsModel:
        """Fetch the settings row, creating a default one if none exists."""
        settings = self.settings_repo.get()
        if settings is None:
            logger.info("Belum ada settings, membuat default")
            settings = self.settings_repo.create(AppSettingsModel())
        return settings

    @staticmethod
    def _time_diff_minutes(later: time, earlier: time) -> int:
        """Return the (possibly negative) minute difference: later - earlier."""
        delta = datetime.combine(_TIME_DIFF_ANCHOR_DATE, later) - datetime.combine(
            _TIME_DIFF_ANCHOR_DATE, earlier
        )
        return int(delta.total_seconds() // 60)