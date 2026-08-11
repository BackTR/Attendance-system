"""Report export page.

UI RULE (AI_RULES.md Rule 2 / 15): this page only does input, output,
and layout. All Excel/PDF generation logic lives in ReportService.
"""

from datetime import timedelta

import streamlit as st

from core.database import get_session
from repositories.attendance_repository import AttendanceRepository
from repositories.employee_repository import EmployeeRepository
from services.report_service import ReportService
from utils.datetime_helper import today

st.set_page_config(page_title="Laporan - AIS", layout="wide")
st.title("🧾 Laporan Absensi")

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input(
        "Dari tanggal", value=today() - timedelta(days=30), key="report_start"
    )
with col2:
    end_date = st.date_input("Sampai tanggal", value=today(), key="report_end")

if start_date > end_date:
    st.error("Tanggal awal tidak boleh lebih besar dari tanggal akhir.")
    st.stop()

st.divider()

report_mode = st.radio(
    "Jenis Laporan",
    options=["detail", "rekap"],
    format_func=lambda v: (
        "Detail Harian (1 baris per tanggal per pegawai)"
        if v == "detail"
        else "Rekap per Pegawai (1 baris per pegawai, tanggal bermasalah dirangkum)"
    ),
)

if report_mode == "rekap":
    st.caption(
        "Cocok untuk cek cepat: siapa yang telat/pulang cepat/tidak hadir, "
        "dan tanggal berapa saja -- tanpa perlu scroll semua tanggal."
    )

st.write("Pilih format file yang ingin diunduh:")

export_col1, export_col2 = st.columns(2)

with export_col1:
    st.subheader("Excel")
    if st.button("Generate Excel", use_container_width=True):
        with get_session() as session:
            service = ReportService(
                AttendanceRepository(session), EmployeeRepository(session)
            )
            if report_mode == "detail":
                excel_bytes = service.export_to_excel(start_date, end_date)
                file_label = "laporan_absensi"
            else:
                excel_bytes = service.export_recap_to_excel(start_date, end_date)
                file_label = "rekap_absensi"
        st.download_button(
            label="⬇️ Download Excel",
            data=excel_bytes,
            file_name=f"{file_label}_{start_date}_{end_date}.xlsx",
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
            if report_mode == "detail":
                pdf_bytes = service.export_to_pdf(start_date, end_date)
                file_label = "laporan_absensi"
            else:
                pdf_bytes = service.export_recap_to_pdf(start_date, end_date)
                file_label = "rekap_absensi"
        st.download_button(
            label="⬇️ Download PDF",
            data=pdf_bytes,
            file_name=f"{file_label}_{start_date}_{end_date}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )