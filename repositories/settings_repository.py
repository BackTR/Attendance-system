from sqlalchemy.orm import Session

from models.app_settings import AppSettingsModel


class SettingsRepository:
    """Handles database access (CRUD only) for AppSettingsModel."""

    def __init__(self, session: Session) -> None:
        """Initialize repository with an active database session.

        Args:
            session: Active SQLAlchemy session.
        """
        self.session = session

    def get(self) -> AppSettingsModel | None:
        """Fetch the single settings row (AIS uses one global settings record)."""
        return self.session.query(AppSettingsModel).first()

    def create(self, settings: AppSettingsModel) -> AppSettingsModel:
        """Persist a new settings record."""
        self.session.add(settings)
        self.session.flush()
        return settings

    def update(self, settings: AppSettingsModel) -> AppSettingsModel:
        """Persist changes made to the settings record."""
        self.session.flush()
        return settings
