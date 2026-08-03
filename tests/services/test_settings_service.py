"""Tests for SettingsService."""

from datetime import time

import pytest

from core.exceptions import InvalidSettingsException
from repositories.settings_repository import SettingsRepository
from services.settings_service import SettingsService


def test_get_settings_creates_default_when_none_exists(db_session):
    service = SettingsService(SettingsRepository(db_session))

    settings = service.get_settings()

    assert settings.work_start == time(7, 30)
    assert settings.work_end == time(15, 30)
    assert settings.friday_end == time(13, 0)


def test_update_settings_persists_valid_values(db_session):
    service = SettingsService(SettingsRepository(db_session))

    updated = service.update_settings(time(8, 0), time(16, 0), time(13, 30), 10, 5)

    assert updated.work_start == time(8, 0)
    assert updated.tolerance_late == 10

    # Re-fetch to confirm it was actually persisted, not just returned.
    refetched = service.get_settings()
    assert refetched.work_start == time(8, 0)


def test_update_settings_rejects_work_start_after_work_end(db_session):
    service = SettingsService(SettingsRepository(db_session))

    with pytest.raises(InvalidSettingsException):
        service.update_settings(time(16, 0), time(8, 0), time(13, 0), 0, 0)


def test_update_settings_rejects_work_start_after_friday_end(db_session):
    service = SettingsService(SettingsRepository(db_session))

    with pytest.raises(InvalidSettingsException):
        service.update_settings(time(14, 0), time(16, 0), time(13, 0), 0, 0)


def test_update_settings_rejects_negative_tolerance(db_session):
    service = SettingsService(SettingsRepository(db_session))

    with pytest.raises(InvalidSettingsException):
        service.update_settings(time(7, 30), time(15, 30), time(13, 0), -1, 0)