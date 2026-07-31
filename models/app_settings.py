from sqlalchemy import Integer
from sqlalchemy import String

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from models.base import Base


class AppSettingsModel(Base):

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True)

    work_start: Mapped[str] = mapped_column(
        String(10),
        default="07:30"
    )

    work_end: Mapped[str] = mapped_column(
        String(10),
        default="15:30"
    )

    friday_end: Mapped[str] = mapped_column(
        String(10),
        default="13:00"
    )

    tolerance_late: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    tolerance_leave: Mapped[int] = mapped_column(
        Integer,
        default=0
    )