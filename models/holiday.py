from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class HolidayModel(Base):
    """Represents a declared holiday (hari libur nasional / cuti bersama)."""

    __tablename__ = "holidays"

    id: Mapped[int] = mapped_column(primary_key=True)

    tanggal: Mapped[date] = mapped_column(Date, unique=True)

    keterangan: Mapped[str] = mapped_column(String(150))