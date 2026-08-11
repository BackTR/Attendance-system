from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.attendance import AttendanceModel


class AttendanceRepository:
    """Handles database access (CRUD only) for AttendanceModel."""

    def __init__(self, session: Session) -> None:
        """Initialize repository with an active database session.

        Args:
            session: Active SQLAlchemy session.
        """
        self.session = session

    def create(self, attendance: AttendanceModel) -> AttendanceModel:
        """Persist a new attendance record."""
        self.session.add(attendance)
        self.session.flush()
        return attendance

    def get_by_employee_and_date(
        self, employee_id: int, tanggal: date
    ) -> AttendanceModel | None:
        """Fetch an attendance record for a specific employee and date."""
        stmt = select(AttendanceModel).where(
            AttendanceModel.employee_id == employee_id,
            AttendanceModel.tanggal == tanggal,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_period(
        self, start_date: date, end_date: date
    ) -> list[AttendanceModel]:
        """Fetch attendance records within an inclusive date range."""
        stmt = select(AttendanceModel).where(
            AttendanceModel.tanggal.between(start_date, end_date)
        )
        return list(self.session.execute(stmt).scalars().all())
    
    def get_unanalyzed(self) -> list[AttendanceModel]:
        """Fetch attendance records that have not yet been analyzed.

        A record is considered unanalyzed if status_hari is still NULL
        (set by ExcelImportService/RawScanImportService, filled in later
        by AttendanceService). status_hari (not status_masuk) is used
        because on holidays status_masuk intentionally stays NULL even
        after analysis.
        """
        stmt = select(AttendanceModel).where(
            AttendanceModel.status_hari.is_(None)
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_all(self) -> list[AttendanceModel]:
        """Fetch every attendance record (used for full re-analysis)."""
        stmt = select(AttendanceModel)
        return list(self.session.execute(stmt).scalars().all())

    def update(self, attendance: AttendanceModel) -> AttendanceModel:
        """Persist changes made to an existing attendance record."""
        self.session.flush()
        return attendance
