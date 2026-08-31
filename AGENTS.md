# Notes for working on Free2Spend

Read `docs/strategy.md` first, then `docs/implementation.md`. This file is for
things that are true of the code but do not belong in either.

## Running it

```bash
python3 -m pytest                                          # no install needed
python3 -m scripts.import_report tests/fixtures/ing_sample.csv
python3 -m ruff check . && python3 -m ruff format .
```

There are no runtime dependencies. `pytest` and `ruff` are the only dev ones.

## Conventions that are not obvious from any one file

- **Money is `int` cents.** Never float, never `Decimal`. Rounding is then an
  explicit decision at the one place it happens.
- **Dates, never timestamps.** `datetime.date` throughout, Europe/Berlin implied.
  The one exception is an export's creation time, which is provenance rather
  than anything the arithmetic touches.
- **`today` is always a parameter.** Nothing in `engine/` reads a clock, which
  is what makes a whole simulated year reproducible.
- **`engine/` imports nothing but the standard library**, so it can be used from
  a bare script with nothing installed.
- Dependency direction is one way: `scripts` and `importers` know `engine`;
  `engine` knows nobody.

## ING CSV export, things that will bite

The format is read by `importers/ing_csv.py`. What is worth knowing:

- **Encoding is not consistent.** cp1252 in practice, sometimes UTF-8. Both are
  tried in turn.
- **The header row repeats `Währung`**, so columns are found by position.
- **The preamble has no fixed length**, so the table is found by scanning for a
  line starting `Buchung;`, not by skipping N lines. Only the export timestamp
  is read from it; the IBAN and bank name are known from the account already.
- **Row order is taken from the running balance**, not from the dates or the
  `Sortierung` header: it is the thing that has to add up, and a one-day export
  gives the dates nothing to go on.
- **Every row carries a running balance** (`Saldo`). This is how a misread
  amount is caught immediately, and how the window's opening balance is derived
  — no field states it outright.
- **Only booked entries are exported.** Pending ones (*vorgemerkte Umsätze*) are
  excluded by the bank, so nothing later changes or duplicates.
- **There is no purchase-date column.** For card payments it sits inside the
  purpose text (`... KAUFUMSATZ 24.08 12.99 ...`). That is payment float, which
  `strategy.md` §5 defers.
- **`Buchungstext` is free text**, not an enum. Observed: Gehalt/Rente,
  Echtzeitüberweisung, Lastschrift, Gutschrift, Gutschrift Echtzeitüberweisung,
  Barabhebung — and the set is not knowable in advance.

The fixture at `tests/fixtures/ing_sample.csv` is synthetic but in the real
format, with a correct running-balance chain. It is not reproducible from a
script; edit it by hand and recompute the chain, or regenerate it wholesale.

## Not built yet, by decision

- **Importer auto-detection.** `importers/importer.py` defines the `Importer`
  protocol; detection is added by extending it with `sniff` and a registry.
- **Range replacement on re-import.** The ING export declares its window in a
  `Zeitraum` header, which is what would drive it. The header is ignored for now
  since not every export has one.
- Anything in `docs/v2-ideas.md`.
