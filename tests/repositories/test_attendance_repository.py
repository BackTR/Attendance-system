"""Tests for AttendanceRepository."""

from datetime import date

from models.attendance import AttendanceModel
from models.employee import EmployeeModel
from repositories.attendance_repository import AttendanceRepository
from repositories.employee_repository import EmployeeRepository


def _make_employee(db_session):
    return EmployeeRepository(db_session).create(
        EmployeeModel(employee_code="EMP001", nama="Budi Santoso")
    )


def test_create_and_get_by_employee_and_date(db_session):
    employee = _make_employee(db_session)
    repo = AttendanceRepository(db_session)
    repo.create(
        AttendanceModel(
            employee_id=employee.id,
            tanggal=date(2026, 7, 27),
            hari="Senin",
            sumber_data="MANUAL",
        )
    )

    found = repo.get_by_employee_and_date(employee.id, date(2026, 7, 27))

    assert found is not None
    assert found.hari == "Senin"


def test_get_by_period_filters_correctly(db_session):
    employee = _make_employee(db_session)
    repo = AttendanceRepository(db_session)
    repo.create(
        AttendanceModel(
            employee_id=employee.id,
            tanggal=date(2026, 7, 27),
            hari="Senin",
            sumber_data="MANUAL",
        )
    )
    repo.create(
        AttendanceModel(
            employee_id=employee.id,
            tanggal=date(2026, 8, 1),
            hari="Sabtu",
            sumber_data="MANUAL",
        )
    )

    july_only = repo.get_by_period(date(2026, 7, 1), date(2026, 7, 31))

    assert len(july_only) == 1
    assert july_only[0].tanggal == date(2026, 7, 27)


def test_get_unanalyzed_only_returns_rows_without_status(db_session):
    employee = _make_employee(db_session)
    repo = AttendanceRepository(db_session)
    repo.create(
        AttendanceModel(
            employee_id=employee.id,
            tanggal=date(2026, 7, 27),
            hari="Senin",
            sumber_data="MANUAL",
            status_masuk=None,
        )
    )
    repo.create(
        AttendanceModel(
            employee_id=employee.id,
            tanggal=date(2026, 7, 28),
            hari="Selasa",
            sumber_data="MANUAL",
            status_masuk="ON_TIME",
        )
    )

    pending = repo.get_unanalyzed()

    assert len(pending) == 1
    assert pending[0].tanggal == date(2026, 7, 27)