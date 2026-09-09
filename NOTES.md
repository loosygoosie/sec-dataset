# Open items

Known defects and unfinished work in this pipeline, written down so they survive a
conversation ending. Everything here was reproduced against the published dataset on
2026-09-09 (7,411 companies, build `3c0126ed`); each item says how to reproduce it.

Nothing here is a scoring or screening rule, and none of it belongs in this repo as one.
The reader decides what to do with a flagged company; the pipeline's job is to flag it.

---

## 1. Share counts that are wrong at source, and are not flagged

The 9 Sep fix (`8562584d`) stopped the pipeline from *creating* bad share counts by
differencing a weighted average out of a year-to-date figure. It did not address counts
that arrive wrong from the filer. `checks.shares` catches only non-positive values
(`invalid:<items>`); a count that is off by a factor of ten or a million reads `ok`.

Two distinct shapes, which need different tests:

**Unit-scale errors** — the filer tagged a figure in millions against a `shares` unit,
so the value is 1,000× or 1,000,000× too small, or too large.

| Ticker | CIK | What is on file |
|---|---|---|
| WAT | 1000697 | Quarters ending 2026-04-04 and 2026-07-04 carry `shares_diluted` of 82,139,000,000 and 98,204,000,000 against `shares_outstanding` of ~98.2m — 1,000× too large. Earlier periods are correct at ~59.7m. (Outstanding genuinely rose 59.5m → 98.2m; that part is the BD Biosciences combination, not an error.) |
| SR | 1126956 | Annual `shares_diluted` of 52.6, 56.3, 58.7 — the figure in millions. Quarters from 2025-12-31 onward are correct at ~59.2m. |
| VHI | 59255 | Annual and quarterly `shares_diluted` of 28.5 through 2025-12-31; correct at 28,500,000 from 2026-03-31. |
| SW, PSKY, VLTO, GEHC, VTRS, PEG | | Same shape, ratios from 678,000× to 5,165,000×. |

**A whole fiscal year 10× out while its own interim quarters are right** — KLA (CIK 319201):

```
A 2024-06-30  dil=1,361,869,000   out=  134,425,000
A 2025-06-30  dil=1,337,502,000   out=1,320,227,000
A 2026-06-30  dil=1,319,633,000   out=1,306,983,000
Q 2026-03-31  dil=  131,750,000            <- correct
Q 2026-06-30  dil=1,319,633,000            <- the Q4 row takes the annual as filed
```

The real count is ~132m. Note the Q4 row inherits the annual error by design: a weighted
average is not additive, so the fiscal-year quarter takes the figure as filed. That is
correct behaviour on a correct input.

### Why the obvious check does not work, and what does

A `shares_diluted ÷ shares_outstanding` cross-check catches WAT (1,001×) but reads a clean
**1.013** for KLA's FY2025 — because *both* fields are 10× out together. It also fires on
30 S&P 500 rows, most of them not errors at all:

```
python3 - <<'PY'
import json, pathlib
sp = json.load(open('data/sp500.json'))
for c in sp['companies']:
    p = pathlib.Path(f"data/companies/{c['cik']}.json")
    if not p.exists(): continue
    d = json.load(open(p))
    for r in d['annual'] + d['quarterly']:
        a, b = r.get('shares_diluted'), r.get('shares_outstanding')
        if a and b and b > 0 and (a/b > 5 or a/b < 0.2):
            print(f"{c['ticker']}:{r['period_end']}:{a/b:,.0f}x"); break
PY
```

The 30 fall into two populations that must not be treated alike. Ratios landing on a known
split factor — AMZN 20×, NVDA 10×, ORLY 15×, DECK 6×, TSCO 5× — are a split-adjustment
mismatch between two fields that come from different places: `shares_diluted` is the
weighted average as filed for that period, `shares_outstanding` is `dei:EntityCommonStockSharesOutstanding`
from a filing's cover page. Ratios of 1,000× and up are genuine unit-scale errors.

**An adjacent-quarter jump test is the better instrument.** Nine S&P 500 names, and it
catches both WAT and KLAC, which no single ratio test does:

```
AMCR 2024-06-30->2024-09-30  5.01x      ECHO 2023-09-30->2023-12-31    998.51x
BKNG 2024-12-31->2025-03-31 24.28x      KLAC 2024-03-31->2024-06-30     10.02x
CVNA 2024-12-31->2025-06-30  5.42x      NFLX 2023-09-30->2023-12-31      9.99x
ORLY 2023-09-30->2023-12-31 15.10x      TSCO 2023-09-30->2023-12-30      5.02x
WAT  2024-12-31->2025-03-29  1,001.11x
```

