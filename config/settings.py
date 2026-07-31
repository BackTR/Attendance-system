import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

APP_NAME = "Attendance Insight System"

APP_VERSION = "1.0.0"

DATABASE_NAME = "attendance.db"

DATABASE_PATH = BASE_DIR / "database" / DATABASE_NAME

LOG_DIR = BASE_DIR / "logs"

UPLOAD_DIR = BASE_DIR / "uploads"

EXPORT_DIR = BASE_DIR / "exports"

REPORT_DIR = BASE_DIR / "reports"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

TIMEZONE = os.getenv("TIMEZONE", "Asia/Jakarta")
