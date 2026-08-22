# Free2Spend — Strategy

Status: draft, evolving. This document describes the *financial strategy* the app
implements, and fixes the vocabulary used everywhere else. It says nothing about
technology, storage or UI — see `implementation.md` for that.

---

## 1. The core idea

You get **one number**: the money you are free to spend, down to the last Euro,
with no guilt and no further thinking.

Everything else in the system exists only to make that number trustworthy.

The number is funded by **last month's leftover money**. This is what makes it
safe to spend to zero: this month's required expenses are paid from this month's
income, not from the free-to-spend money. Free-to-spend is genuinely surplus
that has already survived a full month.

---

## 2. The model

### 2.1 The definition

At the start of each period:

> **free-to-spend = balance − pockets**

where *balance* is the real money in all tracked accounts at the moment the
previous period ended, and *pockets* is the sum of all virtual pockets.

That is the whole system. Free-to-spend is **derived from reality**, not
accumulated. It is recomputed from the bank's own number at every rollover.

During the period the number only ever goes down, and only by transactions
classified as **fun**. Everything else — income arriving, rent going out — just
moves the balance, and shows up at the next rollover.

### 2.2 Why this is the good part

Because free-to-spend is derived rather than tracked, a long list of things
need no rules at all:

- **Unspent money carries over.** Not by a carry-over rule — the money is simply
  still in the account, so next period's balance is higher. Nothing to implement.
- **The books cannot drift.** `balance = free-to-spend + pockets` is not an
  invariant to maintain, it is the definition. It re-derives from the bank every
  period. There is no accumulated state to get out of sync with reality.
- **Windfalls need no handling.** A bonus raises the balance, which raises next
  period's free-to-spend.
- **Volatility is self-smoothing.** Underspend twice and the money is there for
  Christmas, with no Christmas pocket.
- **Negative months need no absorb rule.** See §4.2.
- **Errors self-correct with one period of lag.** Underestimate groceries and
  this period's income absorbs it; next period's free-to-spend is smaller.

### 2.3 Rollover

At each rollover:

1. take the balance across all tracked accounts
2. apply this period's automatic virtual transactions into pockets (raising `pockets`)
3. `free-to-spend = balance − pockets`

That is the entire periodic logic. There are no snapshots to keep and no
running totals to maintain.

### 2.4 Classification, and what actually matters

Every real transaction gets a class:

| Class | Effect | If it is wrong |
|---|---|---|
| **required** (default) | none — it only moves the balance | self-erases at the next rollover |
| **fun** | reduces this period's free-to-spend | self-erases at the next rollover |
| **pocket payment** | reduces that pocket | **permanent** offset |
| **transfer** | between two tracked accounts; no effect | balance unaffected either way |

The required/fun split is a **display concern only**. It affects what the number
reads *during* the period and nothing else — `free-to-spend = balance − pockets`
does not contain the split, so a misclassification is completely erased at
rollover. This is why classification can stay manual and casual.

Pocket payments are different and must be right. If the €600 insurance debit is
not recorded as drawing down the insurance pocket, that pocket stays €600 too
full forever and free-to-spend is permanently €600 lower. Correctness effort
belongs here, not in the fun/required split.

---

## 3. What deserves a pocket

**The pocket test:** a pocket is for things where *not having the money at a
specific moment is a real problem*.

- The amount is essentially non-negotiable, **and**
- paying it out of a single period would wipe that period out

Both true → pocket. Otherwise → free-to-spend. *(This test should appear as a
hint in the app when creating a pocket.)*

| | Pocket? | Why |
|---|---|---|
| Yearly insurance premium | yes | fixed amount, fixed date, large |
| Buffer (safety net) | yes | see §4.3 |
| Clothes | **no** | budget tight → buy cheaper or wait. That's fine. |
| Christmas / birthday presents | **no** | same; the amount is negotiable |
| Holiday / travel | user's choice | only if they'd rather it not compete with daily spending |
| Phone / laptop replacement | user's choice | leaning no; free-to-spend absorbs it over a couple of periods |
| Loan repayment | no | a standing required expense |
| Savings / investing | no | a real transfer to a hidden account — see §4.4 |

