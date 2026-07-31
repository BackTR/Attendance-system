from enum import Enum


class CheckInStatus(str, Enum):
    """
    Status absensi masuk.
    """

    ON_TIME = "ON_TIME"
    LATE = "LATE"
    MISSING = "MISSING"


class CheckOutStatus(str, Enum):
    """
    Status absensi pulang.
    """

    NORMAL = "NORMAL"
    EARLY = "EARLY"
    MISSING = "MISSING"


class AttendanceStatus(str, Enum):
    """
    Status kehadiran harian.
    """

    PRESENT = "PRESENT"

    ABSENT = "ABSENT"

    INCOMPLETE = "INCOMPLETE"