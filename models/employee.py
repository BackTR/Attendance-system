from datetime import datetime

from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from models.base import Base


class EmployeeModel(Base):

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    employee_code: Mapped[str] = mapped_column(
        String(20),
        unique=True
    )

    nama: Mapped[str] = mapped_column(
        String(150)
    )

    jabatan: Mapped[str] = mapped_column(
        String(100),
        nullable=True
    )

    unit: Mapped[str] = mapped_column(
        String(100),
        nullable=True
    )

    aktif: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )