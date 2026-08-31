"""Read an ING "Umsatzanzeige" CSV export.

The format, as of 2026:

    Umsatzanzeige;Datei erstellt am: 31.08.2026 15:33
    <blank>
    IBAN;DE26 ...
    Kontoname;Girokonto
    Bank;ING
    Kunde;...
    Zeitraum;28.02.2026 - 31.08.2026
    Saldo;12.345,67;EUR
    <blank>
    Sortierung;Datum absteigend
    <blank>
    In der CSV-Datei finden Sie alle bereits gebuchten Umsaetze. ...
    <blank>
    Buchung;Wertstellungsdatum;Auftraggeber/Empfaenger;Buchungstext;Verwendungszweck;Saldo;Waehrung;Betrag;Waehrung
    31.08.2026;31.08.2026;My Company GmbH;Gehalt/Rente;LOHN / GEHALT 08/26;12.345,67;EUR;1.234,56;EUR

Three things about it are worth knowing:

- **It carries a running balance on every row.** That is far better than the
  single balance anchor docs/implementation.md section 3.3 assumes: the whole
  chain can be verified, and the opening balance of the window derived exactly.
- **Only booked entries are included.** The preamble says so. There are no
  pending entries to later change or duplicate.
- **The header row repeats `Waehrung` twice**, so columns are located by
  position, not by a dict of names.

This importer never raises on a bad row. It collects the failures and returns
them, because the first run against a real export should report everything
wrong with it at once rather than dying on line 800.
"""

from __future__ import annotations

import csv
import hashlib
import io
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta

from engine.model import Transaction
from importers.parsing import ParseError, parse_german_cents, parse_german_date

TABLE_HEADER_PREFIX = "Buchung;"
OPENING_BALANCE_ID = "ing-opening-balance"
ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")
EXPECTED_CURRENCY = "EUR"


@dataclass(frozen=True)
class RowError:
    line_number: int
    message: str
    raw: str

    def __str__(self) -> str:
        return f"line {self.line_number}: {self.message}"


@dataclass(frozen=True)
class ImportedStatement:
    """One CSV export, parsed."""

    encoding: str
    bank: str = ""
    iban: str = ""
    account_name: str = ""
    period_start: date | None = None
    period_end: date | None = None
    statement_balance_cents: int | None = None
    opening_balance_cents: int = 0
    transactions: tuple[Transaction, ...] = ()
    row_errors: tuple[RowError, ...] = ()
    balance_discrepancies: tuple[str, ...] = field(default=())

    @property
    def is_clean(self) -> bool:
        return not self.row_errors and not self.balance_discrepancies

    @property
    def booked(self) -> tuple[Transaction, ...]:
        """Every transaction except the synthetic opening balance."""
        return tuple(t for t in self.transactions if t.id != OPENING_BALANCE_ID)


def read(path: str) -> ImportedStatement:
    """Parse an export from disk."""
    with open(path, "rb") as handle:
        return parse(handle.read())


def parse(payload: bytes) -> ImportedStatement:
    text, encoding = _decode(payload)
    lines = text.splitlines()

    header_index = _find_table_header(lines)
    meta = _parse_meta(lines[:header_index])
    columns = _column_positions(next(csv.reader([lines[header_index]], delimiter=";")))

    rows, row_errors = _parse_rows(lines[header_index + 1 :], header_index + 2, columns)
    rows = _oldest_first(rows, meta)

    discrepancies = _verify_balance_chain(rows) if not row_errors else ()
    opening = rows[0].balance_cents - rows[0].transaction.amount_cents if rows else 0

    transactions = tuple(row.transaction for row in rows)
    if transactions:
        transactions = (_opening_transaction(opening, transactions[0].booking_date), *transactions)

    statement_balance = _meta_cents(meta, "Saldo")
    if statement_balance is not None and rows:
        total = sum(t.amount_cents for t in transactions)
        if total != statement_balance:
            discrepancies = (
                *discrepancies,
                f"transactions sum to {total} cents but the statement says {statement_balance}",
            )

    period_start, period_end = _parse_period(meta)
    return ImportedStatement(
        encoding=encoding,
        bank=_meta_str(meta, "Bank"),
        iban=_meta_str(meta, "IBAN"),
        account_name=_meta_str(meta, "Kontoname"),
        period_start=period_start,
        period_end=period_end,
        statement_balance_cents=statement_balance,
        opening_balance_cents=opening,
        transactions=transactions,
        row_errors=tuple(row_errors),
        balance_discrepancies=tuple(discrepancies),
    )


# --- internals ---------------------------------------------------------------


@dataclass(frozen=True)
class _Row:
    transaction: Transaction
    balance_cents: int
    line_number: int


def _decode(payload: bytes) -> tuple[str, str]:
    """ING exports are not consistently encoded; try the plausible ones in turn."""
    for encoding in ENCODINGS:
        try:
            return payload.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ParseError(f"could not decode the file as any of {', '.join(ENCODINGS)}")


def _find_table_header(lines: list[str]) -> int:
    for index, line in enumerate(lines):
        if line.startswith(TABLE_HEADER_PREFIX):
            return index
    raise ParseError(f"no table header: expected a line starting with {TABLE_HEADER_PREFIX!r}")


def _parse_meta(lines: list[str]) -> dict[str, list[str]]:
    meta: dict[str, list[str]] = {}
    for line in lines:
        if ";" not in line:
            continue
        key, *values = next(csv.reader([line], delimiter=";"))
        if key.strip():
            meta.setdefault(key.strip(), [v.strip() for v in values])
    return meta


