# Free2Spend — Stack

Status: decided, revisable. The technology choices and the reasoning behind them.
The strategy lives in `strategy.md`, the conceptual design in `implementation.md`.

---

## 1. Decisions

| Concern | Choice |
|---|---|
| Backend language | **Python** |
| API framework | **FastAPI** |
| Engine | pure Python, stdlib + dataclasses, no dependencies |
| Storage | **SQLite**, one file, accessed through plain `sqlite3` |
| Frontend | **Nuxt in SPA mode** (or Vite + Vue — see §6) |
| Front↔back contract | OpenAPI schema → generated TypeScript client |
| Serving | FastAPI serves the built frontend as static files; one process |
| Deployment | one container on a home server |
| HTTPS / hostname | Tailscale (preferred) or Caddy with a public DNS name |
| Auth | single password, hashed, session cookie |
| Money | integer cents, everywhere, never floats |
| Dates | `datetime.date` only, Europe/Berlin, no timestamps |
| Tests | pytest, table-driven over the engine |
| Bank access | Enable Banking (PSD2) |

Deliberately **not** chosen: an ORM, a migration framework, a task queue, a cache,
a separate database server, user management, a native app. §10 says why.

---

## 2. Why a Python backend

The deciding factor is not technical merit — it is that this is a solo project
that has to stay interesting for years, and the author writes Python with more
pleasure than TypeScript. The engine is where the thinking happens; it should be
in the language that invites thinking.

The usual objections mostly do not apply here:

| Objection | Reality |
|---|---|
| "You lose Nuxt" | You lose Nuxt's *server routes*. Nuxt itself stays as the frontend. |
| "You lose SSR" | Irrelevant: a private single-user app, no SEO, and a PWA caches itself. |
| "Two deploys" | Not if FastAPI serves the built frontend (§7). One container, one process. |
| "Type sharing" | Improved. FastAPI emits OpenAPI; the TS client is generated from it, which beats hand-maintained shared types. |
| "Two dev processes" | True. A compose file or `Makefile`, set up once. |

What is genuinely gained: pytest for the engine's table-driven tests, and RSA-JWT
signing for Enable Banking being a two-line affair with `pyjwt` + `cryptography`.

---

## 3. Layers

Three layers with hard boundaries. This matters more than any individual
technology choice, because it is what lets the strategy be validated before a
bank is ever connected.

```
engine/        pure functions. no I/O, no framework, no clock.
store/         sqlite persistence. thin.
importers/     enablebanking/, csv/  → normalise into engine shapes
api/           fastapi. http, auth, serving the frontend.
web/           the SPA
tests/
```

Dependency direction is strictly downward: `api` knows `store` and `engine`,
`store` knows `engine`, and **`engine` knows nothing**.

The existing Nuxt app sits at the repository root and will be moved under `web/`.

---

## 4. Engine rules

Four constraints, each of which removes a class of bug outright:

1. **No I/O.** The engine takes data in and returns data out. It never reads a
   file, a database, or the network.
2. **No clock.** "Today" is a parameter. This is what makes it possible to run a
   whole simulated year through it in a test, and to reproduce any bug exactly.
3. **Integer cents.** Never floats, never `Decimal`. `amount_cents: int`.
   Rounding is then an explicit decision at the one place it occurs (splitting a
   pocket target across periods), not an emergent property of the arithmetic.
4. **Dates, not timestamps.** `datetime.date` throughout, Europe/Berlin implied.
   Bank data is date-granular anyway, and periods are defined by day of month.

Plain `dataclasses`, no pydantic — pydantic belongs at the API boundary, where
validating untrusted input is the job. Keeping it out of the engine keeps the
engine importable from a bare script with nothing installed.

The engine's signature is roughly:

```
(transactions, virtual_transactions, pockets, rollover_day, today)
    → balances, pocket balances, free-to-spend, remaining free-to-spend
```

---

## 5. Storage

SQLite, one file. Backup is `cp`. There is no scenario in this project where that
is not enough: a few thousand transactions a year, one user, no concurrency, and
every derived number recomputed from scratch in microseconds.

