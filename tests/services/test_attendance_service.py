"""Unit tests for AttendanceService's pure business-rule methods.

These methods don't touch the repositories, so we pass None for both
dependencies -- this is intentional, not a shortcut.
"""

from datetime import date, time

from core.enums.attendance import CheckInStatus, CheckOutStatus
from services.attendance_service import AttendanceService


def _service() -> AttendanceService:
    return AttendanceService(attendance_repo=None, settings_repo=None)


def test_calculate_late_returns_late_status():
    minutes, status = _service().calculate_late(
        time(7, 45), time(7, 30), tolerance_minutes=0
    )

    assert minutes == 15
    assert status == CheckInStatus.LATE


def test_calculate_late_within_tolerance_is_on_time():
    minutes, status = _service().calculate_late(
        time(7, 35), time(7, 30), tolerance_minutes=10
    )

    assert minutes == 0
    assert status == CheckInStatus.ON_TIME


def test_calculate_late_missing_check_in_is_missing_status():
    minutes, status = _service().calculate_late(
        None, time(7, 30), tolerance_minutes=0
    )

    assert minutes == 0
    assert status == CheckInStatus.MISSING


def test_calculate_early_leave_detects_early():
    minutes, status = _service().calculate_early_leave(
        time(15, 0), time(15, 30), tolerance_minutes=0
    )

    assert minutes == 30
    assert status == CheckOutStatus.EARLY


def test_calculate_early_leave_within_tolerance_is_normal():
    minutes, status = _service().calculate_early_leave(
        time(15, 25), time(15, 30), tolerance_minutes=10
    )

    assert minutes == 0
    assert status == CheckOutStatus.NORMAL


def test_calculate_work_duration():
    duration = _service().calculate_work_duration(time(7, 30), time(15, 30))

    assert duration == 480


def test_calculate_work_duration_none_when_check_out_missing():
    assert _service().calculate_work_duration(time(7, 30), None) is None


def test_resolve_work_end_uses_friday_end_on_friday():
    # 2026-07-31 is a Friday.
    result = _service().resolve_work_end(date(2026, 7, 31), time(15, 30), time(13, 0))

    assert result == time(13, 0)


def test_resolve_work_end_uses_normal_end_on_weekday():
    # 2026-07-27 is a Monday.
    result = _service().resolve_work_end(date(2026, 7, 27), time(15, 30), time(13, 0))

    assert result == time(15, 30)