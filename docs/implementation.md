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
- virtual transactions, automatic and manual (§5.2)
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
3. periods and the rollover day (§4)
4. classification (§6)
5. pockets (§5)
6. the numbers and their display (§7)

---

## 3. Getting data in

### 3.1 The channel

**PSD2 bank access via Enable Banking** for ongoing import. Its consequences
shape the build:

- **A backend is mandatory.** PSD2 aggregators authenticate the *application*
  with a private key, which cannot live in a browser.
- **Consent expires.** Reconnecting is a recurring event, not a setup step, so
  the app holds last-known data, keeps working while disconnected, and shows a
  clear reconnect state.
- **Staleness between refreshes is accepted.** No compensating mechanism, such
  as entering an expense before it lands.
- **A CSV or PDF import path is the initial backfill only**, run once. PSD2
  returns a limited window of history, but free-to-spend needs only the balance
  at the last rollover and the current period's transactions, so a short window
  is enough to run on.

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

### 4.1 The rollover day

A single configuration value: the day of month at which one period ends and the
next begins, counted either from the start of the month (1..31, clamped in short
months) or from its end (-1 is the last day, -2 the day before it). A period is
shown as its actual date range, not a month name.

The relative form matters when income arrives on the last banking day rather than
a fixed date: a fixed day drifts against the month end as month lengths change,
a relative one does not.

It defaults to **-5**, which clears a month-end salary with a few days to spare.

**The setting has to explain itself.** A rollover day on the wrong side of the
salary overstates free-to-spend by a full salary every period, permanently, and
nothing else in the app is as easy to get quietly wrong. The report warns when a
period's income is more than 50% from the median, which is the symptom.

Suggesting a day from the history, and previewing its effect, are parked in
`v2-ideas.md`.

### 4.2 No scheduled work

Rollover is not an event that needs to fire on time. "Which period is today in"
is a pure function of the date and the rollover day, and every number is derived.
The only thing that needs to *happen* at a rollover is materializing pocket
contributions (§5.2), and that can be done lazily on next app load: "materialize
contributions for any period that has begun since we last looked."

So: no cron, no background jobs, no risk of a missed rollover corrupting anything.

---

## 5. Pockets

### 5.1 Configuration

A pocket has: a name, an optional **target**, an optional **due date** with an
optional **recurrence**, and a **contribution** per period. Three useful
combinations:

| Setup | Contribution | Example |
|---|---|---|
| target + due date | computed: `(target − current) / periods remaining` | yearly insurance |
| target, no due date | user-set; stops on reaching the target | the buffer |
| neither | user-set, or manual moves only | an open-ended pot |

**Recurrence** matters because insurance is due every year, not once. On depletion
(§5.3) the due date rolls forward and the contribution recomputes, so the pocket is
fire-and-forget instead of needing reconfiguration after every payment.

### 5.2 Virtual transactions

At each rollover the app **writes an automatic virtual transaction** into each
pocket. A pocket's balance is the sum of the virtual transactions and pocket
payments against it — it is never recomputed from the pocket's configuration.

This is the one place stored state is required: a configuration change must be
**forward-looking**, affecting future rollovers only, and a derived balance would
rewrite every past period as though the new amount had always applied.

Manual virtual transactions (section 5.4) are the same record, differing only in
who created them.

**Idempotency.** Automatic virtual transactions are generated lazily on app load
(section 4.2) rather than by a scheduled job, so they are keyed by pocket and
period: two loads in quick succession must not create the contribution twice.

### 5.3 Depletion: detection plus a prompt

When the insurance is actually paid, the transaction must be classified as a
**pocket payment** against that pocket. This is ledger-critical: a missed one
leaves the pocket permanently too full and free-to-spend permanently too low
(`strategy.md` §2.4).

Two mechanisms, because pattern matching alone is not reliable enough for
something with a permanent consequence:

- **Matching rules** on the pocket — counterparty and/or reference text, with an
  amount range. A matching transaction is *proposed* as that pocket's payment.

  The transaction's class remains the single source of truth. Pocket rules never
  write it directly; they pre-fill the review queue and the user confirms. That
  keeps exactly one code path for "which pocket did this deplete", and means
  classification by hand always works even when no rule exists.
- **A due-date prompt.** A pocket whose due date has passed while it is still
  full is almost certainly a missed payment. Asking is a far stronger safety net
  than any matching heuristic, and it costs nothing to implement.

### 5.4 Manual virtual transactions

The user must be able to move money virtually, in both directions:

- pocket → free-to-spend (the holiday is being paid for; the buffer is covering a
  negative free-to-spend)
- free-to-spend → pocket (put something aside this period)
- pocket → pocket

Same record type as the automatic ones, dated into a period.

### 5.5 Initial balances

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

Rules can come later, and when they do they are **explicitly configured**, not
inferred: *if the amount is X and the counterparty is Y, classify as Z.* No
learning, no guessing from history. A rule the user wrote is auditable and
predictable; a rule the app inferred is neither, and this is money.

### 6.2 The review queue

The main recurring interaction. Newly imported transactions arrive unclassified
and need a pass. The queue's important job is **not** the fun/required split — it
is catching pocket payments and transfers, which are the two classes with
permanent consequences.

Design the queue around that: make pocket payments prominent and fun a one-tap
afterthought, not the other way round.

### 6.3 Transfers between tracked accounts

**Not needed in the first version**, which tracks a single account. Recorded here
because it is the first thing a second account requires.

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
free-to-spend = balance(at last rollover) − pockets(at last rollover, after contributions)
remaining     = free-to-spend − sum(fun transactions in this period)
```

For the projection of the next period, which is a display concern only and must
never write to the ledger:

```
projected = balance(now)
          − pockets(now)
          + expected recurring income before the next rollover
          − expected recurring required expenses before the next rollover
          − next period's contributions
```

Note that recurring-transaction detection has not disappeared — it moved. It is
no longer needed for period assignment (§4.1 handles that), but it *is* needed
here. This makes the projection a later stage than the core numbers, which is
fine: it is the less important of the two.

---

## 8. Demo mode

The app runs end to end **with no bank connection at all**, against a committed
export in a real bank's format (`tests/fixtures/`), so the UI can be built and
judged against realistic numbers before any account is connected.

That fixture is unclassified, so it does not exercise the fun and required split
until classification is storable (M5), at which point classification is added on
top of it.

## 9. The ritual

What the user actually does, which should drive UI priorities:

- **Daily / whenever spending:** glance at *remaining*. Read-only. This is the
  product; it has to be one tap away and always current.
- **Weekly:** refresh the import, clear the review queue. A few minutes. If this
  is tedious, the system dies.
- **At a rollover:** look at the new free-to-spend. Notice if it is negative, and
  decide whether to cover it from the buffer.
- **Rarely:** add or adjust a pocket, make a manual move.
