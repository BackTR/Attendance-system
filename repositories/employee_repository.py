from sqlalchemy import select
from sqlalchemy.orm import Session

from models.employee import EmployeeModel


class EmployeeRepository:
    """Handles database access (CRUD only) for EmployeeModel."""

    def __init__(self, session: Session) -> None:
        """Initialize repository with an active database session.

        Args:
            session: Active SQLAlchemy session.
        """
        self.session = session

    def get_by_id(self, employee_id: int) -> EmployeeModel | None:
        """Fetch an employee by primary key."""
        return self.session.get(EmployeeModel, employee_id)

    def get_by_code(self, employee_code: str) -> EmployeeModel | None:
        """Fetch an employee by their unique employee_code."""
        stmt = select(EmployeeModel).where(
            EmployeeModel.employee_code == employee_code
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_all_active(self) -> list[EmployeeModel]:
        """Fetch all active employees."""
        stmt = select(EmployeeModel).where(EmployeeModel.aktif.is_(True))
        return list(self.session.execute(stmt).scalars().all())

    def create(self, employee: EmployeeModel) -> EmployeeModel:
        """Persist a new employee record."""
        self.session.add(employee)
        self.session.flush()
        return employee

    def update(self, employee: EmployeeModel) -> EmployeeModel:
        """Persist changes made to an existing employee record."""
        self.session.flush()
        return employee

    def delete(self, employee: EmployeeModel) -> None:
        """Remove an employee record."""
        self.session.delete(employee)
        self.session.flush()
