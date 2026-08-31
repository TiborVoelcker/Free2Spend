"""The generic reader. It knows a header line and rows, and nothing else."""

import pytest

from importers import csv_table
from importers.errors import ParseError


def table_of(text: str, **kwargs):
    lines, encoding = csv_table.decode_lines(text.encode("utf-8"))
    return csv_table.table_from(lines, encoding, **kwargs)


def test_anything_above_the_header_line_is_ignored():
    text = "Report;created today\n\nIBAN;DE26\n\nAlpha;Beta\n1;2\n"
    table = table_of(text, header_line=4)
    assert table.header == ("Alpha", "Beta")
    assert len(table.rows) == 1


def test_rows_carry_their_line_number():
    table = table_of("junk\nAlpha;Beta\n1;2\n3;4\n", header_line=1)
    assert [row.line_number for row in table.rows] == [3, 4]


def test_a_repeated_column_name_resolves_to_the_first():
    """Bank headers repeat names; positions are what matter."""
    table = table_of("Alpha;Unit;Beta;Unit\n1;EUR;2;EUR\n")
    assert table.column("Unit") == 1
    assert table.column("Beta") == 2


def test_a_short_row_is_rejected_with_its_shape():
    table = table_of("A;B;C\n1;2\n")
    with pytest.raises(ParseError, match="needs at least 3"):
        table.rows[0].at(2)


def test_require_columns_names_what_is_missing():
    table = table_of("Alpha;Beta\n1;2\n")
    with pytest.raises(ParseError, match="Delta"):
        table.require_columns("Alpha", "Delta")


def test_a_header_line_outside_the_file_is_rejected():
    with pytest.raises(ParseError, match="outside a file"):
        table_of("Alpha;Beta\n1;2\n", header_line=9)


def test_quoting_is_honoured():
    table = table_of('Alpha;Beta\n"one;two";3\n')
    assert table.rows[0].cells == ("one;two", "3")


def test_encodings_are_tried_in_turn():
    lines, encoding = csv_table.decode_lines("A;B\nÜ;1\n".encode("cp1252"))
    assert encoding == "cp1252"
    assert csv_table.table_from(lines, encoding).rows[0].cells[0] == "Ü"


def test_an_undecodable_file_is_rejected():
    with pytest.raises(ParseError, match="could not decode"):
        csv_table.decode_lines(b"\xff\xfe\x00", encodings=("utf-8",))
