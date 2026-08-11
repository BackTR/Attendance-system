"""Default fallback constants for AIS.

IMPORTANT: These values are ONLY used to seed the `settings` table on
first run (see models/app_settings.py + services/settings_service.py).
Business logic (Service layer) must always read working hours from the
database via SettingsService, never hardcode them again (AI_RULES Rule 9).
"""

from datetime import time

DEFAULT_WORK_START_TIME: time = time(7, 30)
DEFAULT_WORK_END_TIME: time = time(15, 30)
DEFAULT_FRIDAY_END_TIME: time = time(13, 0)

DEFAULT_TOLERANCE_LATE_MINUTES: int = 0
DEFAULT_TOLERANCE_LEAVE_MINUTES: int = 0

FRIDAY_WEEKDAY_INDEX: int = 4  # Monday=0 ... Sunday=6
WEEKEND_WEEKDAY_INDEXES: tuple[int, ...] = (5, 6)  # Saturday, Sunday

EXCEL_REQUIRED_COLUMNS: tuple[str, ...] = (
    "employee_code",
    "tanggal",
    "jam_masuk",
    "jam_keluar",
)

MAX_UPLOAD_SIZE_MB: int = 10
ALLOWED_EXCEL_EXTENSIONS: tuple[str, ...] = (".xlsx", ".xls")