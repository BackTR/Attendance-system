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
from models.employee import EmployeeModel
from repositories.attendance_repository import AttendanceRepository
from repositories.employee_repository import EmployeeRepository
from services.employee_service import EmployeeService
from utils.excel_scan_helpers import (
    SCAN_DAY_COLUMNS,
    build_date_lookup,
    extract_header,
    extract_month_day,
    extract_report_period,
    is_date_row,
    is_header_row,
    is_time_row,
    parse_time_range,
)

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

@dataclass
class RawScanImportResult:
    """Summary of a raw fingerprint-scan Excel import run."""

    total_employees: int = 0
    imported: int = 0
    skipped_duplicate: list[str] = field(default_factory=list)
    new_employees_created: list[str] = field(default_factory=list)


class RawScanImportService:
    """Imports the fingerprint-machine 'Data Scan Karyawan' export format.

    Unlike ExcelImportService (clean employee_code/tanggal/jam_masuk/
    jam_keluar columns), this format is a pivoted per-employee grid with
    merged header cells and embedded print-page footers. This format has
    no employee_code -- employees are matched by exact name, and any
    unmatched name is auto-registered with a generated code (explicit
    product decision, since manually pre-registering every employee from
    a machine export is impractical).
    """

    def __init__(self, session: Session) -> None:
        """Initialize the service with an active database session.

        Args:
            session: Active SQLAlchemy session (see core.database.get_session).
        """
        self.session = session
        self.employee_repo = EmployeeRepository(session)
        self.attendance_repo = AttendanceRepository(session)
        self.employee_service = EmployeeService(self.employee_repo)

    def import_from_excel(self, file_path: str) -> RawScanImportResult:
        """Read, parse, and persist attendance data from a raw scan export.

        Args:
            file_path: Path to the uploaded .xlsx/.xls file.

        Returns:
            RawScanImportResult summarizing employees found and rows imported.

        Raises:
            InvalidExcelFormatException: If the file can't be read or the
                report period header can't be found.
        """
        rows = self._read_grid(file_path)

        all_text = [str(v) for row in rows for v in row if isinstance(v, str)]
        period = extract_report_period(all_text)
        if period is None:
            raise InvalidExcelFormatException(
                "Format periode laporan tidak ditemukan "
                "(diharapkan format 'Dari DD-MM-YYYY s/d DD-MM-YYYY')."
            )
        date_lookup = build_date_lookup(*period)

        result = RawScanImportResult()
        for employee_name, day_records in self._extract_employee_blocks(
            rows, date_lookup
        ):
            result.total_employees += 1
            employee = self._get_or_create_employee(employee_name, result)

            for tanggal, jam_masuk, jam_keluar in day_records:
                self._save_attendance(
                    employee, tanggal, jam_masuk, jam_keluar, result
                )

        logger.info(
            f"Raw scan import selesai: {result.total_employees} pegawai, "
            f"{result.imported} data absensi baru, "
            f"{len(result.new_employees_created)} pegawai baru didaftarkan"
        )
        return result

    def _read_grid(self, file_path: str) -> list[tuple]:
        """Read the raw Excel grid (no header row, raw cell values)."""
        try:
            df = pd.read_excel(file_path, header=None)
        except Exception as exc:
            logger.exception(exc)
            raise InvalidExcelFormatException("Gagal membaca file Excel.") from exc
        return [tuple(row) for row in df.itertuples(index=False, name=None)]

    def _extract_employee_blocks(
        self, rows: list[tuple], date_lookup: dict[str, date]
    ) -> list[tuple[str, list[tuple]]]:
        """Split the grid into (employee_name, day_records) blocks.

        Robust to blank rows and embedded print-page footers appearing
        between date/time row pairs -- only header/date/time rows are
        meaningful, everything else is skipped.
        """
        blocks: list[tuple[str, list[tuple]]] = []
        current_name: str | None = None
        current_records: list[tuple] = []
        pending_date_row: tuple | None = None

        for row in rows:
            if is_header_row(row):
                if current_name is not None:
                    blocks.append((current_name, current_records))
                _, current_name = extract_header(row)
                current_records = []
                pending_date_row = None
                continue

            if is_date_row(row):
                pending_date_row = row
                continue

            if is_time_row(row) and pending_date_row is not None:
                current_records.extend(
                    self._pair_date_time_row(pending_date_row, row, date_lookup)
                )
                pending_date_row = None

        if current_name is not None:
            blocks.append((current_name, current_records))

        return blocks

    def _pair_date_time_row(
        self, date_row: tuple, time_row: tuple, date_lookup: dict[str, date]
    ) -> list[tuple[date, time | None, time | None]]:
        """Zip one date-row with its time-row at the fixed day-slot columns."""
        records: list[tuple[date, time | None, time | None]] = []
        for col in SCAN_DAY_COLUMNS:
            date_cell = date_row[col] if col < len(date_row) else None
            if not isinstance(date_cell, str):
                continue

            month_day = extract_month_day(date_cell)
            if month_day is None or month_day not in date_lookup:
                continue  # outside the declared report period

            time_cell = time_row[col] if col < len(time_row) else None
            jam_masuk, jam_keluar = (
                parse_time_range(time_cell)
                if isinstance(time_cell, str)
                else (None, None)
            )
            records.append((date_lookup[month_day], jam_masuk, jam_keluar))
        return records

    def _get_or_create_employee(
        self, employee_name: str, result: RawScanImportResult
    ) -> EmployeeModel:
        """Find an employee by name, or auto-register a new one."""
        existing = self.employee_repo.get_by_name(employee_name)
        if existing is not None:
            return existing

        code = self._generate_employee_code()
        created = self.employee_service.create_employee(
            employee_code=code, nama=employee_name
        )
        result.new_employees_created.append(f"{employee_name} -> {code}")
        return created

    def _generate_employee_code(self) -> str:
        """Generate a unique employee_code like EMP0001, EMP0002, ..."""
        candidate_number = len(self.employee_repo.get_all()) + 1
        while True:
            code = f"EMP{candidate_number:04d}"
            if self.employee_repo.get_by_code(code) is None:
                return code
            candidate_number += 1

    def _save_attendance(
        self,
        employee: EmployeeModel,
        tanggal: date,
        jam_masuk: time | None,
        jam_keluar: time | None,
        result: RawScanImportResult,
    ) -> None:
        """Persist one attendance row, skipping if already imported."""
        existing = self.attendance_repo.get_by_employee_and_date(
            employee.id, tanggal
        )
        if existing is not None:
            result.skipped_duplicate.append(f"{employee.nama} @ {tanggal}")
            return

        hari = Weekday.from_index(tanggal.weekday()).value
        attendance = AttendanceModel(
            employee_id=employee.id,
            tanggal=tanggal,
            hari=hari,
            jam_masuk=jam_masuk,
            jam_keluar=jam_keluar,
            sumber_data="EXCEL_IMPORT_SCAN",
        )
        self.attendance_repo.create(attendance)
        result.imported += 1