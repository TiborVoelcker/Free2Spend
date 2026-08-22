# Free2Spend — Conceptual Implementation

Status: draft, evolving. How the strategy in `strategy.md` is realised, at a
conceptual level. Deliberately says nothing about language, framework, storage
engine or UI toolkit. The staged build plan is a separate document, written once
this is settled.

Vocabulary is defined in `strategy.md` §7.

---

## 1. Guiding principle: derive everything

Because `free-to-spend = balance − pockets` is a *definition* rather than an
accumulator, the app needs almost no stored state.

**Stored (the source of truth):**

- accounts (tracked / hidden)
- the transaction log, with each transaction's class
- pocket configuration
- materialized contributions and manual moves (§5.3)
- balance anchors from imports (§3.3)

**Derived on demand, never stored:**

- the balance at any point in time
- every pocket's balance
- free-to-spend and remaining, for any period, past or present

The payoff is that nothing can go stale or out of sync. A transaction that
arrives late, or a misclassification corrected three months later, simply changes
the derived numbers — there is no repair logic, no migration, no reconciliation
of accumulated totals. It also means the whole history can be recomputed from
scratch at any time, which makes the system very easy to test.

The one consequence to accept: **past periods are not immutable.** Correcting an
old transaction changes what free-to-spend *was*. That is correct behaviour, but
the UI should not present historic numbers as carved in stone.

---

## 2. What has to exist

Roughly in dependency order, not build order:

1. accounts and a transaction log
2. import (§3)
3. periods and the cutover day (§4)
4. classification (§6)
5. pockets (§5)
6. the numbers and their display (§7)

---

## 3. Getting data in

### 3.1 Channels, and the staleness problem

Two options were on the table: online banking access, or importing PDF
statements.

There is a hard constraint that decides this: **the product is a live number.**
If the data is a month old, "remaining" is a month old, and the app is useless
for the decision it exists to support — *can I buy this right now?* A monthly PDF
statement cannot deliver that.

So the channel needs to support **frequent, low-friction refresh**. In rough
order of preference:

1. **Direct bank access** (FinTS/HBCI or a PSD2 API) — refresh on demand, real
   transaction identifiers, real reported balances. Harder to build, and per-bank.
2. **CSV export from online banking** — a manual download, but takes seconds and
   can be done weekly. Generalises far better than PDF across banks.
3. **PDF statements** — easy to obtain, but monthly and hard to parse reliably.
   Useful mainly for the initial history backfill.

A reasonable split: **PDF or CSV for the one-off history backfill, and the best
available live channel for ongoing refresh.** The importer should be written
against a neutral internal shape so channels are interchangeable.

### 3.2 Import identity and deduplication

The user will re-import overlapping ranges. Getting this wrong either duplicates
transactions (free-to-spend collapses) or drops them (free-to-spend inflates).

The trap: **genuine duplicates exist.** Two €3.50 coffees at the same shop on the
same day are two transactions, not one, so per-row deduplication by content is
wrong.

Two mechanisms, in order:

- **If the channel provides a stable transaction id**, use it. Bank APIs do.
- **Otherwise, import by range replacement**: an import covers a known date
  range, and importing it *replaces* every transaction in that range rather than
  merging row by row. Duplicates within the range are preserved correctly, and
  re-importing is idempotent.

Range replacement has to preserve the classifications the user already made for
transactions in that range. Match on content to carry the class over, and leave
anything ambiguous back in the review queue — a lost classification is harmless
(§6), so this can be crude.

### 3.3 Balance anchors and reconciliation

Every import brings a **balance anchor**: "on this date, the account held X".
Historic balances are then derived by walking the transaction log back from an
anchor.

The check that matters: **two anchors must agree with the transactions between
them.** If they don't, transactions are missing, and since free-to-spend is
`balance − pockets`, missing transactions corrupt the number directly.

This reconciliation check is the app's only real defence against silent data
loss, so it should be a visible status, not a hidden assertion. It is also cheap:
one subtraction per import.

---

## 4. Periods

### 4.1 The cutover day

A single configuration value: the day of month at which one period ends and the
next begins. A period is labelled by the calendar month it mostly covers.

This replaces the alternative of detecting recurring transactions and shifting
their dates individually. See `strategy.md` §4.1 for why — briefly: only
*recurring* transactions on the wrong side of a boundary cause a permanent
offset, and both the culprits (salary in, rent out) cluster in the same few days
at the end of the month, so one boundary shift catches them together.

The cutover day should be picked by looking at the actual transaction history for
a reliable gap. It needs a margin: if the salary sometimes lands a day early, the
cutover has to sit safely before the earliest it has ever arrived.

### 4.2 No scheduled work

Rollover is not an event that needs to fire on time. "Which period is today in"
is a pure function of the date and the cutover day, and every number is derived.
The only thing that needs to *happen* at a rollover is materializing pocket
contributions (§5.3), and that can be done lazily on next app load: "materialize
contributions for any period that has begun since we last looked."

So: no cron, no background jobs, no risk of a missed rollover corrupting anything.

---

## 5. Pockets

### 5.1 Configuration

A pocket has: a name, an optional **target**, an optional **due date**, and a
**contribution** per period. Three useful combinations:

