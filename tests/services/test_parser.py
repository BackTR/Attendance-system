"""Tests for ExcelImportService (services/parser.py)."""

from datetime import date, time

import pandas as pd
import pytest

from core.exceptions import InvalidExcelFormatException
from models.employee import EmployeeModel
from repositories.employee_repository import EmployeeRepository
from services.parser import ExcelImportService


def _write_excel(tmp_path, rows):
    path = tmp_path / "test.xlsx"
    pd.DataFrame(rows).to_excel(path, index=False)
    return str(path)


def test_import_skips_row_with_missing_employee(db_session, tmp_path):
    file_path = _write_excel(
        tmp_path,
        [
            {
                "employee_code": "GHOST",
                "tanggal": date(2026, 7, 27),
                "jam_masuk": time(7, 30),
                "jam_keluar": time(15, 30),
            }
        ],
    )

    result = ExcelImportService(db_session).import_from_excel(file_path)

    assert result.imported == 0
    assert result.skipped_employee_not_found == ["GHOST"]


def test_import_raises_on_missing_columns(tmp_path):
    path = tmp_path / "bad.xlsx"
    pd.DataFrame([{"foo": "bar"}]).to_excel(path, index=False)

    with pytest.raises(InvalidExcelFormatException):
        # session=None is safe here: column validation raises before any
        # repository/session access happens.
        ExcelImportService(None).import_from_excel(str(path))


def test_import_skips_row_with_invalid_date(db_session, tmp_path):
    EmployeeRepository(db_session).create(
        EmployeeModel(employee_code="EMP001", nama="Budi")
    )
    file_path = _write_excel(
        tmp_path,
        [
            {
                "employee_code": "EMP001",
                "tanggal": "TANGGAL_RUSAK",
                "jam_masuk": time(7, 30),
                "jam_keluar": time(15, 30),
            }
        ],
    )

    result = ExcelImportService(db_session).import_from_excel(file_path)

    assert result.imported == 0
    assert len(result.skipped_invalid_row) == 1


def test_import_detects_duplicate_employee_and_date(db_session, tmp_path):
    EmployeeRepository(db_session).create(
        EmployeeModel(employee_code="EMP001", nama="Budi")
    )
    file_path = _write_excel(
        tmp_path,
        [
            {
                "employee_code": "EMP001",
                "tanggal": date(2026, 7, 27),
                "jam_masuk": time(7, 30),
                "jam_keluar": time(15, 30),
            },
            {
                "employee_code": "EMP001",
                "tanggal": date(2026, 7, 27),
                "jam_masuk": time(7, 45),
                "jam_keluar": time(15, 30),
            },
        ],
    )

    result = ExcelImportService(db_session).import_from_excel(file_path)

    assert result.imported == 1
    assert len(result.skipped_duplicate) == 1