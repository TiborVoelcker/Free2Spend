"""The ING adapter, against a fixture with a real running-balance chain."""

from datetime import datetime
from pathlib import Path

import pytest

from importers.errors import ParseError
from importers.importer import Importer
from importers.ing_csv import IngCsvImporter
from importers.statement import ImportedStatement, ImportFailed

FIXTURE = Path(__file__).parent / "fixtures" / "ing_sample.csv"
RAW = FIXTURE.read_bytes()


def parse(payload: bytes):
    return IngCsvImporter().parse(payload)


@pytest.fixture(scope="module")
def statement():
    result = parse(RAW)
    assert isinstance(result, ImportedStatement)
    return result


def test_the_ing_adapter_is_an_importer():
    assert isinstance(IngCsvImporter(), Importer)


def test_the_fixture_parses(statement):
    assert len(statement.transactions) == 62
    assert statement.created_at == datetime(2026, 8, 31, 15, 33)


def test_amounts_come_from_betrag_not_saldo(statement):
    """The header repeats `Waehrung`, so columns are found by position."""
    salary = [t for t in statement.transactions if t.kind == "Gehalt/Rente"]
    assert {t.amount_cents for t in salary} == {285_000}


def test_both_dates_are_kept_and_can_differ(statement):
    differing = [t for t in statement.transactions if t.value_date != t.booking_date]
    assert differing, "the fixture should contain at least one Wertstellung mismatch"
    assert differing[0].value_date > differing[0].booking_date


def test_the_opening_balance_is_an_anchor_not_a_transaction(statement):
    """It is what the bank said, not something that happened."""
    opening, closing = statement.anchors
    assert opening.as_of < min(t.booking_date for t in statement.transactions)
    assert opening.balance_cents == 312_045
    assert closing.balance_cents == 1_120_566


def test_the_anchors_and_the_transactions_agree(statement):
    """The end-to-end check: the window's own numbers explain its endpoints."""
    assert statement.ledger.reconcile() == []


def test_a_latin1_and_a_utf8_export_parse_identically(statement):
    utf8 = RAW.decode("cp1252").encode("utf-8")
    assert parse(utf8).transactions == statement.transactions


def test_ids_are_stable_across_reimports(statement):
    assert [t.id for t in parse(RAW).transactions] == [t.id for t in statement.transactions]


def test_identical_purchases_on_one_day_stay_distinct():
    """Two coffees at the same shop are two transactions, not one."""
    body = (
        "Buchung;Wertstellungsdatum;Auftraggeber/Empfänger;Buchungstext;"
        "Verwendungszweck;Saldo;Währung;Betrag;Währung\n"
        "01.03.2026;01.03.2026;CAFE;Lastschrift;KAFFEE;97,00;EUR;-3,50;EUR\n"
        "01.03.2026;01.03.2026;CAFE;Lastschrift;KAFFEE;100,50;EUR;-3,50;EUR\n"
    )
    result = parse(body.encode("utf-8"))
    assert len(result.transactions) == 2
    assert len({t.id for t in result.transactions}) == 2


def test_a_misread_amount_is_caught_by_the_running_balance():
    corrupted = RAW.decode("cp1252").replace("-700,00;EUR", "-70,00;EUR", 1)
    result = parse(corrupted.encode("cp1252"))
    assert isinstance(result, ImportFailed)
    assert len(result.problems) == 1


def test_every_bad_row_is_reported_not_just_the_first():
    """A first run against a real export should report all of it at once."""
    lines = RAW.decode("cp1252").splitlines()
    for index in (-1, -2):
        lines[index] = lines[index].replace(";EUR;", ";EUR;nonsense;", 1)
    result = parse("\n".join(lines).encode("cp1252"))
    assert isinstance(result, ImportFailed)
    assert len(result.problems) == 2
    assert all(problem.line and problem.context for problem in result.problems)


def test_the_export_order_is_taken_from_the_running_balance():
    """Not from the dates: they carry no order within a day, and 8 of this
    fixture's 54 dates hold more than one row. Not from the `Sortierung`
    header either: whether the numbers add up should not rest on a German word.
    """
    text = RAW.decode("cp1252")
    head, _, table = text.partition("Buchung;Wertstellungsdatum")
    header, *rows = ("Buchung;Wertstellungsdatum" + table).splitlines()
    flipped = head + "\n".join([header, *reversed([r for r in rows if r.strip()])])

    result = parse(flipped.encode("cp1252"))
    assert isinstance(result, ImportedStatement)
    assert result.transactions == parse(RAW).transactions
    assert result.anchors == parse(RAW).anchors


def test_a_foreign_currency_row_is_rejected():
    body = (
        "Buchung;Wertstellungsdatum;Auftraggeber/Empfänger;Buchungstext;"
        "Verwendungszweck;Saldo;Währung;Betrag;Währung\n"
        "01.03.2026;01.03.2026;SHOP;Lastschrift;X;97,00;EUR;-3,50;USD\n"
    )
    result = parse(body.encode("utf-8"))
    assert isinstance(result, ImportFailed)
    assert "USD" in result.problems[0].message


def test_a_file_without_a_table_is_rejected():
    with pytest.raises(ParseError, match="no table header"):
        parse(b"Umsatzanzeige;irgendwas\n\nIBAN;DE00\n")
