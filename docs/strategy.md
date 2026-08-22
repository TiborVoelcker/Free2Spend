# Free2Spend — Strategy

Status: draft, evolving. This document describes the *financial strategy* the app
implements. It deliberately says nothing about technology, storage or UI.

---

## 1. The core idea

You get **one number**: the money you are free to spend, down to the last Euro,
with no guilt and no further thinking.

Everything else in the system exists only to make that number trustworthy.

The number is funded by **last month's leftover money**. This is what makes it
safe to spend to zero: this month's required expenses are paid from this month's
income, not from the free-to-spend money. The free-to-spend money is genuinely
surplus that has already survived a full month.

Two properties make the whole thing work:

- **Errors self-correct with one month of lag.** Underestimate groceries by €150
  and this month's income absorbs it; next month's free-to-spend is €150 smaller.
  Closed loop, no manual correction.
- **Savings and irregular costs are deducted first**, so the residual really is
  free. "Save whatever is left over" is inverted into "spend whatever is left over".

---

## 2. The model

### 2.1 Pots

All money is in exactly one of these pots at any time:

| Pot | Fed by | Drained by |
|---|---|---|
| **Operating (current month)** | this month's income | this month's required expenses, this month's pocket contributions |
| **Free-to-spend** | the operating surplus of the previous month | discretionary spending |
| **Pockets** | monthly contributions from operating | the specific expenses they exist for |
| **Safety net** | manual/configured contributions | only a free-to-spend balance that has gone below zero |

The safety net is a pocket. It differs only in *when* it may be drained.

### 2.2 The invariant

> **real money in all tracked accounts = operating + free-to-spend + all pockets**

Every rule in the system must preserve this. This is what makes it safe to be
sloppy elsewhere: any inaccuracy can only *move money between pots*, never
create or destroy it. A negative month must be booked somewhere real, never
silently clamped to zero.

### 2.3 Free-to-spend is a balance, not a monthly allowance

It is a running pot that receives a deposit at each month boundary and **never
resets**. This single decision covers, with no extra rules:

- carry-over of unspent money (the balance just stays)
- windfalls (bigger surplus → bigger deposit)
- negative months (a negative deposit)
- month-to-month volatility (self-smoothing)
- saving up for seasonal lumps like Christmas (underspend twice, the money is there)

If the balance drifts upward over time, that is a signal — the user should move
some of it into savings by hand. The system does not do this automatically.

### 2.4 Month rollover

At the month boundary:

1. `operating surplus = income − required expenses − pocket contributions`
2. `free-to-spend += operating surplus` (may be negative)
3. operating resets to zero and begins collecting the new month's income

That is the entire monthly logic.

### 2.5 Classification is mandatory

Every transaction is assigned to exactly one of:

- **required** → reduces this month's operating pot
- **free** → reduces the free-to-spend balance
- **pocket X** → reduces that pocket
- **transfer** → moves money between tracked accounts, affects no pot

This split is *not* optional. Required spending and discretionary spending hit
different pots; without the split, the number is meaningless.

**But misclassification is self-healing.** Mark a fun purchase as required and
this month's free-to-spend reads too high while next month's reads too low by
the same amount. The total is unaffected. Errors cost a wrong signal for a few
weeks, never real money.

The practical consequence: transaction review is the recurring cost of running
this system, and merchant-based auto-classification rules are load-bearing, not
a nice-to-have. If review takes more than a few minutes a week, the system will
be abandoned.

---

## 3. What deserves a pocket

**The test:** a pocket is for things where *not having the money at a specific
moment is a real problem*.

- Amount is essentially non-negotiable, **and**
- paying it out of one month would wipe out that month

Both true → pocket. Otherwise → free-to-spend.

Worked examples:

| | Pocket? | Why |
|---|---|---|
| Yearly insurance premium | yes | fixed amount, fixed date, large |
| Savings / investing | yes | must be deducted before the residual, or it never happens |
| Safety net | yes | see below |
| Clothes | **no** | if the budget is tight, buy cheaper or wait — that's fine |
| Christmas / birthday presents | **no** | same; amount is negotiable |
| Holiday / travel | user's choice | only if they'd rather not have it compete with daily spending |
| Phone / laptop replacement | user's choice | leaning no; free-to-spend can absorb it over a couple of months |
| Loan repayment | no | it's a standing required expense |

The default is **no pocket**. Pockets are the complexity in this system; each one
is a recurring decision the user has to maintain.

---

## 4. Rules and edge cases

### 4.1 Accounting month vs. value date

Every transaction carries two dates:

- **value date** — when the money actually moved
- **accounting month** — which month it counts toward

They are normally the same. The known exception: **salary often arrives at the
end of the preceding month** but belongs to the month it pays for. Without this
separation, that salary would inflate the previous month's surplus and thus
free-to-spend, double-counting it.

Keeping this as an explicit field costs nothing and is what makes payment float
(§5) a later rule change rather than a rewrite.

### 4.2 Negative months

The operating surplus can be negative (a tax bill, a car repair, an annual
reconciliation). Then:

1. free-to-spend absorbs it first — the balance simply drops, possibly to a
   small number. This is the normal case and needs no intervention.
2. Only if the free-to-spend **balance itself would go below zero** does the
   safety net come into play.

