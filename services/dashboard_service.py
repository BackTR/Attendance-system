"""Dashboard aggregation service.

Owns all statistics/recap logic (Rule 4: "Rekap Pegawai" is Service
business logic, not something the Dashboard page computes itself).
The Dashboard page only calls this Service and renders the result.
"""

from dataclasses import dataclass
from datetime import date

from core.enums.attendance import CheckInStatus, CheckOutStatus
from models.attendance import AttendanceModel
from repositories.attendance_repository import AttendanceRepository
from repositories.employee_repository import EmployeeRepository


@dataclass
class PeriodSummary:
    """Aggregate attendance statistics for a date range."""

    total_records: int = 0
    total_hadir: int = 0
    total_tidak_hadir: int = 0
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
            PeriodSummary with totals for hadir/telat/pulang cepat/tidak hadir.
        """
        records = self.attendance_repo.get_by_period(start_date, end_date)
        summary = PeriodSummary(total_records=len(records))

        durations: list[int] = []
        for record in records:
            if record.status_masuk == CheckInStatus.MISSING.value and (
                record.status_keluar == CheckOutStatus.MISSING.value
            ):
                summary.total_tidak_hadir += 1
            else:
                summary.total_hadir += 1

            if record.status_masuk == CheckInStatus.LATE.value:
                summary.total_telat += 1

            if record.status_keluar == CheckOutStatus.EARLY.value:
                summary.total_pulang_cepat += 1

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
                is_absent = record.status_masuk == CheckInStatus.MISSING.value and (
                    record.status_keluar == CheckOutStatus.MISSING.value
                )
                if is_absent:
                    recap.total_tidak_hadir += 1
                else:
                    recap.total_hadir += 1
                if record.status_masuk == CheckInStatus.LATE.value:
                    recap.total_telat += 1
                if record.status_keluar == CheckOutStatus.EARLY.value:
                    recap.total_pulang_cepat += 1
            recaps.append(recap)

        return recaps