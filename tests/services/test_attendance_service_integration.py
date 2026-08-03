"""Integration test: AttendanceService.analyze_pending against a real DB session."""

from datetime import date, time

from models.attendance import AttendanceModel
from models.employee import EmployeeModel
from repositories.attendance_repository import AttendanceRepository
from repositories.employee_repository import EmployeeRepository
from repositories.settings_repository import SettingsRepository
from services.attendance_service import AttendanceService


def test_analyze_pending_updates_status_and_duration(db_session):
    employee = EmployeeRepository(db_session).create(
        EmployeeModel(employee_code="EMP001", nama="Budi Santoso")
    )
    attendance_repo = AttendanceRepository(db_session)
    attendance_repo.create(
        AttendanceModel(
            employee_id=employee.id,
            tanggal=date(2026, 7, 27),  # Monday
            hari="Senin",
            jam_masuk=time(7, 45),
            jam_keluar=time(15, 30),
            sumber_data="MANUAL",
        )
    )

    service = AttendanceService(attendance_repo, SettingsRepository(db_session))
    processed = service.analyze_pending()

    assert processed == 1

    updated = attendance_repo.get_by_employee_and_date(employee.id, date(2026, 7, 27))
    assert updated.status_masuk == "LATE"
    assert updated.menit_telat == 15
    assert updated.status_keluar == "NORMAL"
    assert updated.durasi_kerja == 465


def test_analyze_pending_marks_absent_day_as_missing(db_session):
    employee = EmployeeRepository(db_session).create(
        EmployeeModel(employee_code="EMP001", nama="Budi Santoso")
    )
    attendance_repo = AttendanceRepository(db_session)
    attendance_repo.create(
        AttendanceModel(
            employee_id=employee.id,
            tanggal=date(2026, 8, 1),
            hari="Sabtu",
            jam_masuk=None,
            jam_keluar=None,
            sumber_data="MANUAL",
        )
    )

    service = AttendanceService(attendance_repo, SettingsRepository(db_session))
    service.analyze_pending()

    updated = attendance_repo.get_by_employee_and_date(employee.id, date(2026, 8, 1))
    assert updated.status_masuk == "MISSING"
    assert updated.status_keluar == "MISSING"
    assert updated.durasi_kerja is None