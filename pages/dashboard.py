"""Dashboard page.

UI RULE (AI_RULES.md Rule 2 / 15): this page only does input, output,
and layout. It never queries the database directly — it only calls
DashboardService, which uses Repositories under the hood.
"""

from datetime import date, timedelta

import plotly.express as px
import streamlit as st

from core.database import get_session
from repositories.attendance_repository import AttendanceRepository
from repositories.employee_repository import EmployeeRepository
from services.dashboard_service import DashboardService
from utils.datetime_helper import today

st.set_page_config(page_title="Dashboard - AIS", layout="wide")
st.title("📊 Dashboard Absensi")

# --- Input: date range (UI only) ---
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Dari tanggal", value=today() - timedelta(days=30))
with col2:
    end_date = st.date_input("Sampai tanggal", value=today())

if start_date > end_date:
    st.error("Tanggal awal tidak boleh lebih besar dari tanggal akhir.")
    st.stop()

# --- Call Service (all business logic lives there) ---
with get_session() as session:
    dashboard_service = DashboardService(
        AttendanceRepository(session), EmployeeRepository(session)
    )
    summary = dashboard_service.get_period_summary(start_date, end_date)
    recap = dashboard_service.get_employee_recap(start_date, end_date)

# --- Output: metrics ---
metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
metric_col1.metric("Total Hadir", summary.total_hadir)
metric_col2.metric("Tidak Hadir", summary.total_tidak_hadir)
metric_col3.metric("Terlambat", summary.total_telat)
metric_col4.metric("Pulang Cepat", summary.total_pulang_cepat)

st.metric("Rata-rata Durasi Kerja (menit)", round(summary.rata_rata_durasi_menit, 1))

st.divider()

# --- Output: chart (Plotly, per Tech Stack rule) ---
st.subheader("Rekap per Pegawai")

if recap:
    chart_data = [
        {
            "Nama": r.nama,
            "Terlambat": r.total_telat,
            "Pulang Cepat": r.total_pulang_cepat,
            "Tidak Hadir": r.total_tidak_hadir,
        }
        for r in recap
    ]
    fig = px.bar(
        chart_data,
        x="Nama",
        y=["Terlambat", "Pulang Cepat", "Tidak Hadir"],
        barmode="group",
        title="Rekap Absensi per Pegawai",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        chart_data,
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("Belum ada data pegawai.")