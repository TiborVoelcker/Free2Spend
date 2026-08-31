"""The ledger: transactions, anchors, and the arithmetic over them.

Nothing here is stored. `free-to-spend = balance - pockets` is a definition
recomputed from the balance at each rollover, not an accumulator
(docs/strategy.md section 2.1).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date

from engine.model import BalanceAnchor, Classification, Transaction
from engine.period import Period, periods_between
from engine.summary import PeriodSummary


@dataclass(frozen=True)
class Discrepancy:
    """Two anchors that the transactions between them do not explain."""

    earlier: BalanceAnchor
    later: BalanceAnchor
    expected_cents: int
    actual_cents: int

    @property
    def difference_cents(self) -> int:
        return self.actual_cents - self.expected_cents

    def __str__(self) -> str:
        return (
            f"{self.earlier.as_of} to {self.later.as_of}: transactions explain "
            f"{self.expected_cents} cents but the bank says {self.actual_cents}"
        )


@dataclass(frozen=True)
class Ledger:
    """Everything known about an account, and every number derived from it."""

    transactions: tuple[Transaction, ...] = ()
    anchors: tuple[BalanceAnchor, ...] = field(default=())

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "transactions",
            tuple(sorted(self.transactions, key=lambda t: (t.booking_date, t.id))),
        )
        object.__setattr__(self, "anchors", tuple(sorted(self.anchors, key=lambda a: a.as_of)))

    # --- what is in it ---

    def __bool__(self) -> bool:
        return bool(self.transactions)

    @property
    def first_date(self) -> date | None:
        return self.transactions[0].booking_date if self.transactions else None

    @property
    def last_date(self) -> date | None:
        return self.transactions[-1].booking_date if self.transactions else None

    # --- balances ---

    def balance_before(self, moment: date) -> int:
        """The balance as `moment` begins; transactions dated `moment` are excluded.

        Counted from the latest anchor before `moment`, which keeps the span of
        transactions being trusted as short as the anchors allow.
        """
        base = 0
        since: date | None = None
        for anchor in self.anchors:
            if anchor.as_of >= moment:
                break
            base, since = anchor.balance_cents, anchor.as_of
        return base + sum(
            t.amount_cents
            for t in self.transactions
            if (since is None or t.booking_date > since) and t.booking_date < moment
        )

    def reconcile(self) -> list[Discrepancy]:
        """Where the transactions between two anchors do not explain the change.

        A discrepancy means transactions are missing. This is the only real
        defence against silent data loss (docs/implementation.md section 3.3).
        """
        problems = []
        for earlier, later in zip(self.anchors, self.anchors[1:]):
            moved = sum(
                t.amount_cents
                for t in self.transactions
                if earlier.as_of < t.booking_date <= later.as_of
            )
            expected = earlier.balance_cents + moved
            if expected != later.balance_cents:
                problems.append(Discrepancy(earlier, later, expected, later.balance_cents))
        return problems

    # --- the numbers ---

    def free_to_spend(self, period: Period) -> int:
        """The period's free-to-spend, fixed at its start.

        This is `balance - pockets`. Pockets arrive in M3; until then there are
        none, so it is exactly the balance at the rollover.
        """
        return self.balance_before(period.start)

    def fun_spend(self, period: Period, as_of: date | None = None) -> int:
        """Fun spending within the period, as a positive number.

        A refund classified as fun reduces the total, which makes this net
        spending rather than gross.
        """
        total = 0
        for transaction in self.transactions:
            if transaction.classification is not Classification.FUN:
                continue
            if not period.contains(transaction.booking_date):
                continue
            if as_of is not None and transaction.booking_date > as_of:
                continue
            total -= transaction.amount_cents
        return total

    def remaining_free_to_spend(self, period: Period, as_of: date | None = None) -> int:
        """What is left of the period's free-to-spend. The number the user looks at.

        May be negative: that means the pockets claim more than the account
        holds, and it is deliberately not clamped (docs/strategy.md section 4.2).
        """
        return self.free_to_spend(period) - self.fun_spend(period, as_of)

    # --- periods ---

    def summarise_period(self, period: Period, as_of: date | None = None) -> PeriodSummary:
        income = 0
        required = 0
        for transaction in self.transactions:
            if not period.contains(transaction.booking_date):
                continue
            if transaction.classification is not Classification.REQUIRED:
                continue
            if transaction.amount_cents > 0:
                income += transaction.amount_cents
            else:
                required -= transaction.amount_cents

        opening = self.free_to_spend(period)
        fun = self.fun_spend(period, as_of)
        return PeriodSummary(
            period=period,
            free_to_spend_cents=opening,
            income_cents=income,
            required_spend_cents=required,
            fun_spend_cents=fun,
            remaining_free_to_spend_cents=opening - fun,
            closing_balance_cents=self.balance_before(period.end),
        )

    def summarise(
        self,
        rollover_day: int,
        today: date,
        since: date | None = None,
    ) -> list[PeriodSummary]:
        """One summary per period, from the earliest transaction through `today`.

        `since` starts the report later; earlier transactions still count toward
        the balance, they simply are not given a row.

        `today` is a parameter rather than read from a clock, so a whole
        simulated year runs through the engine reproducibly.
        """
        if not self.transactions:
            return []
        first = self.first_date
        if since is not None:
            first = max(first, since)
        if first > today:
            return []
        periods = periods_between(first, today, rollover_day)
        return [self.summarise_period(period, today) for period in periods]


def ledger_of(transactions: Iterable[Transaction], anchors: Iterable[BalanceAnchor] = ()) -> Ledger:
    """Convenience constructor that accepts any iterables."""
    return Ledger(tuple(transactions), tuple(anchors))
