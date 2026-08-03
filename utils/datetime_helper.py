"""Timezone-aware date/time helpers.

Ruff (DTZ011) flags naive `datetime.date.today()` because it silently
relies on the server's local timezone. This wraps it explicitly using
the app's configured TIMEZONE (config/settings.py).
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from config.settings import TIMEZONE


def today() -> date:
    """Return today's date in the application's configured timezone."""
    return datetime.now(tz=ZoneInfo(TIMEZONE)).date()