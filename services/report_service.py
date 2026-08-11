"""Report export service: Excel and PDF generation.

Per AI_RULES.md Rule 3 ("Repository tidak boleh... export excel, export
pdf"), all report generation logic lives here, never in Repository or UI.

Every row includes a human-readable "Keterangan" column built from
status_hari + status_masuk/status_keluar, so reports don't require
manually cross-referencing raw status codes to tell late/early-leave
apart from absent/holiday/overtime days.
"""

from dataclasses import dataclass, field
from datetime import date
from io import BytesIO

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from core.enums.attendance import AttendanceStatus, CheckInStatus, CheckOutStatus
from core.logger import logger
from models.attendance import AttendanceModel
from repositories.attendance_repository import AttendanceRepository
from repositories.employee_repository import EmployeeRepository

_STATUS_HARI_LABELS: dict[str, str] = {
    AttendanceStatus.PRESENT.value: "Hadir",
    AttendanceStatus.ABSENT.value: "Tidak Hadir",
    AttendanceStatus.INCOMPLETE.value: "Hadir (Tidak Lengkap)",
    AttendanceStatus.LIBUR.value: "Libur",
    AttendanceStatus.LEMBUR.value: "Lembur",
}

@dataclass
class EmployeeRecapDetail:
    """Per-employee recap: totals plus WHICH dates each problem happened on.

    This is what a report reader actually needs -- not 23 rows per
    employee to scan through, but one row naming the exact dates.
    """

    employee_code: str
    nama: str
    total_hadir: int = 0
    total_tidak_hadir: int = 0
    total_telat: int = 0
    total_pulang_cepat: int = 0
    total_libur: int = 0
    total_lembur: int = 0
    tanggal_tidak_hadir: list[str] = field(default_factory=list)
    tanggal_telat: list[str] = field(default_factory=list)
    tanggal_pulang_cepat: list[str] = field(default_factory=list)

