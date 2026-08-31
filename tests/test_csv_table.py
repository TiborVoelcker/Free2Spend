"""The generic reader: a delimited table below a metadata preamble."""

import pytest

from importers import csv_table
from importers.errors import ParseError

SAMPLE = (
    "Report;created 31.08.2026\n"
    "\n"
    "IBAN;DE26 0000\n"
    "Saldo;12.345,67;EUR\n"
    "\n"
    "Alpha;Beta;Unit;Gamma;Unit\n"
    "1;2;EUR;3;EUR\n"
    "4;5;EUR;6;EUR\n"
)


@pytest.fixture
def table():
    return csv_table.read(SAMPLE.encode("utf-8"), header_starts_with="Alpha;")


def test_the_preamble_is_read_as_metadata(table):
    assert table.meta_value("IBAN") == "DE26 0000"
    assert table.meta["Saldo"] == ("12.345,67", "EUR")


def test_a_repeated_column_name_resolves_to_the_first(table):
    """Bank headers repeat names; positions are what matter."""
    assert table.column("Unit") == 2
    assert table.column("Gamma") == 3


def test_rows_carry_their_line_number(table):
    assert [row.line_number for row in table.rows] == [7, 8]
    assert table.rows[0].at(table.column("Gamma")) == "3"


def test_a_short_row_is_rejected_with_its_shape():
    table = csv_table.read(b"A;B;C\n1;2\n", header_starts_with="A;")
    with pytest.raises(ParseError, match="needs at least 3"):
        table.rows[0].at(2)


def test_require_columns_names_what_is_missing(table):
    with pytest.raises(ParseError, match="Delta"):
        table.require_columns("Alpha", "Delta")


def test_encodings_are_tried_in_turn():
    payload = "Kopf;x\n\nA;B\nÜ;1\n".encode("cp1252")
    table = csv_table.read(payload, header_starts_with="A;")
    assert table.encoding == "cp1252"
    assert table.rows[0].cells[0] == "Ü"


def test_a_file_without_a_table_is_rejected():
    with pytest.raises(ParseError, match="no table header"):
        csv_table.read(b"Report;something\n\nIBAN;DE00\n", header_starts_with="Alpha;")
