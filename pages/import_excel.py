"""Excel import page.

UI RULE (AI_RULES.md Rule 2 / 15): input (file upload + format choice),
output (result summary), layout only. All parsing/validation logic
lives in ExcelImportService / RawScanImportService (services/parser.py).

SECURITY (CODING_STANDARDS.md Security Guidelines): the original
filename is never trusted or used to write to disk -- a random name is
generated instead, and file size is capped.
"""

import uuid
from pathlib import Path

import streamlit as st

from config.constants import ALLOWED_EXCEL_EXTENSIONS, MAX_UPLOAD_SIZE_MB
from config.settings import UPLOAD_DIR
from core.database import get_session
from core.exceptions import InvalidExcelFormatException
from repositories.attendance_repository import AttendanceRepository
from repositories.settings_repository import SettingsRepository
from services.attendance_service import AttendanceService
from services.parser import ExcelImportService, RawScanImportService

st.set_page_config(page_title="Import Excel - AIS", layout="wide")
st.title("📥 Import Data Absensi")

file_format = st.radio(
    "Format File",
    options=["standar", "mesin_absensi"],
    format_func=lambda v: (
        "Standar (kolom: employee_code, tanggal, jam_masuk, jam_keluar)"
        if v == "standar"
        else "Mesin Absensi Fingerprint (format 'Data Scan Karyawan')"
    ),
)

if file_format == "standar":
    st.caption(
        "Kolom wajib: employee_code, tanggal, jam_masuk, jam_keluar. "
        f"Maks ukuran file {MAX_UPLOAD_SIZE_MB} MB."
    )
else:
    st.caption(
        "Untuk file hasil export mesin absensi fingerprint. Pegawai yang "
        "belum terdaftar akan otomatis didaftarkan dengan kode baru. "
        f"Maks ukuran file {MAX_UPLOAD_SIZE_MB} MB."
    )

uploaded_file = st.file_uploader(
    "Pilih file Excel",
    type=[ext.lstrip(".") for ext in ALLOWED_EXCEL_EXTENSIONS],
)

if uploaded_file is not None:
    size_mb = uploaded_file.size / (1024 * 1024)
    if size_mb > MAX_UPLOAD_SIZE_MB:
        st.error(
            f"Ukuran file {size_mb:.1f} MB melebihi batas {MAX_UPLOAD_SIZE_MB} MB."
        )
        st.stop()

    if st.button("Proses Import", type="primary"):
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        extension = Path(uploaded_file.name).suffix.lower()
        safe_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{extension}"
        safe_path.write_bytes(uploaded_file.getvalue())

        try:
            if file_format == "standar":
                with get_session() as session:
                    import_result = ExcelImportService(session).import_from_excel(
                        str(safe_path)
                    )

                with get_session() as session:
                    analyzed_count = AttendanceService(
                        AttendanceRepository(session), SettingsRepository(session)
                    ).analyze_pending()

                st.success(
                    f"Import selesai: {import_result.imported}/"
                    f"{import_result.total_rows} baris berhasil, "
                    f"{analyzed_count} data dianalisis."
                )
                if import_result.skipped_employee_not_found:
                    st.warning(
                        "Kode pegawai tidak ditemukan: "
                        + ", ".join(import_result.skipped_employee_not_found)
                    )
                if import_result.skipped_duplicate:
                    st.warning(
                        "Data duplikat dilewati: "
                        + ", ".join(import_result.skipped_duplicate)
                    )
                if import_result.skipped_invalid_row:
                    st.warning(
                        "Baris tidak valid: "
                        + "; ".join(import_result.skipped_invalid_row)
                    )
            else:
                with get_session() as session:
                    scan_result = RawScanImportService(session).import_from_excel(
                        str(safe_path)
                    )

                with get_session() as session:
                    analyzed_count = AttendanceService(
                        AttendanceRepository(session), SettingsRepository(session)
                    ).analyze_pending()

                st.success(
                    f"Import selesai: {scan_result.total_employees} pegawai, "
                    f"{scan_result.imported} data absensi baru, "
                    f"{analyzed_count} data dianalisis."
                )
                if scan_result.new_employees_created:
                    st.info(
                        f"{len(scan_result.new_employees_created)} pegawai baru "
                        "otomatis didaftarkan:\n\n"
                        + "\n".join(f"- {x}" for x in scan_result.new_employees_created)
                    )
                if scan_result.skipped_duplicate:
                    st.warning(
                        f"{len(scan_result.skipped_duplicate)} data duplikat dilewati."
                    )
        except InvalidExcelFormatException as exc:
            st.error(str(exc))
        finally:
            safe_path.unlink(missing_ok=True)