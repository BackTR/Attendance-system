from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

APP_NAME = "Attendance Insight System"

APP_VERSION = "1.0.0"

DATABASE_NAME = "attendance.db"

DATABASE_PATH = BASE_DIR / "database" / DATABASE_NAME

LOG_DIR = BASE_DIR / "logs"

UPLOAD_DIR = BASE_DIR / "uploads"

EXPORT_DIR = BASE_DIR / "exports"

REPORT_DIR = BASE_DIR / "reports"