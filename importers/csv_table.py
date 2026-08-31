"""Reading a delimited table out of a text file.

It knows only that a file decodes to lines, that one of those lines is the
header, and that the rest are rows. Where the header is, and what anything
above it means, is the importer's business — banks differ, and some have no
preamble at all.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass

from importers.errors import ParseError

DEFAULT_ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")


@dataclass(frozen=True)
class Row:
    line_number: int
    cells: tuple[str, ...]

    def at(self, index: int) -> str:
        if index >= len(self.cells):
            raise ParseError(f"row has {len(self.cells)} columns, needs at least {index + 1}")
        return self.cells[index].strip()

    @property
    def raw(self) -> str:
        return ";".join(self.cells)


@dataclass(frozen=True)
class CsvTable:
    encoding: str
    header: tuple[str, ...]
    rows: tuple[Row, ...]

    def column(self, name: str) -> int:
        """Position of a column. The first occurrence wins, since names repeat."""
        try:
            return self.header.index(name)
        except ValueError as exc:
            raise ParseError(f"no column {name!r}; got {list(self.header)}") from exc

    def has_column(self, name: str) -> bool:
        return name in self.header

    def require_columns(self, *names: str) -> None:
        missing = [name for name in names if not self.has_column(name)]
        if missing:
            raise ParseError(f"table is missing {', '.join(missing)}; got {list(self.header)}")


def decode_lines(
    payload: bytes,
    encodings: tuple[str, ...] = DEFAULT_ENCODINGS,
) -> tuple[list[str], str]:
    """Exports are not consistently encoded; try the plausible ones in turn."""
    for encoding in encodings:
        try:
            return payload.decode(encoding).splitlines(), encoding
        except UnicodeDecodeError:
            continue
    raise ParseError(f"could not decode the file as any of {', '.join(encodings)}")


def split_line(line: str, delimiter: str = ";") -> list[str]:
    """One delimited line to cells, honouring quoting."""
    return next(csv.reader([line], delimiter=delimiter))


def table_from(
    lines: list[str],
    encoding: str,
    *,
    header_line: int = 0,
    delimiter: str = ";",
) -> CsvTable:
    """The table starting at `header_line`, a zero-based index into `lines`.

    Defaults to the first line, which is the case for a file that is only a
    table. Anything above the header is ignored here.
    """
    if not 0 <= header_line < len(lines):
        raise ParseError(f"header line {header_line} is outside a file of {len(lines)} lines")

    rows = [
        Row(header_line + 2 + offset, tuple(split_line(line, delimiter)))
        for offset, line in enumerate(lines[header_line + 1 :])
        if line.strip()
    ]
    return CsvTable(
        encoding=encoding,
        header=tuple(cell.strip() for cell in split_line(lines[header_line], delimiter)),
        rows=tuple(rows),
    )
