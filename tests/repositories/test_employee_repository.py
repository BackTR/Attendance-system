"""Tests for EmployeeRepository."""

from models.employee import EmployeeModel
from repositories.employee_repository import EmployeeRepository


def test_create_and_get_by_code(db_session):
    repo = EmployeeRepository(db_session)
    repo.create(EmployeeModel(employee_code="EMP001", nama="Budi Santoso"))

    found = repo.get_by_code("EMP001")

    assert found is not None
    assert found.nama == "Budi Santoso"


def test_get_by_code_returns_none_when_missing(db_session):
    repo = EmployeeRepository(db_session)

    found = repo.get_by_code("NOT_EXIST")

    assert found is None


def test_get_all_active_excludes_inactive(db_session):
    repo = EmployeeRepository(db_session)
    repo.create(EmployeeModel(employee_code="EMP001", nama="Aktif", aktif=True))
    repo.create(EmployeeModel(employee_code="EMP002", nama="Nonaktif", aktif=False))

    active = repo.get_all_active()

    assert len(active) == 1
    assert active[0].employee_code == "EMP001"