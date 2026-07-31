from datetime import date
from datetime import time

from sqlalchemy import Date
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Time

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from models.base import Base


class AttendanceModel(Base):
    """Represents a single daily attendance record for an employee."""

    __tablename__ = "attendance"

    id: Mapped[int] = mapped_column(primary_key=True)

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id")
    )

    tanggal: Mapped[date] = mapped_column(Date)

    hari: Mapped[str] = mapped_column(String(20))

    jam_masuk: Mapped[time] = mapped_column(
        Time,
        nullable=True
    )

    jam_keluar: Mapped[time] = mapped_column(
        Time,
        nullable=True
    )

    status_masuk: Mapped[str] = mapped_column(
        String(30),
        nullable=True
    )

    status_keluar: Mapped[str] = mapped_column(
        String(30),
        nullable=True
    )

    menit_telat: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    menit_pulang_cepat: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    sumber_data: Mapped[str] = mapped_column(
        String(30)
    )

    employee = relationship("EmployeeModel")
