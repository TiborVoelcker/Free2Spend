"""ING "Umsatzanzeige" CSV exports. Format quirks are noted in AGENTS.md."""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import pairwise

from engine import BalanceAnchor, Transaction
from importers import csv_table, german
from importers.csv_table import CsvTable, Row
from importers.errors import ParseError, Problem
from importers.statement import ImportedStatement, ImportFailed, ImportResult

HEADER_PREFIX = "Buchung;"
CURRENCY = "EUR"

BOOKING = "Buchung"
VALUE_DATE = "Wertstellungsdatum"
COUNTERPARTY = "Auftraggeber/Empfänger"
KIND = "Buchungstext"
PURPOSE = "Verwendungszweck"
BALANCE = "Saldo"
AMOUNT = "Betrag"


class IngCsvImporter:
    """The ING adapter, over `csv_table` and `german`."""

    name = "ING Umsatzanzeige (CSV)"

    def read(self, path: str) -> ImportResult:
        with open(path, "rb") as handle:
            return self.parse(handle.read())

    def parse(self, payload: bytes) -> ImportResult:
        lines, encoding = csv_table.decode_lines(payload)
        table = csv_table.table_from(lines, encoding, header_line=_find_header(lines))
        table.require_columns(BOOKING, COUNTERPARTY, KIND, PURPOSE, AMOUNT)

        entries, problems = _read_entries(table)
        if not problems:
            entries, problems = _in_balance_order(entries)
        if problems:
            return ImportFailed(tuple(problems))

        return ImportedStatement(
            encoding=encoding,
            created_at=_created_at(lines),
            transactions=tuple(entry.transaction for entry in entries),
            anchors=_anchors(entries),
        )


@dataclass(frozen=True)
class _Entry:
    transaction: Transaction
    balance_cents: int
    line_number: int


def _find_header(lines: list[str]) -> int:
    """ING puts a preamble above the table, of no fixed length."""
    for index, line in enumerate(lines):
        if line.startswith(HEADER_PREFIX):
            return index
    raise ParseError(f"no table header: expected a line starting with {HEADER_PREFIX!r}")


def _created_at(lines: list[str]):
    """When the export was made. The only thing the preamble is read for."""
    for line in lines:
        if (found := german.find_timestamp(line)) is not None:
            return found
    return None


def _read_entries(table: CsvTable) -> tuple[list[_Entry], list[Problem]]:
    """Bad rows are collected, not raised: a first run against an unfamiliar
    export should report everything wrong with it at once."""
    entries: list[_Entry] = []
    problems: list[Problem] = []
    seen: Counter[str] = Counter()

    for row in table.rows:
        try:
            entries.append(_read_entry(row, table, seen))
        except ParseError as exc:
            problems.append(Problem(str(exc), line=row.line_number, context=row.raw))
    return entries, problems


def _read_entry(row: Row, table: CsvTable, seen: Counter[str]) -> _Entry:
    where = f"line {row.line_number}"
    booking = german.parse_date(row.at(table.column(BOOKING)), where=where)
    amount = german.parse_cents(row.at(table.column(AMOUNT)), where=where)
    _check_currency(row, table.column(AMOUNT) + 1, where)

    value_date = None
    if table.has_column(VALUE_DATE):
        raw = row.at(table.column(VALUE_DATE))
        value_date = german.parse_date(raw, where=where) if raw else None

    balance = 0
    if table.has_column(BALANCE):
        balance = german.parse_cents(row.at(table.column(BALANCE)), where=where)

    counterparty = row.at(table.column(COUNTERPARTY))
    purpose = row.at(table.column(PURPOSE))

    return _Entry(
        transaction=Transaction(
            id=_identifier(booking, amount, counterparty, purpose, seen),
            booking_date=booking,
            amount_cents=amount,
            description=purpose,
            counterparty=counterparty,
            value_date=value_date,
            kind=row.at(table.column(KIND)),
        ),
        balance_cents=balance,
        line_number=row.line_number,
    )


def _check_currency(row: Row, index: int, where: str) -> None:
    if index >= len(row.cells):
        return
    currency = row.cells[index].strip()
    if currency and currency != CURRENCY:
        raise ParseError(f"currency is {currency!r}, only {CURRENCY} is supported ({where})")


def _identifier(
    booking: date, amount: int, counterparty: str, purpose: str, seen: Counter[str]
) -> str:
    """Content hash plus an occurrence number.

    The export carries no transaction id, and two identical purchases on one day
    are two transactions. The occurrence number keeps them distinct while the id
    stays stable across re-imports of the same file.
    """
    key = f"{booking.isoformat()}|{amount}|{counterparty}|{purpose}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    seen[digest] += 1
    return f"ing-{digest}-{seen[digest]}"


def _in_balance_order(entries: list[_Entry]) -> tuple[list[_Entry], list[Problem]]:
    """The entries oldest first, and any row whose running balance does not follow.

    The direction is taken from the balance itself rather than from the dates or
    the export's `Sortierung` header. The balance is the thing that has to add
    up, a one-day export gives the dates nothing to go on, and a German word in
    a header is a poor thing to trust the numbers to.
    """
    forwards = _chain_problems(entries)
    if not forwards:
        return entries, []

    backwards = list(reversed(entries))
    backwards_problems = _chain_problems(backwards)
    if not backwards_problems:
        return backwards, []

    # Neither direction adds up, so one amount was misread. The real order is
    # the one that explains more of the file; reporting the other would bury a
    # single bad row under a knock-on error for every row after it.
    if len(backwards_problems) < len(forwards):
        return backwards, backwards_problems
    return entries, forwards


def _anchors(entries: list[_Entry]) -> tuple[BalanceAnchor, ...]:
    """Two per import: the balance before the window, and after it.

    The opening balance is stated nowhere in the file; it is the first row's
    running balance less that row's own amount.
    """
    if not entries:
        return ()
    first, last = entries[0], entries[-1]
    return (
        BalanceAnchor(
            as_of=first.transaction.booking_date - timedelta(days=1),
            balance_cents=first.balance_cents - first.transaction.amount_cents,
            source="ING export, opening",
        ),
        BalanceAnchor(
            as_of=last.transaction.booking_date,
            balance_cents=last.balance_cents,
            source="ING export, closing",
        ),
    )


def _chain_problems(entries: list[_Entry]) -> list[Problem]:
    """Every row carries a running balance, so a misread amount shows up at once."""
    problems = []
    for previous, current in pairwise(entries):
        expected = previous.balance_cents + current.transaction.amount_cents
        if expected != current.balance_cents:
            problems.append(
                Problem(
                    f"running balance is {current.balance_cents} cents, expected {expected}",
                    line=current.line_number,
                )
            )
    return problems
