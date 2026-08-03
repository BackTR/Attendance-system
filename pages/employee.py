"""Employee management page.

UI RULE (AI_RULES.md Rule 2 / 15): this page only does input, output,
and layout. All validation (duplicate code, empty fields) lives in
EmployeeService.
"""

import streamlit as st

from core.database import get_session
from core.exceptions import EmployeeAlreadyExistsException
from repositories.employee_repository import EmployeeRepository
from services.employee_service import EmployeeService

st.set_page_config(page_title="Pegawai - AIS", layout="wide")
st.title("👤 Kelola Pegawai")

st.subheader("Tambah Pegawai Baru")
with st.form("form_tambah_pegawai", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        employee_code = st.text_input("Kode Pegawai *")
        jabatan = st.text_input("Jabatan")
    with col2:
        nama = st.text_input("Nama Lengkap *")
        unit = st.text_input("Unit")

    submitted = st.form_submit_button("Simpan Pegawai", type="primary")

    if submitted:
        try:
            with get_session() as session:
                EmployeeService(EmployeeRepository(session)).create_employee(
                    employee_code=employee_code,
                    nama=nama,
                    jabatan=jabatan,
                    unit=unit,
                )
            st.success(f"Pegawai '{nama}' berhasil ditambahkan.")
        except (EmployeeAlreadyExistsException, ValueError) as exc:
            st.error(str(exc))

st.divider()
st.subheader("Daftar Pegawai")

with get_session() as session:
    employees = EmployeeService(EmployeeRepository(session)).get_all()
    employee_rows = [
        {
            "id": e.id,
            "Kode": e.employee_code,
            "Nama": e.nama,
            "Jabatan": e.jabatan or "-",
            "Unit": e.unit or "-",
            "Status": "Aktif" if e.aktif else "Nonaktif",
        }
        for e in employees
    ]

if employee_rows:
    st.dataframe(
        [{k: v for k, v in row.items() if k != "id"} for row in employee_rows],
        use_container_width=True,
        hide_index=True,
    )

    st.write("Ubah status aktif pegawai:")
    selected_code = st.selectbox(
        "Pilih pegawai", options=[row["Kode"] for row in employee_rows]
    )
    selected_row = next(
        row for row in employee_rows if row["Kode"] == selected_code
    )

    action_label = "Nonaktifkan" if selected_row["Status"] == "Aktif" else "Aktifkan"
    if st.button(action_label):
        with get_session() as session:
            EmployeeService(EmployeeRepository(session)).set_active_status(
                selected_row["id"], aktif=(action_label == "Aktifkan")
            )
        st.success(f"Status '{selected_code}' diubah menjadi {action_label.lower()}.")
        st.rerun()
else:
    st.info("Belum ada pegawai. Tambahkan lewat form di atas.")