"""What an importer reports rather than raises."""

from __future__ import annotations

from dataclasses import dataclass


class ParseError(ValueError):
    """A field or a file could not be read."""


@dataclass(frozen=True)
class Problem:
    """One thing wrong with an export, reported alongside all the others."""

    message: str
    line: int | None = None
    context: str = ""

    def __str__(self) -> str:
        return f"line {self.line}: {self.message}" if self.line else self.message
