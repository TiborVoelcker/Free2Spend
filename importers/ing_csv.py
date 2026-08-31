"""ING "Umsatzanzeige" CSV exports.

What the format contains, and why it is read this way, is in
docs/implementation.md section 3.1.2.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta

from engine import BalanceAnchor, Transaction
from importers import csv_table, german
from importers.csv_table import CsvTable, Row
from importers.errors import ParseError, RowError
from importers.statement import ImportedStatement

HEADER_PREFIX = "Buchung;"
CURRENCY = "EUR"

BOOKING = "Buchung"
VALUE_DATE = "Wertstellungsdatum"
COUNTERPARTY = "Auftraggeber/Empfänger"
KIND = "Buchungstext"
PURPOSE = "Verwendungszweck"
BALANCE = "Saldo"
AMOUNT = "Betrag"


def read(path: str) -> ImportedStatement:
    with open(path, "rb") as handle:
        return parse(handle.read())


def parse(payload: bytes) -> ImportedStatement:
    table = csv_table.read(payload, header_starts_with=HEADER_PREFIX)
    table.require_columns(BOOKING, COUNTERPARTY, KIND, PURPOSE, AMOUNT)

    entries, row_errors = _read_entries(table)
    entries = _oldest_first(entries, table)

    start, end = _period(table)
    return ImportedStatement(
        encoding=table.encoding,
        bank=table.meta_value("Bank"),
        iban=table.meta_value("IBAN"),
        account_name=table.meta_value("Kontoname"),
        period_start=start,
        period_end=end,
        transactions=tuple(entry.transaction for entry in entries),
        anchors=_anchors(entries, table),
        row_errors=tuple(row_errors),
        balance_discrepancies=() if row_errors else _verify_chain(entries),
    )


@dataclass(frozen=True)
class _Entry:
    transaction: Transaction
    balance_cents: int
    line_number: int


def _read_entries(table: CsvTable) -> tuple[list[_Entry], list[RowError]]:
    """Bad rows are collected, not raised: a first run against an unfamiliar
    export should report everything wrong with it at once."""
    entries: list[_Entry] = []
    errors: list[RowError] = []
    seen: Counter[str] = Counter()

    for row in table.rows:
        try:
            entries.append(_read_entry(row, table, seen))
        except ParseError as exc:
            errors.append(RowError(row.line_number, str(exc), row.raw))
    return entries, errors


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


def _oldest_first(entries: list[_Entry], table: CsvTable) -> list[_Entry]:
    descending = "absteigend" in table.meta_value("Sortierung").lower()
    if not descending and len(entries) > 1:
        descending = entries[0].transaction.booking_date > entries[-1].transaction.booking_date
    return list(reversed(entries)) if descending else entries


def _anchors(entries: list[_Entry], table: CsvTable) -> tuple[BalanceAnchor, ...]:
    """Two per import: the balance before the window, and after it.

    The opening balance is stated nowhere in the file; it is the first row's
    running balance less that row's own amount.
    """
    if not entries or not table.has_column(BALANCE):
        return ()
    first, last = entries[0], entries[-1]
    source = f"ING {table.meta_value('Kontoname') or table.meta_value('IBAN')}".strip()
    return (
        BalanceAnchor(
            as_of=first.transaction.booking_date - timedelta(days=1),
            balance_cents=first.balance_cents - first.transaction.amount_cents,
            source=f"{source} opening",
        ),
        BalanceAnchor(
            as_of=last.transaction.booking_date,
            balance_cents=last.balance_cents,
            source=f"{source} closing",
        ),
    )


def _verify_chain(entries: list[_Entry]) -> tuple[str, ...]:
    """Every row carries a running balance, so a misread amount shows up at once."""
    problems = []
    for previous, current in zip(entries, entries[1:]):
        expected = previous.balance_cents + current.transaction.amount_cents
        if expected != current.balance_cents:
            problems.append(
                f"line {current.line_number}: running balance is {current.balance_cents} "
                f"cents, expected {expected}"
            )
    return tuple(problems)


def _period(table: CsvTable) -> tuple[date | None, date | None]:
    """`Zeitraum;01.03.2026 - 31.08.2026`, the range an import replaces."""
    parts = [part.strip() for part in table.meta_value("Zeitraum").split("-")]
    if len(parts) != 2:
        return None, None
    try:
        return german.parse_date(parts[0]), german.parse_date(parts[1])
    except ParseError:
        return None, None
