"""Settings page.

UI RULE (AI_RULES.md Rule 2 / 15): this page only does input, output,
and layout. All validation lives in SettingsService — this page never
decides whether a value is valid, it just shows the error if rejected.
"""

import streamlit as st

from core.database import get_session
from core.exceptions import InvalidSettingsException
from repositories.settings_repository import SettingsRepository
from services.settings_service import SettingsService

st.set_page_config(page_title="Pengaturan - AIS", layout="centered")
st.title("⚙️ Pengaturan Jam Kerja")

with get_session() as session:
    current = SettingsService(SettingsRepository(session)).get_settings()
    current_work_start = current.work_start
    current_work_end = current.work_end
    current_friday_end = current.friday_end
    current_tolerance_late = current.tolerance_late
    current_tolerance_leave = current.tolerance_leave

st.subheader("Senin - Kamis")
col1, col2 = st.columns(2)
with col1:
    work_start = st.time_input("Jam Masuk", value=current_work_start)
with col2:
    work_end = st.time_input("Jam Pulang", value=current_work_end)

st.subheader("Jumat")
friday_end = st.time_input("Jam Pulang (Jumat)", value=current_friday_end)

st.subheader("Toleransi")
col3, col4 = st.columns(2)
with col3:
    tolerance_late = st.number_input(
        "Toleransi Telat (menit)", min_value=0, value=current_tolerance_late
    )
with col4:
    tolerance_leave = st.number_input(
        "Toleransi Pulang Cepat (menit)", min_value=0, value=current_tolerance_leave
    )

if st.button("Simpan Pengaturan", type="primary", use_container_width=True):
    try:
        with get_session() as session:
            service = SettingsService(SettingsRepository(session))
            service.update_settings(
                work_start=work_start,
                work_end=work_end,
                friday_end=friday_end,
                tolerance_late=int(tolerance_late),
                tolerance_leave=int(tolerance_leave),
            )
        st.success("Pengaturan berhasil disimpan.")
    except InvalidSettingsException as exc:
        st.error(str(exc))