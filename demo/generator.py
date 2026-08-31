"""Generate a plausible German year of transactions.

Deterministic for a given seed, so a run can be reproduced exactly and asserted
against in tests.

The shape of the year is chosen to exercise the things that matter:

- salary and rent land at the *end of the preceding month*, which is the case
  the rollover day exists for (docs/strategy.md section 4.1)
- an annual insurance premium, so a large non-monthly cost is present
- a windfall and a nasty surprise, so at least one period is unusually good and
  one unusually bad
- fun spending sized close to the surplus, so free-to-spend hovers rather than
  climbing forever
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from engine.dates import add_month, clamp_day, subtract_month
from engine.model import Classification, Transaction
from engine.period import period_containing

# Monthly rhythm. Day-of-month, amount in cents, description, counterparty.
# Salary and rent are placed in the *preceding* month; see _month_transactions.
SALARY_DAY, SALARY_CENTS = 29, 320_000
RENT_DAY, RENT_CENTS = 30, 115_000

FIXED_MONTHLY = [
    (1, -42_000, "Shared flat account", "Gemeinschaftskonto"),
    (3, -3_500, "Gym membership", "FitnessFirst"),
    (5, -2_200, "Mobile phone", "Telekom"),
    (8, -1_299, "Streaming", "Netflix"),
    (8, -1_099, "Music streaming", "Spotify"),
    (15, -9_500, "Utilities", "Stadtwerke"),
]

GROCERY_DAYS = (2, 9, 16, 23, 30)
GROCERY_RANGE = (4_500, 9_500)
GROCERY_SHOPS = ("REWE", "Edeka", "Aldi", "Lidl", "Denns Biomarkt")

# Fun spending is drawn from this catalogue until a period's target is reached.
FUN_CATALOGUE = [
    ("Restaurant", "Trattoria Bella", 2_200, 6_500),
    ("Drinks", "Zum Anker", 1_500, 4_000),
    ("Cinema", "CineStar", 1_200, 2_600),
    ("Books", "Thalia", 900, 3_500),
    ("Clothes", "Zalando", 2_500, 12_000),
    ("Coffee", "Kaffeeroesterei", 350, 900),
    ("Concert tickets", "Eventim", 3_500, 9_000),
    ("Takeaway", "Lieferando", 1_400, 3_200),
    ("Electronics", "MediaMarkt", 3_000, 18_000),
    ("Day trip", "Deutsche Bahn", 1_900, 7_500),
]

FUN_TARGET_CENTS = 100_000
FUN_TARGET_SPREAD = 22_000
FUN_TARGET_FLOOR = 30_000
# Stop filling once the remainder is small, rather than trailing off in coffees.
FUN_STOP_BELOW = 1_500

OPENING_BALANCE_ID = "demo-0000"

# One-off events, keyed by how many months into the generated year they fall.
ANNUAL_INSURANCE_MONTH = 3  # March, by calendar month
ANNUAL_INSURANCE_CENTS = -28_800
WINDFALL_OFFSET, WINDFALL_CENTS = 4, 48_000  # travel expenses reimbursed
SURPRISE_OFFSET, SURPRISE_CENTS = 7, -82_000  # the car breaks down

# A holiday saved up for over two lean periods, then booked. This is the
# strategy working as designed (docs/strategy.md section 2.2), and it drives
# free-to-spend negative for one period so the overspent case is visible.
SAVING_UP_OFFSETS = (8, 9)
SAVING_UP_FACTOR = 0.45
SPLURGE_OFFSET, SPLURGE_CENTS = 10, -290_000


class _Ids:
    """Stable, sequential transaction ids."""

    def __init__(self) -> None:
        self._n = 0

    def next(self) -> str:
        self._n += 1
        return f"demo-{self._n:04d}"


def _month_transactions(
    year: int,
    month: int,
    offset: int,
    rng: random.Random,
    ids: _Ids,
    splurge_cents: int = SPLURGE_CENTS,
) -> list[Transaction]:
    """Everything belonging to one budget month.

    Salary and rent are dated into the preceding calendar month, which is what
    makes this data worth testing against.
    """
    out: list[Transaction] = []
    previous_year, previous_month = subtract_month(year, month)

    out.append(
        Transaction(
            ids.next(),
            clamp_day(previous_year, previous_month, SALARY_DAY),
            SALARY_CENTS,
            "Salary",
            "Arbeitgeber GmbH",
        )
    )
    out.append(
        Transaction(
            ids.next(),
            clamp_day(previous_year, previous_month, RENT_DAY),
            -RENT_CENTS,
            "Rent",
            "Hausverwaltung Meyer",
        )
    )

    for day, cents, description, counterparty in FIXED_MONTHLY:
        out.append(
            Transaction(ids.next(), clamp_day(year, month, day), cents, description, counterparty)
        )

    for day in GROCERY_DAYS:
        out.append(
            Transaction(
                ids.next(),
                clamp_day(year, month, day),
                -rng.randint(*GROCERY_RANGE),
                "Groceries",
                rng.choice(GROCERY_SHOPS),
            )
        )

    if month == ANNUAL_INSURANCE_MONTH:
        out.append(
            Transaction(
                ids.next(),
                clamp_day(year, month, 12),
                ANNUAL_INSURANCE_CENTS,
                "Car insurance, annual premium",
                "HUK-Coburg",
            )
        )

    if offset == WINDFALL_OFFSET:
        out.append(
            Transaction(
                ids.next(),
                clamp_day(year, month, 18),
                WINDFALL_CENTS,
                "Travel expenses reimbursed",
                "Arbeitgeber GmbH",
            )
        )

    if offset == SURPRISE_OFFSET:
        out.append(
            Transaction(
                ids.next(),
                clamp_day(year, month, 14),
                SURPRISE_CENTS,
                "Car repair",
                "Autohaus Schneider",
            )
        )

    out.extend(_fun_transactions(year, month, offset, rng, ids, splurge_cents))
    return out


def _fun_transactions(
    year: int,
    month: int,
    offset: int,
    rng: random.Random,
    ids: _Ids,
    splurge_cents: int = SPLURGE_CENTS,
) -> list[Transaction]:
    """Fill a period's fun budget with purchases that fit inside it.

    Only items the remaining budget can afford are ever drawn, and filling stops
    while a small remainder is still unspent. Both keep the loop from trailing
    off into a long tail of tiny purchases.
    """
    target = max(FUN_TARGET_FLOOR, int(rng.gauss(FUN_TARGET_CENTS, FUN_TARGET_SPREAD)))
    if offset in SAVING_UP_OFFSETS:
        target = int(target * SAVING_UP_FACTOR)

    out: list[Transaction] = []
    remaining = target
    while remaining >= FUN_STOP_BELOW:
        affordable = [item for item in FUN_CATALOGUE if item[2] <= remaining]
        description, counterparty, low, high = rng.choice(affordable)
        amount = rng.randint(low, min(high, remaining))
        out.append(
            Transaction(
                ids.next(),
                clamp_day(year, month, rng.randint(1, 26)),
                -amount,
                description,
                counterparty,
                Classification.FUN,
            )
        )
        remaining -= amount

    if offset == SPLURGE_OFFSET and splurge_cents:
        out.append(
            Transaction(
                ids.next(),
                clamp_day(year, month, 6),
                splurge_cents,
                "Holiday, two weeks Mallorca",
                "TUI",
                Classification.FUN,
            )
        )

    return out


def generate_year(
    *,
    rollover_day: int = 27,
    first_month: tuple[int, int] = (2025, 9),
    months: int = 12,
    opening_balance_cents: int = 240_000,
    splurge_cents: int = SPLURGE_CENTS,
    seed: int = 20260101,
) -> list[Transaction]:
    """A year of transactions, sorted by date.

    The opening balance is dated one day before the first period begins, so the
    first period is complete rather than showing a bootstrap row. That is why
    `rollover_day` is needed here: the data is generated for a chosen rollover
    day.
    """
    rng = random.Random(seed)
    ids = _Ids()

    year, month = first_month
    transactions: list[Transaction] = []
    for offset in range(months):
        transactions.extend(
            _month_transactions(year, month, offset, rng, ids, splurge_cents)
        )
        year, month = add_month(year, month)

    first_period = period_containing(min(t.date for t in transactions), rollover_day)
    transactions.append(
        Transaction(
            OPENING_BALANCE_ID,
            first_period.start - timedelta(days=1),
            opening_balance_cents,
            "Opening balance",
            "",
        )
    )

    return sorted(transactions, key=lambda t: (t.date, t.id))


def last_date(transactions: list[Transaction]) -> date:
    """The most recent transaction date. Useful as `today` for a demo run."""
    return max(t.date for t in transactions)


def first_budget_date(transactions: list[Transaction]) -> date:
    """The earliest date that is a real budget event.

    The opening balance stands in for a balance anchor (docs/implementation.md
    section 3.3), which M1 has no representation for yet. It is not a budget
    event, so reporting should not begin with the period it happens to fall in.
    """
    return min(t.date for t in transactions if t.id != OPENING_BALANCE_ID)
