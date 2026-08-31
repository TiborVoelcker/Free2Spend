# Free2Spend — Build Plan

Status: proposed. Staged milestones, ordered so that problems surface as early
and as cheaply as possible.

Read `strategy.md` first, then `implementation.md` and `stack.md`.

---

## The ordering principle

Two rules decide the sequence:

1. **Validate the strategy before building the app.** The biggest risk in this
   project is not a bug, it is that the strategy turns out to feel wrong in
   practice. That can be tested with a script and a table of numbers, long before
   any database, API or interface exists.
2. **The bank comes last.** Enable Banking is the highest-friction, lowest-learning
   part of the build: consent flows, sandbox differences, a redirect URL that
   constrains hosting. Everything else can be built and judged without it, using
   generated data and a one-off CSV export of real history.

The consequence is that the first thing to exist is a script that prints twelve
months of free-to-spend, and the last is the bank connection.

### A property that makes early validation nearly free

`free-to-spend = balance − pockets`. With no pockets configured yet, that is just
**the account balance at each rollover** — which means the very first real-data
check needs *no classification, no pockets, and no bank API*. A CSV export of last
year plus a rollover day is enough to see what free-to-spend would have been every
month. That is milestone M2, and it answers the central question of the whole
project.

---

## M0 — Skeleton — *done*

**Goal:** a repository that runs its own tests.

**Build:** restructure into `engine/ store/ importers/ api/ web/ tests/`, move the
existing Nuxt app under `web/`, set up the Python project and pytest.

**Done when:** `pytest` runs green on one trivial test, and the Nuxt dev server
still starts.

**Not yet:** anything with behaviour.

*Outcome:* done. `store/`, `importers/` and `api/` were not created empty — they
arrive with their milestones. The Nuxt dev server does still start from `web/`,
but its 2023 dependencies need `yarn install --ignore-engines` on current Node.
Whether to upgrade Nuxt or rebuild the frontend is a decision for M4.

---

## M1 — Engine and a demo year — *done*

**Goal:** see twelve periods of free-to-spend, from generated data.

**Build:**
- the engine: periods from a rollover day, balances from a transaction log,
  free-to-spend and remaining free-to-spend. Pure, no clock, integer cents.
- the demo data generator: a plausible German year — salary landing at the end of
  the preceding month, rent, weekly groceries, an annual insurance premium, a
  windfall, one nasty surprise.
- a CLI script that prints a period-by-period table.
- pytest scenarios over the engine.

**Proves:** the core arithmetic, and the rollover-day mechanism against the exact
case it exists for (salary arriving before the month it pays for).

**Done when:** you can read a year of numbers and say whether they feel right.

**Not yet:** no database, no API, no UI, no pockets.

*Outcome:* done. `python3 -m scripts.demo_year` prints the table. The demo year
deliberately contains an annual insurance premium, a windfall, a car repair, and
a holiday saved up for across two lean periods; `--splurge` dials that holiday up
until a period is overspent, so the negative case can be summoned rather than
waited for. The salary-timing case has a regression test that states the bug the
rollover day prevents, by comparing against a calendar-month boundary.

---

## M2 — Your own history — *built*

**Goal:** the same table, on real numbers.

**Build:** the CSV backfill importer, and a report that prints where recurring
income landed so a rollover day can be chosen against it.

*No suggester.* The original plan had one; the review of PR #5 parked
"suggest a rollover day from the history" in `v2-ideas.md` as too much for the
first build. Printing the observed dates, absolute and relative to the month end,
gives the same decision at a fraction of the cost.

**Proves:** less than this plan first claimed, and the correction matters.

With nothing classified, every payment counts as required, so free-to-spend is
simply the accumulated balance — a real number, but not the free-to-spend you
would have had, because you would have been spending it down. What the milestone
really establishes is:

- **the surplus per period** — income less everything that left. That is what
  each period would hand to the next, and it is the honest preview of the budget
- **that income reliably exceeds required expenses** (requirement 1 in
  `strategy.md` section 6)
