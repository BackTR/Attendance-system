"""Employee management service.

Owns validation for employee creation and activation status changes
(AI_RULES.md Rule 4: business logic in Service, Rule 20: validate all
user input).
"""

from core.exceptions import EmployeeAlreadyExistsException
from core.logger import logger
from models.employee import EmployeeModel
from repositories.employee_repository import EmployeeRepository


class EmployeeService:
    """Validates and manages employee records."""

    def __init__(self, employee_repo: EmployeeRepository) -> None:
        """Initialize the service with a required repository.

        Args:
            employee_repo: Repository for reading/writing employee rows.
        """
        self.employee_repo = employee_repo

    def get_all(self) -> list[EmployeeModel]:
        """Fetch every employee, active and inactive."""
        return self.employee_repo.get_all()

    def get_all_active(self) -> list[EmployeeModel]:
        """Fetch only active employees."""
        return self.employee_repo.get_all_active()

    def create_employee(
        self,
        employee_code: str,
        nama: str,
        jabatan: str | None = None,
        unit: str | None = None,
    ) -> EmployeeModel:
        """Validate and create a new employee.

        Args:
            employee_code: Unique employee code (case-insensitive, will
                be stored uppercased).
            nama: Full name.
            jabatan: Job title (optional).
            unit: Work unit/department (optional).

        Returns:
            The newly created EmployeeModel.

        Raises:
            ValueError: If employee_code or nama is empty.
            EmployeeAlreadyExistsException: If employee_code is already used.
        """
        employee_code = employee_code.strip().upper()
        nama = nama.strip()

        if not employee_code:
            raise ValueError("Kode pegawai tidak boleh kosong.")
        if not nama:
            raise ValueError("Nama pegawai tidak boleh kosong.")

        if self.employee_repo.get_by_code(employee_code) is not None:
            raise EmployeeAlreadyExistsException(
                f"Kode pegawai '{employee_code}' sudah terdaftar."
            )

        employee = EmployeeModel(
            employee_code=employee_code,
            nama=nama,
            jabatan=jabatan.strip() if jabatan else None,
            unit=unit.strip() if unit else None,
        )
        created = self.employee_repo.create(employee)
        logger.info(f"Employee baru dibuat: {employee_code}")
        return created

    def set_active_status(self, employee_id: int, aktif: bool) -> EmployeeModel:
        """Activate or deactivate an employee (soft delete).

        Args:
            employee_id: Primary key of the employee.
            aktif: New active status.

        Returns:
            The updated EmployeeModel.

        Raises:
            ValueError: If no employee exists with that id.
        """
        employee = self.employee_repo.get_by_id(employee_id)
        if employee is None:
            raise ValueError("Pegawai tidak ditemukan.")

        employee.aktif = aktif
        updated = self.employee_repo.update(employee)
        logger.info(f"Status aktif {employee.employee_code} diubah menjadi {aktif}")
        return updated