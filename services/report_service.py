"""Report export service: Excel and PDF generation.

Per AI_RULES.md Rule 3 ("Repository tidak boleh... export excel, export
pdf"), all report generation logic lives here, never in Repository or UI.

Every row includes a human-readable "Keterangan" column built from
status_hari + status_masuk/status_keluar, so reports don't require
manually cross-referencing raw status codes to tell late/early-leave
apart from absent/holiday/overtime days.
"""

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