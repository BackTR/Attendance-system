"""Attendance analysis service.

Owns ALL business rules for lateness, early leave, work duration, and
daily attendance status, per PROJECT_CONTEXT.md Section 9. Repositories
only fetch/persist data; this Service decides what the numbers mean
(AI_RULES.md Rule 4: business logic only lives in Service).
"""

from datetime import date, datetime, time

from config.constants import FRIDAY_WEEKDAY_INDEX
from core.enums.attendance import CheckInStatus, CheckOutStatus
from core.logger import logger
from models.app_settings import AppSettingsModel
from models.attendance import AttendanceModel
from repositories.attendance_repository import AttendanceRepository
from repositories.settings_repository import SettingsRepository

#const
_TIME_DIFF_ANCHOR_DATE = date(2000, 1, 1)
class AttendanceService:
    """Calculates lateness, early leave, and work duration for attendance records."""

    def __init__(
        self,
        attendance_repo: AttendanceRepository,
        settings_repo: SettingsRepository,
    ) -> None:
        """Initialize the service with required repositories.

        Args:
            attendance_repo: Repository for reading/writing attendance rows.
            settings_repo: Repository for reading working-hour settings.
        """
        self.attendance_repo = attendance_repo
        self.settings_repo = settings_repo

    def analyze_pending(self) -> int:
        """Analyze every attendance record that hasn't been analyzed yet.

        Returns:
            Number of records analyzed.
        """
        settings = self._get_or_create_settings()
        pending = self.attendance_repo.get_unanalyzed()

        for attendance in pending:
            self._analyze_one(attendance, settings)

        logger.info(f"{len(pending)} data absensi berhasil dianalisis")
        return len(pending)

    def _analyze_one(
        self, attendance: AttendanceModel, settings: AppSettingsModel
    ) -> AttendanceModel:
        """Calculate and store lateness/early-leave/duration for one record."""
        work_end = self.resolve_work_end(
            attendance.tanggal, settings.work_end, settings.friday_end
        )

        menit_telat, status_masuk = self.calculate_late(
            attendance.jam_masuk, settings.work_start, settings.tolerance_late
        )
        menit_pulang_cepat, status_keluar = self.calculate_early_leave(
            attendance.jam_keluar, work_end, settings.tolerance_leave
        )
        durasi_kerja = self.calculate_work_duration(
            attendance.jam_masuk, attendance.jam_keluar
        )

        attendance.status_masuk = status_masuk.value
        attendance.status_keluar = status_keluar.value
        attendance.menit_telat = menit_telat
        attendance.menit_pulang_cepat = menit_pulang_cepat
        attendance.durasi_kerja = durasi_kerja

        return self.attendance_repo.update(attendance)

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