"""The ledger: transactions, anchors, and the balances derived from them."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from engine.model import BalanceAnchor, Classification, Transaction
from engine.period import Period


class Ledger:
    """Everything known about an account."""

    def __init__(
        self,
        transactions: Iterable[Transaction] = (),
        anchors: Iterable[BalanceAnchor] = (),
    ) -> None:
        self.transactions = tuple(sorted(transactions, key=lambda t: (t.booking_date, t.id)))
        # Sorted by balance as well as date so that two anchors claiming the same
        # day resolve the same way every time. They contradict each other, and
        # `reconcile` reports it; picking silently and differently would not.
        self.anchors = tuple(sorted(anchors, key=lambda a: (a.as_of, a.balance_cents)))

    def __bool__(self) -> bool:
        return bool(self.transactions)

    @property
    def first_date(self) -> date | None:
        return self.transactions[0].booking_date if self.transactions else None

    @property
    def last_date(self) -> date | None:
        return self.transactions[-1].booking_date if self.transactions else None

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

    def reconcile(self) -> list[str]:
        """Where the transactions between two anchors do not explain the change.

        A discrepancy means transactions are missing. This is the only real
        defence against silent data loss.
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
                problems.append(
                    f"{earlier.as_of} to {later.as_of}: transactions explain "
                    f"{expected} cents but the bank says {later.balance_cents}"
                )
        return problems

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

    def required_spend(self, period: Period) -> int:
        total = 0
        for transaction in self.transactions:
            if transaction.classification is not Classification.REQUIRED:
                continue
            if period.contains(transaction.booking_date) and transaction.amount_cents < 0:
                total -= transaction.amount_cents
        return total

    def income(self, period: Period) -> int:
        total = 0
        for transaction in self.transactions:
            if transaction.classification is not Classification.REQUIRED:
                continue
            if period.contains(transaction.booking_date) and transaction.amount_cents > 0:
                total += transaction.amount_cents
        return total
