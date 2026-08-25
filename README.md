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

## Current state

Milestones **M0 and M1**. There is no application yet, by design: the strategy
is validated before the app is built (`docs/build-plan.md`). What exists is a
pure engine, a demo data generator, and a script that prints a year of
free-to-spend.

## Running the demo report

No dependencies, no database, no setup:

```bash
python3 -m scripts.demo_year
```

Useful variations:

```bash
# calendar months instead of a rollover day, showing the salary-timing problem
python3 -m scripts.demo_year --rollover-day 1

# a rollover day relative to the month end: -1 is the last day, -3 the third from last
python3 -m scripts.demo_year --rollover-day -3

# dial the holiday up past that period's free-to-spend to see an overspent period
python3 -m scripts.demo_year --splurge 480000

python3 -m scripts.demo_year --help
```

## Tests

```bash
python3 -m pip install pytest
python3 -m pytest
```

## Layout

```
engine/     pure functions. no I/O, no framework, no clock.
demo/       generated demo data, so the app can run with no bank connection
scripts/    command line entry points. the only layer here that does I/O.
tests/
web/        the frontend
docs/
```

`store/`, `importers/` and `api/` arrive with the milestones that need them.

## Frontend

`web/` holds the original Nuxt 3.4 scaffolding, untouched and unused until M4.

It predates current Node releases, so installing it needs
`yarn install --ignore-engines` on Node 20+. Whether to upgrade Nuxt or rebuild
the frontend is a decision for M4, when `docs/stack.md` calls for Nuxt in SPA
mode behind a generated API client.
