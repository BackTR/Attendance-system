from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.holiday import HolidayModel


class HolidayRepository:
    """Handles database access (CRUD only) for HolidayModel."""

    def __init__(self, session: Session) -> None:
        """Initialize repository with an active database session.

        Args:
            session: Active SQLAlchemy session.
        """
        self.session = session

    def create(self, holiday: HolidayModel) -> HolidayModel:
        """Persist a new holiday record."""
        self.session.add(holiday)
        self.session.flush()
        return holiday

    def get_by_date(self, tanggal: date) -> HolidayModel | None:
        """Fetch a holiday by its exact date."""
        stmt = select(HolidayModel).where(HolidayModel.tanggal == tanggal)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_id(self, holiday_id: int) -> HolidayModel | None:
        """Fetch a holiday by primary key."""
        return self.session.get(HolidayModel, holiday_id)

    def get_by_period(self, start_date: date, end_date: date) -> list[HolidayModel]:
        """Fetch all holidays within an inclusive date range."""
        stmt = select(HolidayModel).where(
            HolidayModel.tanggal.between(start_date, end_date)
        ).order_by(HolidayModel.tanggal)
        return list(self.session.execute(stmt).scalars().all())

    def get_all(self) -> list[HolidayModel]:
        """Fetch every declared holiday."""
        stmt = select(HolidayModel).order_by(HolidayModel.tanggal)
        return list(self.session.execute(stmt).scalars().all())

    def delete(self, holiday: HolidayModel) -> None:
        """Remove a holiday record."""
        self.session.delete(holiday)
        self.session.flush()