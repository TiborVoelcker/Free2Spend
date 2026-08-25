"""Date helpers. Dates only, never timestamps (docs/stack.md section 4)."""

from __future__ import annotations

import calendar
from datetime import date


def clamp_day(year: int, month: int, day: int) -> date:
    """A day of the month, counted from either end.

    A positive day counts from the start and clamps to the last day of a shorter
    month, so 31 lands on 28 or 29 in February rather than being an error.

    A negative day counts back from the end, as list indexing does: -1 is the
    last day of the month, -2 the day before it. That tracks the month end
    instead of a fixed number, which is what a rollover day placed relative to
    month end needs when salaries land on the last banking day.
    """
    last = calendar.monthrange(year, month)[1]
    if day < 0:
        day = last + 1 + day
    return date(year, month, max(1, min(day, last)))


def add_month(year: int, month: int) -> tuple[int, int]:
    """The (year, month) one month after the given one."""
    return (year + 1, 1) if month == 12 else (year, month + 1)


def subtract_month(year: int, month: int) -> tuple[int, int]:
    """The (year, month) one month before the given one."""
    return (year - 1, 12) if month == 1 else (year, month - 1)
