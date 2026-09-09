# Open items

Known defects and unfinished work in this pipeline, written down so they survive a
conversation ending. Everything here was reproduced against the published dataset on
2026-09-09 (7,411 companies, build `3c0126ed`); each item says how to reproduce it.

Nothing here is a scoring or screening rule, and none of it belongs in this repo as one.
The reader decides what to do with a flagged company; the pipeline's job is to flag it.

---

## 1. Share counts wrong at source — now flagged, not fixed  ✅ FLAGGED 9 Sep 2026

`checks.share_scale` was added (`build_sec_dataset.py`, `share_scale()`), and `checks.shares` now
reads off the values rather than off which tag resolved. Both are covered by
`tests/test_share_scale.py`. Nothing about the underlying figures changed — the pipeline cannot
invent a count a filer tagged wrongly — but a reader is no longer told the data is fine.

**28 of the S&P 500** carry `share_scale: suspect`: AMCR BKNG BRO CRWD CVNA DD DLR ECHO EG GEHC
GRMN HST IBKR KLAC MCD NFLX NOW ORLY PEG PSKY SW TER TPL VLTO VTRS WAT WRB WSM. Every one was
checked by hand and none is a false positive.

Two shapes, two reasons:
- **`scale`** — a diluted count more than 50× its own outstanding count or less than 1/50.
  McDonald's files `716.4` for 716 million shares; Waters files 98,204,000,000 against 98m.
- **`levels`** — the quarterly series steps between levels more than once. A split steps once and
  stays. Netflix alternates 437m and 4,392m *before* its split date; Booking runs two quarters
  near 33m then two near 800m on a stock that never split 25:1; KLA's fiscal-year rows are 10×
  its own interims; Interactive Brokers mixes its ~107m Class A count with its ~440m total.

**Two designs were tried and discarded, both recorded because the reasoning is not obvious:**
1. A `shares_diluted ÷ shares_outstanding` cross-check alone reads a clean **1.013** for KLA,
   where both fields are 10× out together. It also cannot see Booking, which has no outstanding
   count at all.
2. Grouping the series by `round(log10(value))` made Goldman — sitting at ~3.1e8, either side of
   10^8.5 — cross a rounding boundary on a 3% move. Adjacent ratios have no such boundary.

**What is still not caught:** a company with no `shares_outstanding` whose series changes level
exactly once, in the wrong direction, at the edge of the window. There is nothing in the numbers
to distinguish that from a split.

## 2. `checks.shares` described tag resolution, not data  ✅ FIXED 9 Sep 2026

`data_checks` set the flag from `tags_used` alone, so a company whose diluted tag resolved but
whose rows were all empty read `ok` — 76 companies dataset-wide, and BKR, ERIE, HSY and LYB in
the S&P 500, every one promising a per-share figure it could not supply. It now reads the values.
The vocabulary is unchanged; seven S&P 500 flags corrected (ARES, BKR, BRK-B, ERIE, HSY, LYB, V).

**The unit test asserted the bug.** `test_the_shares_flag_says_which_per_share_tests_a_reader_can_run`
called `data_checks([], [], tags_used=...)` — no rows at all — and expected `"ok"`. Code and test
agreed with each other and neither ever looked at data, which is how this survived a suite that
was written specifically to catch share-count defects. It now passes rows, including the empty
case that was the bug.

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

## 5. `share_scale` never reached the manifest

`data_checks` computes `share_scale` and every company file carries it, but the manifest row
written in `build_sec_dataset.py` copies only `reconciles` and `shares`. The manifest is what a
reader opens first — it is the 1.8 MB index every task uses to go from ticker to CIK — so the
flag is currently invisible to anyone who does not open all 7,411 company files. Adding the key
is additive and safe under the ground rules below. Not done yet because it belongs to the same
run as the next full dataset build, not to the filing-text change.

## 6. The filing-text parser has not met a real 10-K

`build_sec_filings.py` and its twenty tests were written on 9 Sep 2026 against synthetic
filings. That is not a shortcut: the SEC refuses requests without the declared contact, so the
parser cannot be exercised anywhere but the workflow. Until a dispatched run reports its
coverage, the honest statement is that the rules are pinned, not proven. The first thing to read
is `data/filings_report.md` — specifically how many of the filings fetched carry `item1`, and
which names are in the "left without text" list. Companies whose MD&A is incorporated by
reference will legitimately be missing `item7`; a company missing `item1` is the parser.

## 7. Smaller things

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