A negative free-to-spend balance is displayed honestly ("you owe your future
self") with a prominent warning. Whether to book a transfer from the safety net
to clear it is the user's decision, not automatic.

### 4.3 Safety net

- No automatic refill. Either a configured monthly contribution, or the user
  moves money in by hand.
- The app shows how full it is against its target and warns when it is short.
- It exists for **required expenses of unknown amount and timing**: tax
  settlements (Steuernachzahlung), utility reconciliation (Nebenkostenabrechnung),
  car repairs, medical bills, replacement of things that broke.

### 4.4 Windfalls

Bonuses, travel reimbursements from the employer, extra work, 13th salary. No
special handling: they are income into operating, which increases the surplus,
which increases next month's free-to-spend deposit. If the user wants to save
it instead, they move it to a pocket by hand.

### 4.5 Pocket underfunding

If the operating pot cannot cover all pocket contributions, **fund the pockets
in full anyway** and let free-to-spend go negative, with a loud warning. No
priority ordering, no partial fills. The user gets the same information with far
less machinery.

### 4.6 Tracked vs. external accounts

- **Tracked accounts** are the accounts the invariant in §2.2 sums over.
- Pockets are purely virtual and are **not** tied to which account the cash
  physically sits in. A safety net pocket does not require a separate real
  account, and a separate real account does not require its own pocket.
- Anything **untracked** — a broker account, the shared flat account — is
  external. Money moving there is an expense; money coming back is income.

### 4.7 Shared flat account

The fixed monthly payment into the shared account (rent + food) is a plain
required expense. Occasional top-ups look like expenses, settlements look like
income, and the user's share of the balance sitting in there is invisible.

Accepted for now, but noted as an **asymmetric** error: systematic overpayment
into the shared account makes the user feel permanently poorer than they are,
with no visible cause. Worth watching over the first months.

### 4.8 Ledger vs. projection

Two different things, and they should not be confused:

- The **ledger** is backward-looking and exact. It is where the invariant holds.
- The **projection** ("what will next month's free-to-spend be?") is
  forward-looking and approximate. It only becomes accurate late in the month.

The projection is a display concern and must never write to the ledger.

### 4.9 Volatility

Displayed raw. No smoothing, no capping. The user is assumed capable of
smoothing it themselves, and §2.3 already smooths it structurally.

---

## 5. Deliberately deferred

Considered, understood, consciously left out of the first version. Recorded so
we do not rediscover them as bugs.

| Thing | Why deferred | Later cost |
|---|---|---|
| **Transitory money** — group dinners, fronted work expenses, deposits, money you'll get back | It nets out within one or two months and the margins are loose enough to absorb it | Low. A "reimbursable" flag on a transaction. |
| **Payment float** — a purchase in month M that settles in M+1 | Everything is debit; float is near zero | Low, *provided* §4.1 (accounting month) is built from the start |
| **Debt as a first-class concept** | Modelled as a required expense or a pocket | Medium. Would need balance tracking. |
| **Pocket priority when underfunded** | §4.5 gives the same information without it | Low |
| **Automatic safety-net refill** | A warning conveys the same urgency | Low |
| **Free-to-spend smoothing** | §2.3 does it structurally | Low |
| **Investment value / net worth** | Savings pockets track *contributions*, not market value | High — needs price data |
| **Multi-currency** | Germany only | High |
| **Multi-user / shared budgets** | Single user; the shared account is a black box (§4.7) | High |
| **Interest, inflation** | Irrelevant at this scale | — |
| **What-if forecasting beyond next month** | Not the point of the tool | Medium |

---

## 6. Requirements for this strategy to work

This strategy is not universal. It works for the author. Anyone else should
check these first — several of them are hard prerequisites, not preferences.

**Hard prerequisites**

1. **Income reliably exceeds required expenses**, with enough headroom that a
   full month's surplus is a meaningful amount of money. If the surplus is
   routinely near zero, there is no free-to-spend budget and the system has
   nothing to say.
2. **Roughly one month of expenses already in the bank.** The free-to-spend pot
   has to start funded. Without it the app starts at €0 and the user waits a
   full month before it does anything. This is a cash prerequisite, not a data
   prerequisite — importing history does not create the buffer.
3. **No high-interest revolving debt.** "Spend everything that's left" is the
   wrong advice while credit card debt is compounding.
4. **A safety net large enough for the worst realistic surprise.** Since
   unknown-amount required expenses (tax bill, utility reconciliation, car,
   dentist) are deliberately *not* given pockets, the safety net is the only
   thing standing behind them. Rule of thumb: the largest plausible single
   surprise, plus one month of required expenses.

**Strong assumptions**

5. **Stable, predictable income.** Occasional extra payments are fine — they are
   just windfalls (§4.4). Genuinely variable income (freelancing) breaks the
   "last month's leftover" premise and would need a smoothing pocket that pays
   the user a fixed salary.
6. **Mostly debit / instant payment.** Heavy credit card use makes float (§5)
   matter much sooner.
7. **Discretionary spending is genuinely discretionary** — it can be cut to
   near zero in a bad month without harm.
8. **Willingness to review and classify transactions**, a few minutes a week
   (§2.5).
9. **Self-control.** The system makes overspending *visible*; it does not
   prevent it. Free-to-spend being a carried balance means an overspend follows
   you into next month.

---

## 7. Open questions

- Does a negative free-to-spend balance stay negative and get eaten by the next
  deposit, or should it be settled from the safety net immediately? Leaning
  toward "stays negative, warn loudly, user decides". To be tested in practice.
- What is the primary display: "remaining this month" plus "projected for next
  month"? A daily burn-down? To be decided when we get to UI.
- Should the app nag when the free-to-spend balance drifts upward over several
  months (i.e. "you could be saving more")?
- How much of the classification can realistically be automated from German
  bank exports (merchant names, Verwendungszweck)?
