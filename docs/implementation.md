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

### 3.1 Channels, and the staleness problem

There is a hard constraint that decides this: **the product is a live number.**
If the data is a month old, "remaining free-to-spend" is a month old, and the app
is useless for the decision it exists to support — *can I buy this right now?* A
monthly PDF statement cannot deliver that, so PDF is not the easy option, it is
the option that does not work.

**Decision: PSD2 bank access via Enable Banking** as the ongoing channel.

This has consequences worth stating up front, because they shape the whole build:

- **A backend is mandatory.** PSD2 aggregators authenticate the *application*
  with a private key. That key cannot live in a browser, so a purely client-side
  app is off the table regardless of any other preference. See `stack.md`.
- **Consent expires.** PSD2 requires periodic re-authentication. Reconnecting is
  a recurring event, not a one-off setup step, so the app must hold last-known
  data, keep working while disconnected, and surface a clear "reconnect" state
  rather than erroring.
- **Build against the sandbox first.** The strategy can be validated long before
  a real bank is ever connected.
- **Staleness between refreshes is accepted.** The number will occasionally be a
  little behind. No compensating mechanism (such as manually entering a fun
  expense before it lands) is built.
- **Bank coverage: verified.** The author's bank is supported by Enable Banking.
  What it actually exposes (history depth, balance types, update latency) is
  still to be measured.

### 3.1.1 History depth, and why it barely matters

PSD2 access typically returns a limited window of history (often around 90 days).
This sounds like a problem for bootstrapping and mostly is not, because
**free-to-spend needs almost no history to be correct**: the balance at the last
rollover, plus this period's transactions. One period is enough for the app to
function fully.

Longer history is wanted for two secondary things: picking the rollover day
(§4.1) and any retrospective analysis. Both are one-off or optional.

So a CSV or PDF import path is not dead — it is demoted to exactly one job:
**the initial backfill**, run once, from an online-banking export. It never needs
to be reliable enough for ongoing use, which removes most of the reason it was
hard.

### 3.1.2 What an ING export actually contains

Measured against a real export (M2), not assumed:

- **A running balance on every row.** Far better than the single balance anchor
  section 3.3 assumes. The whole chain can be verified, which catches a misread
  amount immediately, and the opening balance of the window is derivable exactly
  as `first row's balance - first row's amount`. No other field states it.
- **Only booked entries.** The preamble says pending entries (*vorgemerkte
  Umsätze*) are excluded, so there is nothing that later changes or duplicates.
- **The window is declared** (`Zeitraum;01.03.2026 - 31.08.2026`), which is
  exactly the input range replacement (section 3.2) needs.
- **Both dates, nearly always equal.** `Buchung` and `Wertstellungsdatum` differ
  only occasionally, on card settlements around weekends. Booking date drives
  every calculation; see `engine/model.py`.
- **No purchase date as a column.** For card payments it is inside the purpose
  text (`... KAUFUMSATZ 24.08 12.99 ...`), recoverable by pattern but not
  structured. This confirms payment float (docs/strategy.md section 5) stays
  deferred rather than being free to pick up.
- **`Buchungstext` is free text, not an enum.** Observed: Gehalt/Rente,
  Echtzeitüberweisung, Lastschrift, Gutschrift, Gutschrift Echtzeitüberweisung,
  Barabhebung — and the set is not knowable in advance, so it is stored as a
  string.
- **The header row repeats `Währung`**, so columns are located by position.

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

This replaces the alternative of detecting recurring transactions and shifting
their dates individually. See `strategy.md` §4.1 for why — briefly: only
*recurring* transactions on the wrong side of a boundary cause a permanent
offset, and both the culprits (salary in, rent out) cluster in the same few days
at the end of the month, so one boundary shift catches them together.

The rollover day should be picked by looking at the actual transaction history for
a reliable gap. It needs a margin either way: if the salary sometimes lands a day
early, the rollover day has to sit safely before the earliest it has ever
arrived.

**This setting has to explain itself.** It is the least intuitive option in the
app, and a rollover day on the wrong side of the salary overstates free-to-spend
by a full salary every period, permanently. The configuration screen should say
that in plain words. Suggesting a day from the history, and previewing its effect,
are parked in `v2-ideas.md`.

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

This is the one place stored state is genuinely required, because a configuration
change must be **forward-looking**. A pocket that has received €50 for 10 periods
holds €500; raising it to €80 must leave it at €500 and grow it by €80 from the
next rollover. Derived from configuration it would instead jump to `80 × 10` =
€800 — claiming money that was never set aside, and dropping free-to-spend by €300
on the spot.

Manual virtual transactions (§5.4) are the same record, differing only in who
created them.

**Idempotency.** Because automatic virtual transactions are generated lazily on
app load (§4.2) rather than by a scheduled job, they must be keyed by pocket and
period, so two loads in quick succession cannot create the contribution twice.

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

Everything above is designed so the app can run end to end **with no bank
connection at all**, against a committed export in a real bank's format
(`tests/fixtures/`).

This is not a testing convenience, it is what lets the UI be built and judged
against realistic numbers before any account is connected.

The fixture is unclassified, so the fun and required split is not exercised by
it until classification is storable (M5), at which point classification is added
on top of the fixture. See `stack.md` §8 for why a generator was removed in
favour of a file.

## 9. The ritual

What the user actually does, which should drive UI priorities:

- **Daily / whenever spending:** glance at *remaining*. Read-only. This is the
  product; it has to be one tap away and always current.
- **Weekly:** refresh the import, clear the review queue. A few minutes. If this
  is tedious, the system dies.
- **At a rollover:** look at the new free-to-spend. Notice if it is negative, and
  decide whether to cover it from the buffer.
- **Rarely:** add or adjust a pocket, make a manual move.
