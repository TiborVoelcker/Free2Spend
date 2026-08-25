import pytest

from engine import format_euros


@pytest.mark.parametrize(
    ("cents", "expected"),
    [(0, "0.00"), (5, "0.05"), (-5, "-0.05"), (-123_456, "-1,234.56")],
)
def test_format_euros(cents, expected):
    assert format_euros(cents) == expected
