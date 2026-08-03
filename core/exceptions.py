"""Custom exceptions for AIS.

Using specific exception types (instead of bare Exception) makes error
handling in Services and UI explicit and predictable (AI_RULES.md Rule 19).
"""


class AISException(Exception):
    """Base exception for all AIS-specific errors."""


class InvalidExcelFormatException(AISException):
    """Raised when an uploaded Excel file does not match the expected schema."""


class EmployeeNotFoundException(AISException):
    """Raised when an employee record cannot be found."""

class InvalidSettingsException(AISException):
    """Raised when submitted working-hour settings fail validation."""

class EmployeeAlreadyExistsException(AISException):
    """Raised when creating an employee with a duplicate employee_code."""