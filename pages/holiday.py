"""Holiday management page.

UI RULE (AI_RULES.md Rule 2 / 15): this page only does input, output,
and layout. All validation (duplicate date, empty description) lives
in HolidayService.
"""

import streamlit as st

from core.database import get_session
from core.exceptions import DuplicateHolidayException
from repositories.attendance_repository import AttendanceRepository
from repositories.holiday_repository import HolidayRepository
from repositories.settings_repository import SettingsRepository
from services.attendance_service import AttendanceService
from services.holiday_service import HolidayService
from utils.datetime_helper import today

st.set_page_config(page_title="Hari Libur - AIS", layout="wide")
st.title("📅 Kelola Hari Libur")

st.caption(
    "Sabtu & Minggu otomatis dianggap libur. Tambahkan di sini untuk "
    "tanggal merah nasional / cuti bersama. Pegawai yang tetap masuk "
    "pada hari libur akan otomatis dikategorikan 'Lembur'."
)

st.subheader("Tambah Hari Libur")
with st.form("form_tambah_libur", clear_on_submit=True):
    col1, col2 = st.columns([1, 2])
    with col1:
        tanggal = st.date_input("Tanggal", value=today())
    with col2:
        keterangan = st.text_input("Keterangan", placeholder="Contoh: HUT RI")

    submitted = st.form_submit_button("Simpan", type="primary")

    if submitted:
        try:
            with get_session() as session:
                HolidayService(HolidayRepository(session)).declare_holiday(
                    tanggal, keterangan
                )
            st.success(f"Hari libur {tanggal} ({keterangan}) berhasil ditambahkan.")
        except (DuplicateHolidayException, ValueError) as exc:
            st.error(str(exc))

st.divider()
st.subheader("Daftar Hari Libur")

with get_session() as session:
    holidays = HolidayService(HolidayRepository(session)).get_all()
    holiday_rows = [
        {"id": h.id, "Tanggal": h.tanggal.strftime("%Y-%m-%d"), "Keterangan": h.keterangan}
        for h in holidays
    ]

if holiday_rows:
    st.dataframe(
        [{k: v for k, v in row.items() if k != "id"} for row in holiday_rows],
        use_container_width=True,
        hide_index=True,
    )

    selected_label = st.selectbox(
        "Pilih hari libur untuk dihapus",
        options=[f"{row['Tanggal']} - {row['Keterangan']}" for row in holiday_rows],
    )
    if st.button("Hapus Hari Libur"):
        selected_row = holiday_rows[
            [f"{r['Tanggal']} - {r['Keterangan']}" for r in holiday_rows].index(
                selected_label
            )
        ]
        with get_session() as session:
            HolidayService(HolidayRepository(session)).remove_holiday(
                selected_row["id"]
            )
        st.success("Hari libur berhasil dihapus.")
        st.rerun()
else:
    st.info("Belum ada hari libur yang didaftarkan.")

st.divider()
st.subheader("Analisis Ulang")
st.caption(
    "Setelah menambah/menghapus hari libur, data absensi yang sudah "
    "pernah dianalisis TIDAK otomatis berubah. Klik tombol ini untuk "
    "menghitung ulang seluruh data."
)
if st.button("Analisis Ulang Semua Data"):
    with get_session() as session:
        count = AttendanceService(
            AttendanceRepository(session),
            SettingsRepository(session),
            HolidayRepository(session),
        ).reanalyze_all()
    st.success(f"{count} data absensi berhasil dianalisis ulang.")