class ReportService:
    """Generates Excel and PDF attendance reports for a given period."""

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

    def export_to_excel(self, start_date: date, end_date: date) -> bytes:
        """Generate an Excel report for the given period.

        Args:
            start_date: Start of the period (inclusive).
            end_date: End of the period (inclusive).

        Returns:
            Raw XLSX file bytes, ready for st.download_button.
        """
        rows = self._build_rows(start_date, end_date)
        df = pd.DataFrame(rows)

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Absensi")
        buffer.seek(0)

        logger.info(f"Excel report generated: {len(rows)} baris")
        return buffer.getvalue()

    def export_to_pdf(self, start_date: date, end_date: date) -> bytes:
        """Generate a PDF report for the given period.

        Args:
            start_date: Start of the period (inclusive).
            end_date: End of the period (inclusive).

        Returns:
            Raw PDF file bytes, ready for st.download_button.
        """
        rows = self._build_rows(start_date, end_date)

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        styles = getSampleStyleSheet()

        elements = [
            Paragraph(
                f"Laporan Absensi ({start_date} s.d. {end_date})", styles["Title"]
            ),
            Spacer(1, 0.5 * cm),
        ]

        if rows:
            headers = list(rows[0].keys())
            table_data = [headers] + [
                [str(value) for value in row.values()] for row in rows
            ]
            table = Table(table_data, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTSIZE", (0, 0), (-1, -1), 7),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#F2F2F2")],
                        ),
                    ]
                )
            )
            elements.append(table)
        else:
            elements.append(
                Paragraph("Tidak ada data pada periode ini.", styles["Normal"])
            )

        doc.build(elements)
        buffer.seek(0)

        logger.info(f"PDF report generated: {len(rows)} baris")
        return buffer.getvalue()

    def export_recap_to_excel(self, start_date: date, end_date: date) -> bytes:
        """Generate a per-employee recap Excel report (1 row per employee).

        Unlike export_to_excel (1 row per employee per day), this lists
        totals plus the exact dates of each absence/lateness/early-leave,
        so a reader doesn't need to scan every date row manually.

        Args:
            start_date: Start of the period (inclusive).
            end_date: End of the period (inclusive).

        Returns:
            Raw XLSX file bytes, ready for st.download_button.
        """
        recaps = self._build_employee_recaps(start_date, end_date)
        rows = [self._recap_to_row(r) for r in recaps]
        df = pd.DataFrame(rows)

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Rekap Pegawai")
            worksheet = writer.sheets["Rekap Pegawai"]
            # Widen the date-list columns so they're readable without
            # manually resizing every time the file is opened.
            for col_letter in ("I", "J", "K"):
                worksheet.column_dimensions[col_letter].width = 40
        buffer.seek(0)

        logger.info(f"Recap Excel generated: {len(rows)} pegawai")
        return buffer.getvalue()

    def export_recap_to_pdf(self, start_date: date, end_date: date) -> bytes:
        """Generate a per-employee recap PDF report (1 row per employee).

        Args:
            start_date: Start of the period (inclusive).
            end_date: End of the period (inclusive).

        Returns:
            Raw PDF file bytes, ready for st.download_button.
        """
        recaps = self._build_employee_recaps(start_date, end_date)

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        styles = getSampleStyleSheet()
        cell_style = styles["Normal"]
        cell_style.fontSize = 7

        elements = [
            Paragraph(
                f"Rekap Absensi per Pegawai ({start_date} s.d. {end_date})",
                styles["Title"],
            ),
            Spacer(1, 0.5 * cm),
        ]

        if recaps:
            headers = [
                "Kode",
                "Nama",
                "Hadir",
                "Tdk Hadir",
                "Telat",
                "Plg Cepat",
                "Libur",
                "Lembur",
                "Tanggal Tidak Hadir",
                "Tanggal Telat",
                "Tanggal Pulang Cepat",
            ]
            table_data = [headers]
            for r in recaps:
                table_data.append(
                    [
                        r.employee_code,
                        r.nama,
                        str(r.total_hadir),
                        str(r.total_tidak_hadir),
                        str(r.total_telat),
                        str(r.total_pulang_cepat),
                        str(r.total_libur),
                        str(r.total_lembur),
                        Paragraph(", ".join(r.tanggal_tidak_hadir) or "-", cell_style),
                        Paragraph(", ".join(r.tanggal_telat) or "-", cell_style),
                        Paragraph(
                            ", ".join(r.tanggal_pulang_cepat) or "-", cell_style
                        ),
                    ]
                )

            table = Table(
                table_data,
                repeatRows=1,
                colWidths=[
                    1.6 * cm, 3.2 * cm, 1.4 * cm, 1.6 * cm, 1.4 * cm, 1.6 * cm,
                    1.4 * cm, 1.6 * cm, 4.5 * cm, 4.5 * cm, 4.5 * cm,
                ],
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTSIZE", (0, 0), (-1, 0), 7),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#F2F2F2")],
                        ),
                    ]
                )
            )
            elements.append(table)
        else:
            elements.append(
                Paragraph("Tidak ada data pada periode ini.", styles["Normal"])
            )

        doc.build(elements)
        buffer.seek(0)

        logger.info(f"Recap PDF generated: {len(recaps)} pegawai")
        return buffer.getvalue()

    def _build_employee_recaps(
        self, start_date: date, end_date: date
    ) -> list[EmployeeRecapDetail]:
        """Group attendance records per employee, collecting problem dates."""
        records = self.attendance_repo.get_by_period(start_date, end_date)
        by_employee: dict[int, list[AttendanceModel]] = {}
        for record in records:
            by_employee.setdefault(record.employee_id, []).append(record)

        recaps: list[EmployeeRecapDetail] = []
        for employee in self.employee_repo.get_all_active():
            employee_records = sorted(
                by_employee.get(employee.id, []), key=lambda r: r.tanggal
            )
            recap = EmployeeRecapDetail(
                employee_code=employee.employee_code, nama=employee.nama
            )
            for record in employee_records:
                self._tally_recap(recap, record)
            recaps.append(recap)

        return recaps

    def _tally_recap(
        self, recap: EmployeeRecapDetail, record: AttendanceModel
    ) -> None:
        """Update one employee's recap counters/date-lists for one record."""
        tanggal_str = record.tanggal.strftime("%d-%m")

        if record.status_hari == AttendanceStatus.LIBUR.value:
            recap.total_libur += 1
        elif record.status_hari == AttendanceStatus.LEMBUR.value:
            recap.total_lembur += 1
        elif record.status_hari == AttendanceStatus.ABSENT.value:
            recap.total_tidak_hadir += 1
            recap.tanggal_tidak_hadir.append(tanggal_str)
        else:
            recap.total_hadir += 1

        if record.status_masuk == CheckInStatus.LATE.value:
            recap.total_telat += 1
            recap.tanggal_telat.append(f"{tanggal_str} ({record.menit_telat}mnt)")

        if record.status_keluar == CheckOutStatus.EARLY.value:
            recap.total_pulang_cepat += 1
            recap.tanggal_pulang_cepat.append(
                f"{tanggal_str} ({record.menit_pulang_cepat}mnt)"
            )

    def _recap_to_row(self, recap: EmployeeRecapDetail) -> dict:
        """Flatten an EmployeeRecapDetail into a spreadsheet row."""
        return {
            "Kode Pegawai": recap.employee_code,
            "Nama": recap.nama,
            "Hadir": recap.total_hadir,
            "Tidak Hadir": recap.total_tidak_hadir,
            "Telat": recap.total_telat,
            "Pulang Cepat": recap.total_pulang_cepat,
            "Libur": recap.total_libur,
            "Lembur": recap.total_lembur,
            "Tanggal Tidak Hadir": ", ".join(recap.tanggal_tidak_hadir) or "-",
            "Tanggal Telat": ", ".join(recap.tanggal_telat) or "-",
            "Tanggal Pulang Cepat": ", ".join(recap.tanggal_pulang_cepat) or "-",
        }

    def _build_rows(self, start_date: date, end_date: date) -> list[dict]:
        """Build flat, human-readable rows (employee data joined in)."""
        records = self.attendance_repo.get_by_period(start_date, end_date)
        employees = {e.id: e for e in self.employee_repo.get_all_active()}

        rows: list[dict] = []
        for record in records:
            employee = employees.get(record.employee_id)
            rows.append(
                {
                    "Kode Pegawai": employee.employee_code if employee else "-",
                    "Nama": employee.nama if employee else "-",
                    "Tanggal": record.tanggal.strftime("%Y-%m-%d"),
                    "Hari": record.hari,
                    "Status Hari": _STATUS_HARI_LABELS.get(
                        record.status_hari, record.status_hari or "-"
                    ),
                    "Jam Masuk": (
                        record.jam_masuk.strftime("%H:%M")
                        if record.jam_masuk
                        else "-"
                    ),
                    "Jam Keluar": (
                        record.jam_keluar.strftime("%H:%M")
                        if record.jam_keluar
                        else "-"
                    ),
                    "Keterangan": self._build_keterangan(record),
                    "Menit Telat": record.menit_telat,
                    "Menit Pulang Cepat": record.menit_pulang_cepat,
                    "Durasi Kerja (menit)": (
                        record.durasi_kerja if record.durasi_kerja is not None else "-"
                    ),
                }
            )
        return rows

    def _build_keterangan(self, record: AttendanceModel) -> str:
        """Build one human-readable summary string for a record.

        This is the column meant to answer "is this row a problem?" at a
        glance, without cross-referencing status_masuk/status_keluar/
        status_hari separately.
        """
        if record.status_hari == AttendanceStatus.LIBUR.value:
            return "Libur"
        if record.status_hari == AttendanceStatus.LEMBUR.value:
            return "Lembur (masuk saat libur)"
        if record.status_hari == AttendanceStatus.ABSENT.value:
            return "Tidak Hadir"

        details: list[str] = []
        if record.status_masuk == CheckInStatus.LATE.value:
            details.append(f"Telat {record.menit_telat} menit")
        elif record.status_masuk == CheckInStatus.MISSING.value:
            details.append("Tidak absen masuk")

        if record.status_keluar == CheckOutStatus.EARLY.value:
            details.append(f"Pulang cepat {record.menit_pulang_cepat} menit")
        elif record.status_keluar == CheckOutStatus.MISSING.value:
            details.append("Tidak absen pulang")

        return ", ".join(details) if details else "Tepat waktu"