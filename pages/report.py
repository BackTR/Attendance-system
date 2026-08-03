"""Report export page.

UI RULE (AI_RULES.md Rule 2 / 15): this page only does input, output,
and layout. All Excel/PDF generation logic lives in ReportService.
"""

from datetime import date, timedelta

import streamlit as st

from core.database import get_session
from repositories.attendance_repository import AttendanceRepository
from repositories.employee_repository import EmployeeRepository
from services.report_service import ReportService

st.set_page_config(page_title="Laporan - AIS", layout="wide")
st.title("🧾 Laporan Absensi")

# --- Input: date range (UI only) ---
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input(
        "Dari tanggal", value=date.today() - timedelta(days=30), key="report_start"
    )
with col2:
    end_date = st.date_input("Sampai tanggal", value=date.today(), key="report_end")

if start_date > end_date:
    st.error("Tanggal awal tidak boleh lebih besar dari tanggal akhir.")
    st.stop()

st.divider()
st.write("Pilih format laporan yang ingin diunduh:")

export_col1, export_col2 = st.columns(2)

with export_col1:
    st.subheader("Excel")
    if st.button("Generate Excel", use_container_width=True):
        with get_session() as session:
            service = ReportService(
                AttendanceRepository(session), EmployeeRepository(session)
            )
            excel_bytes = service.export_to_excel(start_date, end_date)
        st.download_button(
            label="⬇️ Download Excel",
            data=excel_bytes,
            file_name=f"laporan_absensi_{start_date}_{end_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

with export_col2:
    st.subheader("PDF")
    if st.button("Generate PDF", use_container_width=True):
        with get_session() as session:
            service = ReportService(
                AttendanceRepository(session), EmployeeRepository(session)
            )
            pdf_bytes = service.export_to_pdf(start_date, end_date)
        st.download_button(
            label="⬇️ Download PDF",
            data=pdf_bytes,
            file_name=f"laporan_absensi_{start_date}_{end_date}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )