# Free2Spend

A personal finance tool built on a single number: **the money you are free to
spend**, down to the last Euro, with no guilt and no further thinking.

That number is last period's leftover money — `balance − pockets` — recomputed
from the bank's own balance at every rollover rather than accumulated. This
period's required expenses are paid from this period's income, so what is left
over has already survived a full month and is genuinely free.

## Documentation

Read in this order:

| Document | What it covers |
|---|---|
| [`docs/strategy.md`](docs/strategy.md) | The financial strategy, its edge cases, what it requires to work, and the vocabulary used everywhere else |
| [`docs/implementation.md`](docs/implementation.md) | The conceptual design: import, periods, pockets, classification, the numbers |
| [`docs/stack.md`](docs/stack.md) | Technology decisions and the reasoning behind them |
| [`docs/build-plan.md`](docs/build-plan.md) | Staged milestones, M0 to M8 |
| [`docs/v2-ideas.md`](docs/v2-ideas.md) | Good ideas deliberately not in the first build |
| [`AGENTS.md`](AGENTS.md) | Conventions, and the export-format quirks that bite |

## Current state

Milestones **M0 to M2**. There is no application yet, by design: the strategy is
validated before the app is built (`docs/build-plan.md`). What exists is a pure
engine, an importer for ING CSV exports, and a script that prints a
period-by-period free-to-spend table from one.

## Reporting on an export

No dependencies, no database, no setup:

```bash
python3 -m scripts.import_report tests/fixtures/ing_sample.csv
python3 -m scripts.import_report statement.csv --rollover-day 27
python3 -m scripts.import_report statement.csv --help
```

The rollover day defaults to **-5**: five days before the month end, counting
back so it tracks the month end rather than drifting against it. The report
warns if any period's income is more than 50% away from the usual, which is the
symptom of a rollover day on the wrong side of the salary.

It verifies the export's running balance against every row, records the window's
opening and closing balances as anchors, and checks that the transactions between
them explain the change.

Nothing is classified at this stage, so every payment counts as required and
free-to-spend is just the accumulating balance. The column that means something
is **Surplus** — income less everything that left, which is what each period
would hand to the next once the budget is actually being spent down.

## Tests

```bash
python3 -m pip install pytest
python3 -m pytest
```

## Layout

```
engine/     pure functions. no I/O, no framework, no clock.
importers/  bank exports, normalised into the engine's shapes
scripts/    command line entry points. the only layer here that does I/O.
tests/
web/        the frontend
docs/
```

`store/` and `api/` arrive with the milestones that need them.

## Frontend

`web/` holds the original Nuxt 3.4 scaffolding, untouched and unused until M4.

It predates current Node releases, so installing it needs
`yarn install --ignore-engines` on Node 20+. Whether to upgrade Nuxt or rebuild
the frontend is a decision for M4, when `docs/stack.md` calls for Nuxt in SPA
mode behind a generated API client.