**No ORM.** An ORM's value — relationships, lazy loading, identity mapping — is
entirely unused here. The schema is a handful of flat tables and the dominant
query is "give me everything". Plain `sqlite3` behind a small repository module
is less code, fully transparent, and a better fit for a design where the database
is essentially an append-oriented log.

**No migration framework, at first.** During the build the schema will churn, and
"drop the database and re-seed" is a perfectly good migration strategy while the
only data is demo data or a re-runnable import. Alembic (and SQLAlchemy under it)
is the escape hatch once there is hand-entered data worth preserving — most
likely once classifications and pocket history exist.

Tables, roughly: `accounts`, `transactions`, `pockets`, `virtual_transactions`,
`balance_anchors`, `settings`.

---

## 6. Frontend

**Nuxt in SPA mode**, on the grounds of familiarity — the repo is already Nuxt 3
and there is no reason to relearn tooling for this.

Worth knowing: with SSR off, a lot of what Nuxt is *for* goes unused, and
Vite + Vue + vue-router would be a leaner base. That is a real alternative if the
Nuxt scaffolding starts feeling like weight. Either way the frontend is a thin
rendering layer over the API; switching it later is a contained job.

Mobile-first, and installable as a **PWA** — the primary use is glancing at
remaining free-to-spend on a phone, which has to be one tap away.

The API client is **generated from the OpenAPI schema**, not hand-written. It is
one command, and it means a backend change that breaks the frontend fails at
build time rather than in the browser.

---

## 7. Serving and deployment

**One container, one process.** The frontend is built to static files and served
by FastAPI. This removes CORS, removes a reverse proxy between the two, removes a
second deployment, and makes "run the whole app" a single command. It is the
detail that makes the Python/Nuxt split nearly free.

**The redirect URL constrains the hosting.** Enable Banking's authorisation flow
redirects the browser back to a registered URI, which will need to be stable and
almost certainly HTTPS. On a home server that means one of:

- **Tailscale** (preferred): a stable hostname with real HTTPS, reachable from
  the phone, with nothing exposed to the public internet. Best privacy posture
  for something holding a complete transaction history.
- **Caddy + a public DNS name**: automatic Let's Encrypt certificates, but the
  app is then reachable from the internet and the password is the only thing in
  front of it.

*To verify against Enable Banking's current documentation before building the
auth flow: whether non-public hostnames are accepted as redirect URIs, and
whether HTTPS is mandatory.*

---

## 8. Testing and demo data

**pytest, table-driven over the engine.** The characteristic test is a scenario:
a fixture transaction log plus a pocket configuration, asserting the
free-to-spend series across a simulated year. Because the engine has no clock and
no I/O, these run in milliseconds and are exactly reproducible.

**Demo data is a first-class module, not a test fixture.** A generator that
produces a plausible German year — salary landing at the end of the preceding
month, rent, weekly groceries, an annual insurance premium, a couple of
surprises — so that:

- the whole app is runnable end to end with **no bank connection at all**
- the strategy can be eyeballed over a full year before any real data exists
- edge cases (a negative period, a pocket depleting, a windfall) can be summoned
  on demand instead of waited for

The app should have a **demo mode** that runs against generated data. This is
what makes "get it running as fast as possible" achievable.

---

## 9. Auth

A single password, hashed, exchanged for a session cookie. No user accounts, no
registration, no password reset, no OAuth.

If the flatmate wants their own instance later, that is a **second container with
its own SQLite file** — zero code, zero schema change. Multi-tenancy is not a
feature this app will ever have.

Auth must exist before the bank is connected, since the redirect URL makes the
app browser-reachable.

---

## 10. Non-goals, and why

| Not doing | Why |
|---|---|
| ORM | Its features are unused here; raw SQL is less code and more transparent (§5) |
| Migration framework | Schema churn is cheap while the data is re-derivable; add Alembic when it isn't |
| PostgreSQL or any server database | One user, a few thousand rows, no concurrency |
| Caching, indexes, incremental recomputation | Full recomputation is already microseconds |
| Task queue / cron | Rollover is a pure function of the date; contributions materialise lazily on load |
| Multi-tenancy | A second container solves it |
| Native mobile app | A PWA reaches the phone at a fraction of the cost |
| Server-side rendering | No SEO, no cold-load concern |