- **where the salary lands**, and therefore the rollover day

A realistic free-to-spend needs the discretionary split, which is M5.

**Done when:** you have run it over your own export, seen the surplus per period,
and chosen a rollover day from the data.

**Not yet:** still no classification, still no pockets — see the property above.

*Outcome:* built against a real ING export format. `python3 -m
scripts.import_report <csv>` reads the export, verifies its running balance
against every row, derives the window's opening balance, prints where recurring
income landed, and renders the table. What a real export contains is recorded in
`implementation.md` section 3.1.2.

---

## M3 — Pockets

**Goal:** the same table again, with your real pockets modelled.

**Build:** pockets in the engine — target, due date with recurrence, monthly
contribution, automatic and manual virtual transactions, pocket payments and the
depletion-and-recompute cycle.

**Proves:** that contributions and depletions behave sanely across a year, and
that free-to-spend stays a usable number once insurance and the buffer are taking
their cut.

**Done when:** the M2 table, re-run with your actual pockets, still makes sense —
including at least one period where a pocket depletes.

---

## M4 — The one number, on your phone

**Goal:** the app exists and is useful, in demo mode.

**Build:** SQLite store, FastAPI, the minimal SPA — one screen showing remaining
free-to-spend — served as static files by FastAPI. Containerised and running on
the home server, reachable on the LAN. PWA manifest so it installs.

**Proves:** the whole stack end to end, and whether the number is actually
reachable fast enough to consult at a till.

**Done when:** you can pull out your phone at home and see a number.

**Not yet:** no auth needed while it is LAN-only. No bank.

---

## M5 — Classification

**Goal:** the number responds to what you spend.

**Build:** transaction classes, the review queue, and the transaction list. Fun as
a one-tap action; pocket payments prominent, since they are the class with
permanent consequences.

**Done when:** marking a transaction as fun visibly moves remaining free-to-spend,
and assigning one to a pocket draws that pocket down.

---

## M6 — Pocket management

**Goal:** pockets are maintainable without editing code.

**Build:** create and edit pockets, the pocket test as a hint on the creation
screen, manual virtual transactions in both directions, the due-date prompt for a
pocket that is past due and still full, and matching rules that pre-fill the
review queue.

**Done when:** you can set up a year's worth of pockets from the UI and leave
them alone.

---

## M7 — Enable Banking

**Goal:** the data arrives by itself.

**Build:** the Enable Banking importer against the **sandbox first**, then the
real bank. Consent lifecycle and a clear "reconnect" state. Balance anchors and
the reconciliation check as a visible status. Import by range replacement,
preserving existing classifications.

Auth (single password, session cookie) and HTTPS on a stable hostname —
Tailscale preferred — both become necessary here, because the redirect URL makes
the app browser-reachable.

**Proves:** the last unknown — how quickly transactions actually appear over PSD2,
which determines how stale the number is between refreshes (`implementation.md`
§10).

**Done when:** a fresh purchase shows up without you doing anything, and the
reconciliation check agrees with the bank.

---

## M8 — Living with it

**Goal:** it survives daily use.

**Build:** whatever the first weeks of real use demand — the projection for next
period (which needs recurring-transaction detection), automatic classification
rules, backups, whatever turns out to be irritating.

This milestone is deliberately unplanned. The list of what matters here is not
knowable in advance, and guessing at it now would be the same mistake the strategy
document avoids by deferring things.

---

## Notes on sequencing

- **M1–M3 produce no application.** That is intentional. They are three scripts
  and a test suite, and they answer the questions that would be expensive to
  answer later.
- **M4 is the first thing you can show anyone.** If motivation flags, it is the
  milestone worth reaching quickly.
- **M2 can be revisited cheaply** whenever the engine changes, since it is a
  script over a CSV. It is the regression test for the strategy, not just for the
  code.
- **Deployment happens at M4, not at the end.** Running on the home server early
  keeps the deployment story small and continuous instead of becoming a project
  of its own.
