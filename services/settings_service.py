"""Settings service.

Owns validation for working-hour settings (AI_RULES.md Rule 4: business
logic — including validation — belongs in Service, never in the UI or
Repository).
"""

from datetime import time

from core.exceptions import InvalidSettingsException
from core.logger import logger
from models.app_settings import AppSettingsModel
from repositories.settings_repository import SettingsRepository


class SettingsService:
    """Reads and validates updates to working-hour settings."""

    def __init__(self, settings_repo: SettingsRepository) -> None:
        """Initialize the service with a settings repository.

        Args:
            settings_repo: Repository for reading/writing settings.
        """
        self.settings_repo = settings_repo

    def get_settings(self) -> AppSettingsModel:
        """Fetch the current settings, creating a default row if none exists.

        Returns:
            The current AppSettingsModel.
        """
        settings = self.settings_repo.get()
        if settings is None:
            logger.info("Belum ada settings, membuat default")
            settings = self.settings_repo.create(AppSettingsModel())
        return settings

    def update_settings(
        self,
        work_start: time,
        work_end: time,
        friday_end: time,
        tolerance_late: int,
        tolerance_leave: int,
    ) -> AppSettingsModel:
        """Validate and persist new working-hour settings.

        Args:
            work_start: New standard (Mon-Thu) work start time.
            work_end: New standard (Mon-Thu) work end time.
            friday_end: New Friday work end time.
            tolerance_late: Grace period (minutes) before LATE is triggered.
            tolerance_leave: Grace period (minutes) before EARLY is triggered.

        Returns:
            The updated AppSettingsModel.

        Raises:
            InvalidSettingsException: If any value fails validation.
        """
        self._validate(work_start, work_end, friday_end, tolerance_late, tolerance_leave)

        settings = self.get_settings()
        settings.work_start = work_start
        settings.work_end = work_end
        settings.friday_end = friday_end
        settings.tolerance_late = tolerance_late
        settings.tolerance_leave = tolerance_leave

        updated = self.settings_repo.update(settings)
        logger.info("Settings berhasil diperbarui")
        return updated

    def _validate(
        self,
        work_start: time,
        work_end: time,
        friday_end: time,
        tolerance_late: int,
        tolerance_leave: int,
    ) -> None:
        """Validate working-hour settings before they are persisted."""
        if work_start >= work_end:
            raise InvalidSettingsException(
                "Jam masuk harus lebih awal dari jam pulang (Senin-Kamis)."
            )
        if work_start >= friday_end:
            raise InvalidSettingsException(
                "Jam masuk harus lebih awal dari jam pulang hari Jumat."
            )
        if tolerance_late < 0:
            raise InvalidSettingsException("Toleransi telat tidak boleh negatif.")
        if tolerance_leave < 0:
            raise InvalidSettingsException(
                "Toleransi pulang cepat tidak boleh negatif."
            )