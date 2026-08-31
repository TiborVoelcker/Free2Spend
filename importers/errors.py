"""Failures an importer reports rather than raises."""

from __future__ import annotations

from dataclasses import dataclass


class ParseError(ValueError):
    """A field or a file could not be read."""


@dataclass(frozen=True)
class RowError:
    """One unreadable row. The rest of the file is still parsed."""

    line_number: int
    message: str
    raw: str

    def __str__(self) -> str:
        return f"line {self.line_number}: {self.message}"