The default is **no pocket**. Pockets are the complexity in this system; each
one is a recurring decision to maintain.

---

## 4. Rules and edge cases

### 4.1 Period boundaries

Salary for month M typically arrives at the *end* of M-1, and rent for M is
often debited then too. If the period were the calendar month, the balance
snapshot would include a salary that has not been earned against yet — and
because it happens *every* month, free-to-spend would be overstated by a full
salary permanently, not just once.

The rule that matters: **a one-off transaction near a boundary only fluctuates
and self-corrects; a recurring one that always lands on the wrong side causes a
permanent offset.**

The fix is to move the boundary, not the transactions: a period runs from the
**rollover day** to the rollover day (e.g. the 27th → the 26th) and is labelled by
the calendar month it mostly covers. One configuration value handles both the
salary and the end-of-month rent, with no per-transaction dates to maintain.

Per-transaction overrides are deferred (§5).

### 4.2 Negative free-to-spend

Needs no special rule. `free-to-spend < 0` simply means the pockets claim more
money than the account holds. It happens when the previous period overspent, or
when contributions were larger than the surplus.

The remedy is one manual move out of the buffer pocket — which *is* the safety
net doing its job. Nothing is automatic; the negative number is the warning.

### 4.3 The buffer (safety net)

A pocket like any other. It exists for **required expenses of unknown amount and
timing**: tax settlements, utility reconciliation (Nebenkostenabrechnung), car
repairs, medical bills, replacing things that broke. These are deliberately *not*
given their own pockets, so the buffer is the only thing standing behind them.

No automatic refill. Either a monthly contribution, or the user moves money in
by hand with a virtual transaction. The app shows how full it is against its target.

### 4.4 Tracked and hidden accounts

- **Tracked accounts** are summed to produce the balance.
- **Hidden accounts** are invisible to the app. Money sent there is simply spent
  (a required expense); money coming back is income.
- Pockets are purely virtual and are **not** tied to which account cash sits in.
  A buffer pocket needs no separate real account, and a real savings account
  needs no pocket.

This is how savings work: rather than a savings pocket, make a real standing
transfer to a hidden savings account. It leaves the balance, so it is deducted
before the residual, which is the whole point — and it needs no pocket machinery.

### 4.5 Pocket underfunding

If the balance cannot cover all pocket contributions, **fund them in full anyway**
and let free-to-spend go negative. No priority ordering, no partial fills. The
user can still go out with friends once, and knows to save this period.

### 4.6 Shared flat account

The fixed monthly payment into a shared account is a plain required expense. The
occasional extra transfer or settlement is treated as a rounding error and
absorbed. The user's share of the balance sitting there is invisible to the app.

### 4.7 Ledger and projection

- The **ledger** is backward-looking and exact.
- The **projection** ("what will next period's free-to-spend be?") is
  forward-looking and approximate; it only sharpens late in the period.

The projection is a display concern and must never write to the ledger.

### 4.8 Volatility

Displayed raw. No smoothing, no capping. §2.2 already smooths it structurally,
and the user is assumed capable of the rest.

---

## 5. Deliberately deferred

Considered, understood, consciously left out. Recorded so we do not rediscover
them as bugs.

| Thing | Why deferred | Later cost |
|---|---|---|
| **Transitory money** — group dinners, fronted work expenses, deposits | Nets out within a period or two; margins are loose enough | Low. A flag on a transaction. |
| **Payment float** — bought in one period, settles in the next | Everything is debit; float is near zero | Low, *provided* the period boundary (§4.1) exists from the start |
| **Per-transaction period overrides** | The rollover day handles the recurring cases, which are the ones that matter | Low |
| **Debt as a first-class concept** | A required expense, or a pocket | Medium — would need balance tracking |
| **Pocket priority when underfunded** | §4.5 gives the same information without it | Low |
| **Automatic buffer refill** | A negative number conveys the same urgency | Low |
| **Free-to-spend smoothing** | §2.2 does it structurally | Low |
| **Investment value / net worth** | Savings live in hidden accounts; the app never sees them | High — needs price data |
| **Multi-currency** | Germany only | High |
| **Multi-user / shared budgets** | Single user; the shared account is a black box (§4.6) | High |
| **Interest, inflation** | Irrelevant at this scale | — |
| **Forecasting beyond the next period** | Not the point of the tool | Medium |

