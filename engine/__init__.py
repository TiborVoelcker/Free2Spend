"""The Free2Spend engine.

Pure functions over a transaction log. No I/O, no framework, and no clock —
"today" is always a parameter. See docs/stack.md section 4.
"""

from engine.ledger import Discrepancy, Ledger, ledger_of
from engine.model import BalanceAnchor, Classification, Transaction
from engine.money import format_euros
from engine.period import Period, period_containing, periods_between
from engine.summary import PeriodSummary

__all__ = [
    "BalanceAnchor",
    "Classification",
    "Discrepancy",
    "Ledger",
    "Period",
    "PeriodSummary",
    "Transaction",
    "format_euros",
    "ledger_of",
    "period_containing",
    "periods_between",
]
