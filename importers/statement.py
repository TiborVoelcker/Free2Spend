"""What every importer produces, whatever the bank or the format."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from engine import BalanceAnchor, Ledger, Transaction
from importers.errors import Problem


@dataclass(frozen=True)
class ImportedStatement:
    """A successful import. If you have one of these, it parsed and it adds up."""

    encoding: str = ""
    created_at: datetime | None = None
    transactions: tuple[Transaction, ...] = ()
    anchors: tuple[BalanceAnchor, ...] = ()

    @property
    def ledger(self) -> Ledger:
        return Ledger(self.transactions, self.anchors)

    @property
    def opening_balance_cents(self) -> int:
        return self.anchors[0].balance_cents if self.anchors else 0

    @property
    def closing_balance_cents(self) -> int:
        return self.anchors[-1].balance_cents if self.anchors else 0


@dataclass(frozen=True)
class ImportFailed:
    """A failed import, with everything wrong with the file, not just the first."""

    problems: tuple[Problem, ...] = ()


ImportResult = ImportedStatement | ImportFailed
