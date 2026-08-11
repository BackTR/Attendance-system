from datetime import date

from core.exceptions import DuplicateHolidayException
from core.logger import logger
from models.holiday import HolidayModel
from repositories.holiday_repository import HolidayRepository


class HolidayService:
    """Validates and manages declared holidays (hari libur nasional/cuti bersama)."""

    def __init__(self, holiday_repo: HolidayRepository) -> None:
        """Initialize the service with a required repository.

        Args:
            holiday_repo: Repository for reading/writing holiday rows.
        """
        self.holiday_repo = holiday_repo

    def get_all(self) -> list[HolidayModel]:
        """Fetch every declared holiday, ordered by date."""
        return self.holiday_repo.get_all()

    def declare_holiday(self, tanggal: date, keterangan: str) -> HolidayModel:
        """Validate and declare a new holiday.

        Args:
            tanggal: The holiday date.
            keterangan: Description (e.g. "Hari Raya Idul Fitri").

        Returns:
            The newly created HolidayModel.

        Raises:
            ValueError: If keterangan is empty.
            DuplicateHolidayException: If the date is already declared.
        """
        keterangan = keterangan.strip()
        if not keterangan:
            raise ValueError("Keterangan hari libur tidak boleh kosong.")

        if self.holiday_repo.get_by_date(tanggal) is not None:
            raise DuplicateHolidayException(
                f"Tanggal {tanggal} sudah terdaftar sebagai hari libur."
            )

        created = self.holiday_repo.create(
            HolidayModel(tanggal=tanggal, keterangan=keterangan)
        )
        logger.info(f"Hari libur baru: {tanggal} - {keterangan}")
        return created

    def remove_holiday(self, holiday_id: int) -> None:
        """Remove a declared holiday by id.

        Raises:
            ValueError: If no holiday exists with that id.
        """
        holiday = self.holiday_repo.get_by_id(holiday_id)
        if holiday is None:
            raise ValueError("Hari libur tidak ditemukan.")
        self.holiday_repo.delete(holiday)
        logger.info(f"Hari libur dihapus: {holiday.tanggal}")