"""German bank export conventions: dates and amounts."""

from __future__ import annotations

import re
from datetime import date, datetime

from importers.errors import ParseError


def parse_date(raw: str, *, where: str = "") -> date:
    """`31.08.2026` to a date."""
    try:
        day, month, year = (int(part) for part in raw.strip().split("."))
        return date(year, month, day)
    except (ValueError, TypeError) as exc:
        raise ParseError(f"not a date: {raw!r}{_at(where)}") from exc


def parse_cents(raw: str, *, where: str = "") -> int:
    """`-1.234,56` to -123456, with integer arithmetic so nothing rounds."""
    text = raw.strip().replace(" ", "").replace(" ", "")
    if not text:
        raise ParseError(f"empty amount{_at(where)}")

    # Exactly one leading sign. `lstrip("+-")` would swallow several and read
    # "--5,00" as -5.00 rather than rejecting it.
    sign = 1
    if text[0] in "+-":
        sign = -1 if text[0] == "-" else 1
        text = text[1:]

    whole, _, fraction = text.replace(".", "").partition(",")
    fraction = (fraction + "00")[:2]
    if not whole.isdigit() or not fraction.isdigit():
        raise ParseError(f"not an amount: {raw!r}{_at(where)}")
    return sign * (int(whole) * 100 + int(fraction))


def _at(where: str) -> str:
    return f" ({where})" if where else ""


TIMESTAMP = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}):(\d{2})")


def find_timestamp(text: str) -> datetime | None:
    """The first `31.08.2026 15:33` anywhere in a line, if there is one."""
    match = TIMESTAMP.search(text)
    if not match:
        return None
    day, month, year, hour, minute = (int(part) for part in match.groups())
    try:
        return datetime(year, month, day, hour, minute)
    except ValueError:
        return None
