"""The Free2Spend engine.

Pure functions over a transaction log. No I/O, no framework, and no clock —
"today" is always a parameter. See docs/stack.md section 4.
"""

from engine.ledger import (
    balance_before,
    free_to_spend,
    fun_spend,
    remaining_free_to_spend,
)
from engine.model import Classification, Transaction
from engine.money import format_euros
from engine.period import Period, period_containing, periods_between
from engine.summary import PeriodSummary, summarise

__all__ = [
    "Classification",
    "Period",
    "PeriodSummary",
    "Transaction",
    "balance_before",
    "format_euros",
    "free_to_spend",
    "fun_spend",
    "period_containing",
    "periods_between",
    "remaining_free_to_spend",
    "summarise",
]
