"""Dashboard aggregation service.

Owns all statistics/recap logic (Rule 4: "Rekap Pegawai" is Service
business logic, not something the Dashboard page computes itself).
The Dashboard page only calls this Service and renders the result.

Uses AttendanceModel.status_hari (set by AttendanceService) as the
single source of truth for whether a day counts as hadir/tidak
hadir/libur/lembur, instead of re-deriving it from status_masuk/
status_keluar -- that avoids counting weekends/holidays as "tidak
hadir" and keeps this logic in one place.
"""

from dataclasses import dataclass
from datetime import date

from core.enums.attendance import AttendanceStatus, CheckInStatus, CheckOutStatus
from models.attendance import AttendanceModel
from repositories.attendance_repository import AttendanceRepository
from repositories.employee_repository import EmployeeRepository


@dataclass
class PeriodSummary:
    """Aggregate attendance statistics for a date range."""

    total_records: int = 0
    total_hadir: int = 0
    total_tidak_hadir: int = 0
    total_libur: int = 0
    total_lembur: int = 0
    total_telat: int = 0
    total_pulang_cepat: int = 0
    rata_rata_durasi_menit: float = 0.0


@dataclass
class EmployeeRecap:
    """Per-employee attendance recap for a date range."""

    employee_code: str
    nama: str
    total_hadir: int = 0
    total_telat: int = 0
    total_pulang_cepat: int = 0
    total_tidak_hadir: int = 0
    total_libur: int = 0
    total_lembur: int = 0


class DashboardService:
    """Computes summary statistics and per-employee recaps for the dashboard."""

    def __init__(
        self,
        attendance_repo: AttendanceRepository,
        employee_repo: EmployeeRepository,
    ) -> None:
        """Initialize the service with required repositories.

        Args:
            attendance_repo: Repository for reading attendance rows.
            employee_repo: Repository for reading employee rows.
        """
        self.attendance_repo = attendance_repo
        self.employee_repo = employee_repo

    def get_period_summary(self, start_date: date, end_date: date) -> PeriodSummary:
        """Compute aggregate attendance statistics for a date range.

        Args:
            start_date: Start of the period (inclusive).
            end_date: End of the period (inclusive).

        Returns:
            PeriodSummary with totals for hadir/telat/pulang cepat/tidak
            hadir/libur/lembur.
        """
        records = self.attendance_repo.get_by_period(start_date, end_date)
        summary = PeriodSummary(total_records=len(records))

        durations: list[int] = []
        for record in records:
            self._tally(summary, record)
            if record.durasi_kerja is not None:
                durations.append(record.durasi_kerja)

        if durations:
            summary.rata_rata_durasi_menit = sum(durations) / len(durations)

        return summary

    def get_employee_recap(
        self, start_date: date, end_date: date
    ) -> list[EmployeeRecap]:
        """Compute per-employee attendance recap for a date range.

        Args:
            start_date: Start of the period (inclusive).
            end_date: End of the period (inclusive).

        Returns:
            List of EmployeeRecap, one per active employee.
        """
        records = self.attendance_repo.get_by_period(start_date, end_date)
        by_employee: dict[int, list[AttendanceModel]] = {}
        for record in records:
            by_employee.setdefault(record.employee_id, []).append(record)

        recaps: list[EmployeeRecap] = []
        for employee in self.employee_repo.get_all_active():
            employee_records = by_employee.get(employee.id, [])
            recap = EmployeeRecap(
                employee_code=employee.employee_code, nama=employee.nama
            )
            for record in employee_records:
                self._tally(recap, record)
            recaps.append(recap)

        return recaps

    def _tally(self, target: "PeriodSummary | EmployeeRecap", record: AttendanceModel) -> None:
        """Increment the right counters on a summary/recap object for one record."""
        if record.status_hari == AttendanceStatus.LIBUR.value:
            target.total_libur += 1
        elif record.status_hari == AttendanceStatus.LEMBUR.value:
            target.total_lembur += 1
        elif record.status_hari == AttendanceStatus.ABSENT.value:
            target.total_tidak_hadir += 1
        else:
            # PRESENT or INCOMPLETE both count as "hadir" (they attended).
            target.total_hadir += 1

        if record.status_masuk == CheckInStatus.LATE.value:
            target.total_telat += 1
        if record.status_keluar == CheckOutStatus.EARLY.value:
            target.total_pulang_cepat += 1