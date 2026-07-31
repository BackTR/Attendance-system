"""Weekday enum for Indonesian day names.

Replaces free-string day constants (e.g. MONDAY = "Senin") per
AI_RULES.md Rule 12: use Enum instead of free strings.
"""

from enum import Enum


class Weekday(str, Enum):
    """Indonesian weekday names, ordered to match date.weekday() (0=Monday)."""

    MONDAY = "Senin"
    TUESDAY = "Selasa"
    WEDNESDAY = "Rabu"
    THURSDAY = "Kamis"
    FRIDAY = "Jumat"
    SATURDAY = "Sabtu"
    SUNDAY = "Minggu"

    @classmethod
    def from_index(cls, weekday_index: int) -> "Weekday":
        """Convert Python's date.weekday() (0=Monday..6=Sunday) to a Weekday.

        Args:
            weekday_index: Result of date.weekday().

        Returns:
            Corresponding Weekday enum member.
        """
        return list(cls)[weekday_index]
