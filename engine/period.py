"""Periods: the budget month, which runs rollover day to rollover day.

The rollover day may be given relative to the end of the month: -1 is the last
day, -2 the day before it. Salaries often land on the last banking day rather
than a fixed date, and a relative rollover day tracks that instead of drifting
against it as month lengths change.

A period is shown as its actual date range, not a month name
(docs/strategy.md section 7).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from engine.dates import add_month, clamp_day, subtract_month


@dataclass(frozen=True, order=True)
class Period:
    """A half-open range of dates: `start` is included, `end` is not."""

    start: date
    end: date

    def contains(self, moment: date) -> bool:
        return self.start <= moment < self.end

    @property
    def last_day(self) -> date:
        return self.end - timedelta(days=1)

    @property
    def label(self) -> str:
        return f"{self.start.isoformat()} to {self.last_day.isoformat()}"


def _validate(rollover_day: int) -> None:
    """A rollover day is 1..31 counting forward, or -1..-28 counting back.

    -28 is the furthest a negative day can go and still mean the same thing in
    February as in a 31 day month.
    """
    if not (1 <= rollover_day <= 31 or -28 <= rollover_day <= -1):
        raise ValueError(
            f"rollover_day must be 1..31 or -1..-28, got {rollover_day}"
        )


def _start_on_or_before(moment: date, rollover_day: int) -> date:
    candidate = clamp_day(moment.year, moment.month, rollover_day)
    if candidate <= moment:
        return candidate
    year, month = subtract_month(moment.year, moment.month)
    return clamp_day(year, month, rollover_day)


def _next_start(start: date, rollover_day: int) -> date:
    year, month = add_month(start.year, start.month)
    return clamp_day(year, month, rollover_day)


def period_containing(moment: date, rollover_day: int) -> Period:
    """The period that `moment` falls into."""
    _validate(rollover_day)
    start = _start_on_or_before(moment, rollover_day)
    return Period(start, _next_start(start, rollover_day))


def next_period(period: Period, rollover_day: int) -> Period:
    _validate(rollover_day)
    return Period(period.end, _next_start(period.end, rollover_day))


def periods_between(first: date, last: date, rollover_day: int) -> list[Period]:
    """Every period touching the inclusive date range `first`..`last`."""
    _validate(rollover_day)
    if last < first:
        return []
    periods = [period_containing(first, rollover_day)]
    while periods[-1].end <= last:
        periods.append(next_period(periods[-1], rollover_day))
    return periods
