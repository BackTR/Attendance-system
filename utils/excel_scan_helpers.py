"""Low-level grid parsing helpers for the fingerprint-machine
'Data Scan Karyawan' Excel export format.

These are pure functions (no DB/session access) so they can be unit
tested in isolation from RawScanImportService's orchestration logic.
The layout is a pivoted per-employee grid: a header row (report
sequence number + name), followed by alternating date-label rows and
time-range rows, with the same 10 fixed "day slot" columns reused for
every week block.
"""

import re
from datetime import date, datetime, time, timedelta

SCAN_DAY_COLUMNS: tuple[int, ...] = (2, 6, 7, 9, 10, 15, 17, 20, 23, 24)
HEADER_NUMBER_COL = 9
HEADER_NAME_COL = 14

_DATE_CELL_RE = re.compile(r"^\d{2}-\d{2} \w{3}$")
_TIME_CELL_RE = re.compile(r"^\s*(\d{2}:\d{2})?\s*-\s*(\d{2}:\d{2})?\s*$")
_PERIOD_RE = re.compile(r"Dari\s+(\d{2}-\d{2}-\d{4})\s+s/d\s+(\d{2}-\d{2}-\d{4})")


def is_header_row(row: tuple) -> bool:
    """A header row marks the start of one employee's block."""
    if len(row) <= HEADER_NAME_COL:
        return False
    number = row[HEADER_NUMBER_COL]
    name = row[HEADER_NAME_COL]
    if not isinstance(name, str) or not name.strip():
        return False
    return isinstance(number, (int, float))


def is_date_row(row: tuple) -> bool:
    """A date row contains 'MM-DD Day' labels at the day-slot columns."""
    values = [v for v in row if isinstance(v, str) and v.strip()]
    if not values:
        return False
    return all(_DATE_CELL_RE.match(v.strip()) for v in values)


def is_time_row(row: tuple) -> bool:
    """A time row contains 'HH:MM-HH:MM' (or partial/absent) pairs."""
    values = [v for v in row if isinstance(v, str) and v.strip()]
    if not values:
        return False
    return all(_TIME_CELL_RE.match(v.strip()) for v in values)


def extract_header(row: tuple) -> tuple[int, str]:
    """Extract (report_sequence_number, employee_name) from a header row."""
    number = int(row[HEADER_NUMBER_COL])
    name = " ".join(str(row[HEADER_NAME_COL]).split())  # collapse whitespace/newlines
    return number, name


def extract_month_day(value: str) -> str | None:
    """Extract 'MM-DD' from a date cell like '11-20 Thu'."""
    stripped = value.strip()
    if not _DATE_CELL_RE.match(stripped):
        return None
    return stripped.split(" ")[0]


def parse_time_range(value: str) -> tuple[time | None, time | None]:
    """Parse a time cell like '06:11-16:02' into (check_in, check_out)."""
    match = _TIME_CELL_RE.match(value.strip())
    if not match:
        return None, None

    check_in_str, check_out_str = match.group(1), match.group(2)
    # Intentional: source Excel data has no timezone info, and the result
    # is truncated to .time() only, so tz-awareness is meaningless here.
    check_in = (
        datetime.strptime(check_in_str, "%H:%M").time()  # noqa: DTZ007
        if check_in_str
        else None
    )
    check_out = (
        datetime.strptime(check_out_str, "%H:%M").time()  # noqa: DTZ007
        if check_out_str
        else None
    )
    return check_in, check_out


def extract_report_period(all_text_values: list[str]) -> tuple[date, date] | None:
    """Find the report period ('Dari DD-MM-YYYY s/d DD-MM-YYYY') in cell text."""
    for text in all_text_values:
        match = _PERIOD_RE.search(text)
        if match:
            # Same reasoning: source has no timezone, result truncated to .date().
            start = datetime.strptime(match.group(1), "%d-%m-%Y").date()  # noqa: DTZ007
            end = datetime.strptime(match.group(2), "%d-%m-%Y").date()  # noqa: DTZ007
            return start, end
    return None


def build_date_lookup(start: date, end: date) -> dict[str, date]:
    """Map every 'MM-DD' in [start, end] to its real date (with year)."""
    lookup: dict[str, date] = {}
    current = start
    while current <= end:
        lookup[current.strftime("%m-%d")] = current
        current += timedelta(days=1)
    return lookup