Splits and errors separate on **whether the jump persists**: after a real split the series
stays at the new level and `shares_outstanding` moves with it (BKNG, NFLX, ORLY, TSCO,
AMCR, CVNA); KLA's jumps to 1.3bn and reverts to 132m the next quarter. That two-part rule
— jump, then reversion or corroboration by `shares_outstanding` — is the design worth
implementing. It is not implemented.

Whatever is added must be a **new** flag value or a new key, never a change to the meaning
of `shares`. Other tasks read these files by field name.

## 2. `checks.shares` describes tag resolution, not data

`data_checks` (`build_sec_dataset.py:517`) sets the flag from `tags_used` alone:

```python
st = (tags_used or {}).get("shares_diluted")
if st and "Diluted" in st:
    shares = "ok"
```

So a company where a diluted tag *resolved* but no value ever landed in a row reads `ok`.
ERIE (CIK 922621) is the clean example: `shares: ok`, and every `shares_diluted`,
`shares_basic` and `shares_outstanding` in the file is `null`. Four S&P 500 names —
**BKR, ERIE, HSY, LYB** — and 76 companies dataset-wide.

Not dangerous: a reader gets `None`, not a wrong number. But the flag reads as a promise it
does not make, and README.md's "Read the `checks` block before trusting a row" describes it
as though it did. Either the flag should require a value to be present, or the README
should say what it actually measures.

```
python3 -c "
import json,pathlib
n=[p for p in pathlib.Path('data/companies').glob('*.json')
   if (d:=json.load(open(p)))['checks'].get('shares')=='ok'
   and not any(r.get('shares_diluted') for r in d['annual']+d['quarterly'])]
print(len(n))"
```

## 3. Diluted share counts still missing

`shares_diluted` is `null` for every period in these S&P 500 holdings:

| Ticker | CIK | Flag | Why |
|---|---|---|---|
| V | 1403161 | `outstanding-only` | Multi-class filer: every share fact is tagged by class of stock, and companyfacts carries no dimensioned facts. |
| BRK-B | 1067983 | `basic-only` | Same. |
| ARES | 1176948 | `basic-only` | Only `WeightedAverageNumberOfSharesOutstandingBasic` resolves. |
| ERIE | 922621 | `ok` (see §2) | Diluted tag resolves, no values. |
| REG | 910606 | `ok` (see §2) | `shares_outstanding` is present; diluted is not. |

The per-filing XBRL fallback added in `f325f4ed` reads instance documents and already
excludes dimensioned contexts. Reading the *class-dimensioned* facts and summing across
classes would give Visa and Berkshire a real count — a deliberate exception to the
"no dimensioned facts" rule, so it needs its own tests. Nobody has attempted it.

## 4. TKO's share count is inconsistent between periods

TKO Group (CIK 1973266) `shares_diluted`:

```
A 2025-12-31  194,011,072
Q 2026-03-31  194,631,394
Q 2026-06-30   75,870,706     <- 2.56x lower
```

TKO has Class A shares plus Class B held by Endeavor. The 2026-06-30 row appears to carry
the Class A count where the others carry the total. Not yet confirmed against the 10-Q —
confirm before changing anything. `shares` reads `ok`; `reconciles` does not test share
counts, so nothing flags it.

## 5. Smaller things

- **`shares_outstanding` of 59,176 for WAT FY2023** (CIK 1000697) — five orders of magnitude
  below its neighbours, sitting under a `shares: ok` flag. Same class of defect as §1, on the
  other field.
- **`WRK` is absent from the manifest.** WestRock is now Smurfit Westrock (`SW`), which is
  present. Expected, recorded so nobody re-investigates it.
- **Dataset-wide counts** for the two candidate tests, if a future run wants a baseline:
  1,333 companies have a row with `shares_diluted/shares_outstanding` outside 0.2–5;
  1,076 have an adjacent-quarter jump beyond 5×/0.2×. Most are micro-caps and many are
  real splits or reverse splits — the S&P 500 subsets above are the useful signal.

---

## Ground rules for anyone picking this up

- `SEC_USER_AGENT` is a repo secret. Never hardcode it, never print it, never send it
  anywhere but sec.gov. Do not probe www.sec.gov from a sandbox with a placeholder contact;
  dispatch the workflow instead, so the real user-agent is used.
- Other tasks read these files by field name. Do not rename, remove or change the meaning
  of any existing key. Adding a field or a new flag value is fine.
- Both workflows refuse an empty script (`test -s`) and refuse to write if fewer than 3,000
  companies parse. Keep those guards.
- Never delete files in `data/` by hand; the build script owns that directory.
- No scoring or screening logic in this repo, and no Form 4 / insider feed unless asked.
- If a test finds a builder bug, stop and report it rather than working around it.