---

## 6. Requirements for this strategy to work

Not universal. It works for the author. Anyone else should check these first —
several are hard prerequisites, not preferences.

**Hard prerequisites**

1. **Income reliably exceeds required expenses**, with enough headroom that a
   period's surplus is a meaningful amount of money. If the surplus is routinely
   near zero there is no free-to-spend budget and the app has nothing to say.
2. **Roughly one period of expenses already in the bank.** This is a *cash*
   prerequisite, not a data one — importing history does not create the buffer.
   This is not an accident of the design, it is the point: you only spend on fun
   when you are certain the money is there, and you are certain when it is last
   period's surplus.
3. **No high-interest revolving debt.** "Spend everything that's left" is the
   wrong advice while credit card debt compounds.
4. **A buffer large enough for the worst realistic surprise.** Since
   unknown-amount required expenses get no pockets, the buffer is all that stands
   behind them. Rule of thumb: the largest plausible single surprise, plus one
   period of required expenses.

**Strong assumptions**

5. **Stable, predictable income.** Occasional extra payments are fine — they are
   just windfalls. Genuinely variable income (freelancing) breaks the "last
   period's leftover" premise and would need a smoothing pocket paying a fixed
   salary.
6. **Mostly debit / instant payment.** Heavy credit card use makes float matter
   much sooner.
7. **Discretionary spending is genuinely discretionary** — cuttable to near zero
   in a bad period without harm.
8. **Willingness to review and classify transactions**, a few minutes a week.
9. **Self-control.** The system makes overspending *visible*; it does not prevent
   it, and an overspend follows you into the next period.

---

## 7. Vocabulary

The official names. Used in the docs, the UI, and the code.

### Money

| Term | Meaning |
|---|---|
| **Balance** | real money across all tracked accounts |
| **Tracked account** | an account whose money counts toward the balance |
| **Hidden account** | an account the app ignores; money sent there is spent |
| **Pocket** | a virtual sub-balance reserved for a purpose |
| **Buffer** | the pocket for unplanned required expenses (the safety net) |
| **Free-to-spend** | `balance − pockets`, fixed at the start of a period |
| **Remaining free-to-spend** | free-to-spend minus the fun spending so far this period. The number the user actually looks at. |

### Time

| Term | Meaning |
|---|---|
| **Period** | one budget month; runs rollover day to rollover day, labelled by the calendar month it mostly covers |
| **Rollover day** | the day of month on which one period ends and the next begins |
| **Rollover** | the event at a rollover day, when free-to-spend is recomputed and automatic virtual transactions are made |

### Movements

| Term | Meaning |
|---|---|
| **Transaction** | a real bank transaction, imported |
| **Class** | what a transaction is: required, fun, pocket payment, or transfer |
| **Required** | the default; does not touch free-to-spend |
| **Fun** | paid out of free-to-spend |
| **Pocket payment** | a real transaction that draws down a pocket |
| **Transfer** | movement between two tracked accounts; no effect on anything |
| **Virtual transaction** | a movement of money between pockets and free-to-spend that has no counterpart at the bank |
| — **automatic** | generated at rollover from a pocket's monthly contribution setting |
| — **manual** | made deliberately by the user |

### Pocket settings

| Term | Meaning |
|---|---|
| **Target** | how much the pocket should hold |
| **Due date** | when it needs to be full (optional), with an optional recurrence |
| **Monthly contribution** | the amount the pocket receives each rollover, as an automatic virtual transaction |

---

## 8. Open questions

- Which rollover day? To be picked from the actual transaction history, looking
  for a reliable gap between the last debits of one month and the salary.
- What is the primary display: *remaining* plus *projected next period*? A daily
  burn-down?
- Should the app say something when free-to-spend drifts upward over several
  periods (i.e. "you could be saving more")?
- How much classification can realistically be automated from German bank
  exports (merchant name, Verwendungszweck)?
