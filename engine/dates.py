"""Date helpers. Dates only, never timestamps (docs/stack.md section 4)."""

from __future__ import annotations

import calendar
from datetime import date


def clamp_day(year: int, month: int, day: int) -> date:
    """The given day of the month, clamped to the last day if the month is shorter.

    A rollover day of 31 therefore lands on 28 or 29 in February, rather than
    being an error.
    """
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last))


def add_month(year: int, month: int) -> tuple[int, int]:
    """The (year, month) one month after the given one."""
    return (year + 1, 1) if month == 12 else (year, month + 1)


def subtract_month(year: int, month: int) -> tuple[int, int]:
    """The (year, month) one month before the given one."""
    return (year - 1, 12) if month == 1 else (year, month - 1)
