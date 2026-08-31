"""Reading a delimited table that sits below a metadata preamble.

Bank exports are not plain CSV: a block of `Key;Value` lines comes first, the
table header is somewhere below it, and column names are not necessarily
unique. This module knows only that shape. Which line starts the table, what
the columns mean, and how to read a row are the importer's business.
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
    meta: dict[str, tuple[str, ...]]
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

    def meta_value(self, key: str) -> str:
        values = self.meta.get(key) or ("",)
        return values[0]


def read(
    payload: bytes,
    *,
    header_starts_with: str,
    delimiter: str = ";",
    encodings: tuple[str, ...] = DEFAULT_ENCODINGS,
) -> CsvTable:
    text, encoding = decode(payload, encodings)
    lines = text.splitlines()

    header_index = _find_header(lines, header_starts_with)
    header = tuple(cell.strip() for cell in _split(lines[header_index], delimiter))

    rows = []
    for offset, line in enumerate(lines[header_index + 1 :]):
        if line.strip():
            rows.append(
                Row(header_index + 2 + offset, tuple(_split(line, delimiter)))
            )

    return CsvTable(
        encoding=encoding,
        meta=_parse_meta(lines[:header_index], delimiter),
        header=header,
        rows=tuple(rows),
    )


def decode(payload: bytes, encodings: tuple[str, ...] = DEFAULT_ENCODINGS) -> tuple[str, str]:
    """Exports are not consistently encoded; try the plausible ones in turn."""
    for encoding in encodings:
        try:
            return payload.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ParseError(f"could not decode the file as any of {', '.join(encodings)}")


def _split(line: str, delimiter: str) -> list[str]:
    return next(csv.reader([line], delimiter=delimiter))


def _find_header(lines: list[str], prefix: str) -> int:
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            return index
    raise ParseError(f"no table header: expected a line starting with {prefix!r}")


def _parse_meta(lines: list[str], delimiter: str) -> dict[str, tuple[str, ...]]:
    meta: dict[str, tuple[str, ...]] = {}
    for line in lines:
        if delimiter not in line:
            continue
        key, *values = _split(line, delimiter)
        if key.strip():
            meta.setdefault(key.strip(), tuple(value.strip() for value in values))
    return meta