def _meta_str(meta: dict[str, list[str]], key: str) -> str:
    values = meta.get(key) or [""]
    return values[0]


def _meta_cents(meta: dict[str, list[str]], key: str) -> int | None:
    raw = _meta_str(meta, key)
    try:
        return parse_german_cents(raw) if raw else None
    except ParseError:
        return None


def _parse_period(meta: dict[str, list[str]]) -> tuple[date | None, date | None]:
    """`Zeitraum;28.02.2026 - 31.08.2026`. This is the range an import replaces."""
    raw = _meta_str(meta, "Zeitraum")
    parts = [part.strip() for part in raw.split("-")]
    if len(parts) != 2:
        return None, None
    try:
        return parse_german_date(parts[0]), parse_german_date(parts[1])
    except ParseError:
        return None, None


def _column_positions(header: list[str]) -> dict[str, int]:
    """First occurrence of each name wins, because `Waehrung` appears twice."""
    positions: dict[str, int] = {}
    for index, name in enumerate(header):
        positions.setdefault(name.strip(), index)
    required = ["Buchung", "Auftraggeber/Empfänger", "Buchungstext", "Verwendungszweck", "Betrag"]
    missing = [name for name in required if name not in positions]
    if missing:
        raise ParseError(f"table header is missing {', '.join(missing)}; got {header}")
    return positions


def _parse_rows(
    lines: list[str],
    first_line_number: int,
    columns: dict[str, int],
) -> tuple[list[_Row], list[RowError]]:
    rows: list[_Row] = []
    errors: list[RowError] = []
    seen: Counter[str] = Counter()

    for offset, line in enumerate(lines):
        line_number = first_line_number + offset
        if not line.strip():
            continue
        try:
            rows.append(_parse_row(line, line_number, columns, seen))
        except ParseError as exc:
            errors.append(RowError(line_number, str(exc), line))
    return rows, errors


def _parse_row(
    line: str,
    line_number: int,
    columns: dict[str, int],
    seen: Counter[str],
) -> _Row:
    cells = next(csv.reader([line], delimiter=";"))

    def cell(name: str) -> str:
        index = columns[name]
        if index >= len(cells):
            raise ParseError(f"row has {len(cells)} columns, needs at least {index + 1}")
        return cells[index].strip()

    where = f"line {line_number}"
    booking = parse_german_date(cell("Buchung"), where=where)
    value_raw = cell("Wertstellungsdatum") if "Wertstellungsdatum" in columns else ""
    value_date = parse_german_date(value_raw, where=where) if value_raw else None

    amount = parse_german_cents(cell("Betrag"), where=where)
    balance = parse_german_cents(cell("Saldo"), where=where) if "Saldo" in columns else 0

    currency_index = columns["Betrag"] + 1
    if currency_index < len(cells):
        currency = cells[currency_index].strip()
        if currency and currency != EXPECTED_CURRENCY:
            raise ParseError(f"currency is {currency!r}, only {EXPECTED_CURRENCY} is supported")

    counterparty = cell("Auftraggeber/Empfänger")
    purpose = cell("Verwendungszweck")
    kind = cell("Buchungstext")

    return _Row(
        transaction=Transaction(
            id=_identifier(booking, amount, counterparty, purpose, seen),
            booking_date=booking,
            amount_cents=amount,
            description=purpose,
            counterparty=counterparty,
            value_date=value_date,
            kind=kind,
        ),
        balance_cents=balance,
        line_number=line_number,
    )


def _identifier(
    booking: date,
    amount: int,
    counterparty: str,
    purpose: str,
    seen: Counter[str],
) -> str:
    """A stable id derived from content, plus an occurrence number.

    The export carries no transaction id. Two identical purchases on the same
    day are two transactions, not one, so the occurrence number is what keeps
    them distinct while the id stays the same across re-imports of the same
    file.
    """
    key = f"{booking.isoformat()}|{amount}|{counterparty}|{purpose}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    seen[digest] += 1
    return f"ing-{digest}-{seen[digest]}"


def _oldest_first(rows: list[_Row], meta: dict[str, list[str]]) -> list[_Row]:
    """The export is normally newest first; the balance chain reads forwards."""
    descending = "absteigend" in _meta_str(meta, "Sortierung").lower()
    if not descending and len(rows) > 1:
        descending = rows[0].transaction.booking_date > rows[-1].transaction.booking_date
    return list(reversed(rows)) if descending else rows


def _verify_balance_chain(rows: list[_Row]) -> tuple[str, ...]:
    """Each row's running balance must be the previous one plus its own amount.

    This is the check that catches a misparsed amount immediately, and it is
    only possible because the export carries a balance on every row.
    """
    problems = []
    for previous, current in zip(rows, rows[1:]):
        expected = previous.balance_cents + current.transaction.amount_cents
        if expected != current.balance_cents:
            problems.append(
                f"line {current.line_number}: running balance is {current.balance_cents} cents, "
                f"expected {expected}"
            )
    return tuple(problems)


def _opening_transaction(opening_cents: int, first_booking: date) -> Transaction:
    """The balance before the window, as a transaction.

    M2 has no representation for a balance anchor, so the opening balance is
    carried as a synthetic entry dated the day before the window opens. Without
    it every free-to-spend in the window would be short by the whole opening
    balance.
    """
    return Transaction(
        id=OPENING_BALANCE_ID,
        booking_date=first_booking - timedelta(days=1),
        amount_cents=opening_cents,
        description="Opening balance",
        reviewed=True,
    )