| Setup | Contribution | Example |
|---|---|---|
| target + due date | computed: `(target − current) / periods remaining` | yearly insurance |
| target, no due date | user-set; stops on reaching the target | the buffer |
| neither | user-set, or manual moves only | an open-ended pot |

### 5.2 Pockets need a recurrence, not just a due date

A gap in the original sketch. Insurance is not due once — it is due *every year*.
With only a one-off due date, every recurring pocket has to be reconfigured by
hand after each payment, which is exactly the recurring maintenance the strategy
tries to avoid.

So a pocket's due date should carry an optional **recurrence** (yearly, quarterly,
…). When the pocket is depleted (§5.4), the due date rolls forward and the
contribution recomputes automatically. The pocket becomes fire-and-forget.

### 5.3 Contributions are materialized, not computed on the fly

The one place stored state is genuinely required.

If contributions were derived from the pocket's current configuration, then
raising a pocket's monthly contribution today would silently rewrite every past
period as though it had always been that amount. History would change under the
user.

So at each rollover, contributions are **written down as records**. Configuration
changes then affect the future only, and past periods stay true to what was
actually decided at the time.

Manual moves (§5.5) are stored the same way, for the same reason.

### 5.4 Depletion: detection plus a prompt

When the insurance is actually paid, the transaction must be classified as a
**pocket payment** against that pocket. This is ledger-critical: a missed one
leaves the pocket permanently too full and free-to-spend permanently too low
(`strategy.md` §2.4).

Two mechanisms, because pattern matching alone is not reliable enough for
something with a permanent consequence:

- **Matching rules** on the pocket — counterparty and/or reference text, with an
  amount range. A matching transaction is proposed as that pocket's payment.
- **A due-date prompt.** A pocket whose due date has passed while it is still
  full is almost certainly a missed payment. Asking is a far stronger safety net
  than any matching heuristic, and it costs nothing to implement.

### 5.5 Manual moves

The user must be able to move money virtually, in both directions:

- pocket → free-to-spend (the holiday is being paid for; the buffer is covering a
  negative free-to-spend)
- free-to-spend → pocket (put something aside this period)
- pocket → pocket

These are stored records, dated into a period.

### 5.6 Initial balances

On setup, a pocket can be seeded with a starting balance — the user has probably
been mentally setting money aside already. Small, but easy to forget, and without
it the first few periods read wrong.

---

## 6. Classification

### 6.1 Manual first

Everything defaults to **required**; the user marks the exceptions. This is right,
and cheaper than it looks, because required/fun is display-only and self-erasing
(`strategy.md` §2.4). Getting it wrong costs a slightly wrong number for a few
weeks and nothing else.

Automatic rules (by counterparty, by amount) can come later. They are a
convenience, not a correctness feature.

### 6.2 The review queue

The main recurring interaction. Newly imported transactions arrive unclassified
and need a pass. The queue's important job is **not** the fun/required split — it
is catching pocket payments and transfers, which are the two classes with
permanent consequences.

Design the queue around that: make pocket payments prominent and fun a one-tap
afterthought, not the other way round.

### 6.3 Transfers between tracked accounts

If the user holds two tracked accounts, money moving between them must be classed
as **transfer** or it reads as an expense on one side and income on the other,
distorting nothing in the balance but confusing everything else.

Auto-detectable: equal and opposite amounts, within a day or two, between two
tracked accounts. Propose it, let the user confirm.

Money moving to a **hidden** account is not a transfer — it is a required
expense, by definition (`strategy.md` §4.4).

---

## 7. Computing the numbers

For the current period:

```
free-to-spend = balance(at last cutover) − pockets(at last cutover, after contributions)
remaining     = free-to-spend − sum(fun transactions in this period)
```

For the projection of the next period, which is a display concern only and must
never write to the ledger:

```
projected = balance(now)
          − pockets(now)
          + expected recurring income before the next cutover
          − expected recurring required expenses before the next cutover
          − next period's contributions
```

Note that recurring-transaction detection has not disappeared — it moved. It is
no longer needed for period assignment (§4.1 handles that), but it *is* needed
here. This makes the projection a later stage than the core numbers, which is
fine: it is the less important of the two.

---

## 8. The ritual

What the user actually does, which should drive UI priorities:

- **Daily / whenever spending:** glance at *remaining*. Read-only. This is the
  product; it has to be one tap away and always current.
- **Weekly:** refresh the import, clear the review queue. A few minutes. If this
  is tedious, the system dies.
- **At a rollover:** look at the new free-to-spend. Notice if it is negative, and
  decide whether to cover it from the buffer.
- **Rarely:** add or adjust a pocket, make a manual move.

---

## 9. Open decisions

- **Live channel:** direct bank access or manual CSV export? This is the single
  biggest scope decision, and §3.1 argues it decides whether the product works at
  all. A pragmatic answer may be to start with CSV and treat direct access as an
  upgrade behind the same internal shape.
- **Between imports the number is stale.** Accept it, or allow a quick manual
  entry of a fun expense that later reconciles against the import? Accepting it
  is simpler, but weekly imports mean the number can be days out of date at
  exactly the moment it is consulted.
- **Multiple tracked accounts in the first version, or one?** One is meaningfully
  simpler (no transfer class needed at all).
- **How is a period labelled in the UI** when it runs the 27th to the 26th —
  "September", or the actual date range?
