"""What every importer produces, whatever the bank or the format."""

from __future__ import annotations

from dataclasses import dataclass

from engine import BalanceAnchor, Ledger, Transaction
from importers.errors import RowError


@dataclass(frozen=True)
class ImportedStatement:
    encoding: str = ""
    bank: str = ""
    iban: str = ""
    account_name: str = ""
    transactions: tuple[Transaction, ...] = ()
    anchors: tuple[BalanceAnchor, ...] = ()
    row_errors: tuple[RowError, ...] = ()
    balance_discrepancies: tuple[str, ...] = ()

    @property
    def ledger(self) -> Ledger:
        return Ledger(self.transactions, self.anchors)

    @property
    def is_clean(self) -> bool:
        return not self.row_errors and not self.balance_discrepancies

    @property
    def opening_balance_cents(self) -> int:
        return self.anchors[0].balance_cents if self.anchors else 0

    @property
    def closing_balance_cents(self) -> int:
        return self.anchors[-1].balance_cents if self.anchors else 0
