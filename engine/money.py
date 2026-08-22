"""Money is integer cents, everywhere. Never floats (docs/stack.md section 4)."""

from __future__ import annotations


def format_euros(cents: int) -> str:
    """Render cents as euros, e.g. -123456 -> '-1,234.56'."""
    sign = "-" if cents < 0 else ""
    whole, remainder = divmod(abs(cents), 100)
    return f"{sign}{whole:,}.{remainder:02d}"
