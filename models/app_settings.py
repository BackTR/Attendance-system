from datetime import time

from sqlalchemy import Integer
from sqlalchemy import Time

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from config.constants import (
    DEFAULT_WORK_START_TIME,
    DEFAULT_WORK_END_TIME,
    DEFAULT_FRIDAY_END_TIME,
    DEFAULT_TOLERANCE_LATE_MINUTES,
    DEFAULT_TOLERANCE_LEAVE_MINUTES,
)
from models.base import Base


class AppSettingsModel(Base):
    """Configurable working-hour rules, editable by an operator at runtime.

    Stored as proper time columns (not strings) so Services can compare
    them directly against attendance check-in/check-out times.
    """

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True)

    work_start: Mapped[time] = mapped_column(
        Time,
        default=DEFAULT_WORK_START_TIME
    )

    work_end: Mapped[time] = mapped_column(
        Time,
        default=DEFAULT_WORK_END_TIME
    )

    friday_end: Mapped[time] = mapped_column(
        Time,
        default=DEFAULT_FRIDAY_END_TIME
    )

    tolerance_late: Mapped[int] = mapped_column(
        Integer,
        default=DEFAULT_TOLERANCE_LATE_MINUTES
    )

    tolerance_leave: Mapped[int] = mapped_column(
        Integer,
        default=DEFAULT_TOLERANCE_LEAVE_MINUTES
    )
