"""Excel import service: parsing, validation, and persisting attendance data.

NOTE ON FILE LOCATION: AI_RULES.md specifies this file as
`services/parser.py`, while CODING_STANDARDS.md specifies
`services/import_service.py`. Per the Final Rule present in both
documents (AI_RULES.md outranks CODING_STANDARDS.md), this module lives
at `services/parser.py`.

This service ONLY reads, validates, and stores raw attendance rows
(jam_masuk / jam_keluar / hari). It does NOT calculate lateness or
early-leave status — that is business logic owned by the Attendance
Analyzer service (Sprint 5), per AI_RULES.md Rule 4.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time

import pandas as pd
from sqlalchemy.orm import Session

from config.constants import EXCEL_REQUIRED_COLUMNS
from core.enums.weekday import Weekday
from core.exceptions import InvalidExcelFormatException
from core.logger import logger
from models.attendance import AttendanceModel
from repositories.attendance_repository import AttendanceRepository
from repositories.employee_repository import EmployeeRepository


@dataclass
class ImportResult:
    """Summary of an Excel import run."""

    total_rows: int = 0
    imported: int = 0
    skipped_employee_not_found: list[str] = field(default_factory=list)
    skipped_invalid_row: list[str] = field(default_factory=list)
    skipped_duplicate: list[str] = field(default_factory=list)


class ExcelImportService:
    """Reads an attendance Excel file, validates it, and persists rows."""

    def __init__(self, session: Session) -> None:
        """Initialize the service with an active database session.

        Args:
            session: Active SQLAlchemy session (see core.database.get_session).
        """
        self.session = session
        self.employee_repo = EmployeeRepository(session)
        self.attendance_repo = AttendanceRepository(session)

    def import_from_excel(self, file_path: str) -> ImportResult:
        """Read, validate, and persist attendance data from an Excel file.

        Args:
            file_path: Path to the uploaded .xlsx/.xls file.

        Returns:
            ImportResult summarizing how many rows were imported/skipped.

        Raises:
            InvalidExcelFormatException: If the file cannot be read or is
                missing required columns.
        """
        df = self._read_excel(file_path)
        self._validate_columns(df)

        result = ImportResult(total_rows=len(df))

        for row_index, row in df.iterrows():
            excel_row_number = row_index + 2  # +1 for header, +1 for 0-index
            try:
                self._import_row(row, result, excel_row_number)
            except InvalidExcelFormatException as exc:
                logger.warning(f"Baris {excel_row_number} dilewati: {exc}")
                result.skipped_invalid_row.append(f"Baris {excel_row_number}: {exc}")

        logger.info(
            f"Import selesai: {result.imported}/{result.total_rows} baris berhasil"
        )
        return result

    def _import_row(
        self, row: "pd.Series", result: ImportResult, excel_row_number: int
    ) -> None:
        """Validate and persist a single attendance row."""
        employee_code = str(row["employee_code"]).strip()
        employee = self.employee_repo.get_by_code(employee_code)

        if employee is None:
            logger.warning(f"Baris {excel_row_number}: employee_code tidak ditemukan")
            result.skipped_employee_not_found.append(employee_code)
            return

        tanggal = self._parse_date(row["tanggal"], excel_row_number)

        existing = self.attendance_repo.get_by_employee_and_date(
            employee.id, tanggal
        )
        if existing is not None:
            logger.warning(
                f"Baris {excel_row_number}: data absensi {employee_code} "
                f"pada {tanggal} sudah ada, dilewati"
            )
            result.skipped_duplicate.append(f"{employee_code} @ {tanggal}")
            return

        jam_masuk = self._parse_time(row["jam_masuk"])
        jam_keluar = self._parse_time(row["jam_keluar"])
        hari = Weekday.from_index(tanggal.weekday()).value

        attendance = AttendanceModel(
            employee_id=employee.id,
            tanggal=tanggal,
            hari=hari,
            jam_masuk=jam_masuk,
            jam_keluar=jam_keluar,
            sumber_data="EXCEL_IMPORT",
        )
        self.attendance_repo.create(attendance)
        result.imported += 1

    def _read_excel(self, file_path: str) -> pd.DataFrame:
        """Read the Excel file into a DataFrame."""
        try:
            return pd.read_excel(file_path)
        except Exception as exc:
            logger.exception(exc)
            raise InvalidExcelFormatException(
                "Gagal membaca file Excel. Pastikan format .xlsx/.xls valid."
            ) from exc

    def _validate_columns(self, df: pd.DataFrame) -> None:
        """Ensure the DataFrame contains all required columns."""
        missing = set(EXCEL_REQUIRED_COLUMNS) - set(df.columns)
        if missing:
            raise InvalidExcelFormatException(
                f"Kolom wajib tidak ditemukan: {sorted(missing)}"
            )

    def _parse_date(self, value: object, excel_row_number: int) -> date:
        """Parse a cell value into a date, raising on invalid input."""
        try:
            return pd.to_datetime(value).date()
        except Exception as exc:
            raise InvalidExcelFormatException(
                f"tanggal tidak valid ({value!r})"
            ) from exc

    def _parse_time(self, value: object) -> time | None:
        """Parse a cell value into a time object, or None if empty/missing."""
        if pd.isna(value):
            return None
        if isinstance(value, time):
            return value
        if isinstance(value, datetime):
            return value.time()
        try:
            return pd.to_datetime(str(value)).time()
        except Exception:
            return None
