# Free2Spend — V2 Ideas

A parking lot. Ideas that are genuinely good but not worth building in the first
version, kept here so they are not rediscovered from scratch later.

This is different from `strategy.md` §5, which records things deliberately left
out of the *strategy*. These are things left out of the *first build*.

---

### Suggest a rollover day from the transaction history

Rather than asking the user cold, analyse the imported history for the widest
reliable gap before recurring income and propose a day.

*Why not V1:* needs recurring-transaction detection, which nothing else in V1
requires. M2 instead prints where recurring income actually landed — absolute
day and days from the month end — and leaves the choice to the user. That turned
out to be enough.

### Preview the effect of a rollover day before saving it

Show which recurring transactions land in which period under the currently chosen
day, so the consequence is visible rather than explained.

*Why not V1:* same dependency, and the same one-off nature.

### Inferred classification

Learning classifications from history, or guessing them from merchant names.

*Why not V1, or possibly ever:* V1 uses **explicitly configured** rules only — *if
the amount is X and the counterparty is Y, classify as Z.* A rule the user wrote
is auditable and predictable; an inferred one is neither, and this is money. This
would need a good reason to revisit.

### Manual entry of a fun expense before it lands

Between refreshes the number is slightly stale. A quick manual entry that later
reconciles against the imported transaction would close that gap.

*Why not V1:* the staleness is accepted (`implementation.md` §3.1), and this needs
a reconciliation mechanism that nothing else needs.
