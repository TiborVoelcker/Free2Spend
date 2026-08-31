import pytest

from importers.errors import ParseError
from importers.german import parse_cents, parse_date


@pytest.mark.parametrize(
    ("raw", "cents"),
    [
        ("1.234,56", 123_456),
        ("-700,00", -70_000),
        ("1.000.000,00", 100_000_000),
        ("0,05", 5),
        ("-0,05", -5),
        ("7", 700),  # no decimal part
        (" 12,3 ", 1_230),  # one decimal digit, padded
    ],
)
def test_parse_cents(raw, cents):
    assert parse_cents(raw) == cents


@pytest.mark.parametrize("raw", ["", "abc", "X.XXX,XX", "1,2,3", "--5,00", "-+5,00"])
def test_unparseable_amounts_are_rejected(raw):
    with pytest.raises(ParseError):
        parse_cents(raw)


def test_parse_error_names_the_row():
    with pytest.raises(ParseError, match="line 42"):
        parse_cents("nonsense", where="line 42")


def test_parse_date():
    assert parse_date("31.08.2026").isoformat() == "2026-08-31"


@pytest.mark.parametrize("raw", ["2026-08-31", "31/08/2026", "32.08.2026", ""])
def test_unparseable_dates_are_rejected(raw):
    with pytest.raises(ParseError):
        parse_date(raw)
