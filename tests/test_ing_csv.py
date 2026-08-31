"""The ING adapter, against a fixture with a real running-balance chain."""

from pathlib import Path

import pytest

from importers import ing_csv
from importers.errors import ParseError
from importers.importer import Importer
from importers.ing_csv import IngCsvImporter

FIXTURE = Path(__file__).parent / "fixtures" / "ing_sample.csv"
RAW = FIXTURE.read_bytes()


@pytest.fixture(scope="module")
def statement():
    return ing_csv.parse(RAW)


def test_the_fixture_parses_cleanly(statement):
    assert statement.is_clean
    assert statement.bank == "ING"
    assert len(statement.transactions) == 62


def test_amounts_come_from_betrag_not_saldo(statement):
    """The header repeats `Waehrung`, so columns are found by position."""
    salary = [t for t in statement.transactions if t.kind == "Gehalt/Rente"]
    assert {t.amount_cents for t in salary} == {285_000}


def test_both_dates_are_kept_and_can_differ(statement):
    differing = [t for t in statement.transactions if t.value_date != t.booking_date]
    assert differing, "the fixture should contain at least one Wertstellung mismatch"
    assert differing[0].value_date > differing[0].booking_date


def test_the_ing_adapter_is_an_importer():
    assert isinstance(IngCsvImporter(), Importer)


def test_the_opening_balance_is_an_anchor_not_a_transaction(statement):
    """It is what the bank said, not something that happened."""
    opening, closing = statement.anchors
    assert opening.as_of < min(t.booking_date for t in statement.transactions)
    assert opening.balance_cents == 312_045
    assert closing.balance_cents == 1_120_566
    assert all("Opening" not in t.description for t in statement.transactions)


def test_the_anchors_and_the_transactions_agree(statement):
    """The end-to-end check: the window's own numbers explain its endpoints."""
    assert statement.ledger.reconcile() == []


def test_a_latin1_and_a_utf8_export_parse_identically():
    utf8 = RAW.decode("cp1252").encode("utf-8")
    assert ing_csv.parse(utf8).transactions == ing_csv.parse(RAW).transactions


def test_ids_are_stable_across_reimports(statement):
    assert [t.id for t in ing_csv.parse(RAW).transactions] == [t.id for t in statement.transactions]


def test_identical_purchases_on_one_day_stay_distinct():
    """Two coffees at the same shop are two transactions, not one."""
    body = (
        "Buchung;Wertstellungsdatum;Auftraggeber/Empfänger;Buchungstext;"
        "Verwendungszweck;Saldo;Währung;Betrag;Währung\n"
        "01.03.2026;01.03.2026;CAFE;Lastschrift;KAFFEE;97,00;EUR;-3,50;EUR\n"
        "01.03.2026;01.03.2026;CAFE;Lastschrift;KAFFEE;100,50;EUR;-3,50;EUR\n"
    )
    parsed = ing_csv.parse(body.encode("utf-8"))
    assert len(parsed.transactions) == 2
    assert len({t.id for t in parsed.transactions}) == 2


def test_a_misread_amount_is_caught_by_the_running_balance():
    corrupted = RAW.decode("cp1252").replace("-700,00;EUR", "-70,00;EUR", 1)
    parsed = ing_csv.parse(corrupted.encode("cp1252"))
    assert parsed.balance_discrepancies
    assert not parsed.is_clean


def test_a_bad_row_is_collected_rather_than_raised():
    """A first run against a real export should report every problem at once."""
    lines = RAW.decode("cp1252").splitlines()
    lines[-1] = lines[-1].replace(";EUR;", ";EUR;nonsense;", 1)
    parsed = ing_csv.parse("\n".join(lines).encode("cp1252"))
    assert len(parsed.row_errors) == 1
    assert len(parsed.transactions) == 61


def test_ascending_and_descending_exports_agree():
    text = RAW.decode("cp1252")
    head, _, table = text.partition("Buchung;Wertstellungsdatum")
    header, *rows = ("Buchung;Wertstellungsdatum" + table).splitlines()
    flipped = head.replace("Datum absteigend", "Datum aufsteigend")
    flipped += "\n".join([header, *reversed([r for r in rows if r.strip()])])

    parsed = ing_csv.parse(flipped.encode("cp1252"))
    assert parsed.is_clean
    assert parsed.transactions == ing_csv.parse(RAW).transactions
    assert parsed.anchors == ing_csv.parse(RAW).anchors


def test_a_foreign_currency_row_is_rejected():
    body = (
        "Buchung;Wertstellungsdatum;Auftraggeber/Empfänger;Buchungstext;"
        "Verwendungszweck;Saldo;Währung;Betrag;Währung\n"
        "01.03.2026;01.03.2026;SHOP;Lastschrift;X;97,00;EUR;-3,50;USD\n"
    )
    parsed = ing_csv.parse(body.encode("utf-8"))
    assert len(parsed.row_errors) == 1
    assert "USD" in parsed.row_errors[0].message


def test_a_file_without_a_table_is_rejected():
    with pytest.raises(ParseError, match="no table header"):
        ing_csv.parse(b"Umsatzanzeige;irgendwas\n\nIBAN;DE00\n")
