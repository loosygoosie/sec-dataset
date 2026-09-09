# Open items

Known defects and unfinished work in this pipeline, written down so they survive a
conversation ending. Everything here was reproduced against the published dataset on
2026-09-09 (7,411 companies, build `42cded4e` — the first published build carrying `checks.share_scale`); each item says how to reproduce it.

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
| V | 1403161 | `none` | Multi-class filer: every share fact is tagged by class of stock, and companyfacts carries no dimensioned facts — so neither a diluted nor an outstanding count survives. |
| BRK-B | 1067983 | `none` | Same. |
| ARES | 1176948 | `outstanding-only` | An outstanding count resolves; no diluted figure does. |
| ERIE | 922621 | `none` | The diluted tag resolves but carries no values, which is exactly the case §2 stopped reporting as `ok`. |

REG (CIK 910606) was listed here and does not belong: its `shares_diluted` is populated and its
flag is `ok`. Removed 9 Sep 2026 — the row was describing a company that does not have the defect.

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

## 5. `share_scale` never reached the manifest  ✅ FIXED 9 Sep 2026

`data_checks` computes `share_scale` and every company file carries it, but the manifest row
written in `build_sec_dataset.py` copies only `reconciles` and `shares`. The manifest is what a
reader opens first — it is the 1.8 MB index every task uses to go from ticker to CIK — so the
flag is currently invisible to anyone who does not open all 7,411 company files. Adding the key
is additive and safe under the ground rules below. **Done:** the manifest row now carries
`share_scale`, and the patch pass moves its counter (and the `shares` counter) instead of leaving
both on the pre-patch value — REPORT.md had been counting the old flag for all 71 patched
companies. The published manifest carries it from the next dataset build.

## 6. The filing-text parser has now met 502 real 10-Ks  ✅ RESOLVED 9 Sep 2026

`build_sec_filings.py` and its twenty tests were written on 9 Sep 2026 against synthetic
filings. That is not a shortcut: the SEC refuses requests without the declared contact, so the
parser cannot be exercised anywhere but the workflow. Until a dispatched run reports its
coverage, the honest statement is that the rules are pinned, not proven. The first thing to read
is `data/filings_report.md` — specifically how many of the filings fetched carry `item1`, and
which names are in the "left without text" list. Companies whose MD&A is incorporated by
reference will legitimately be missing `item7`; a company missing `item1` is the parser.

## 7. The cross-reference filers have no narrative in the dataset

A dozen S&P 500 companies publish an integrated annual report and put a **cross-reference index**
in the 10-K instead of item headings — the twelve seen on 9 Sep 2026 were Citigroup, Cardinal Health, Church & Dwight, Cincinnati
Financial, Edison International, General Electric, Honeywell, Intel, McDonald's, Morgan Stanley,
Synchrony and Weyerhaeuser. (Interactive Brokers is NOT one of them — that was an error here.) GE's primary document is 461,146 characters of narrative with 22 index
rows at the end and not one item heading in the body. There is nothing for the extractor to
slice, and the first version of it stored three of those index rows as sections: "Item 3. Legal
Proceedings 70-71" is a page reference, not a disclosure. That is fixed — such a run is now
recognised as a table of the whole form and dropped — so these companies are reported by name and
left without text, which is the honest answer.

Closing the gap means following the index into the exhibit (usually EX-13, the annual report
itself) and slicing by the page ranges the index gives. That is a different parser and it was not
started here. Until it exists, the briefs task names these companies rather than writing them.

## 8. Smaller things

- **`shares_outstanding` of 59,176 for WAT FY2023** (CIK 1000697) — five orders of magnitude
  below its neighbours, sitting under a `shares: ok` flag. Same class of defect as §1, on the
  other field.
- **`WRK` is absent from the manifest.** WestRock is now Smurfit Westrock (`SW`), which is
  present. Expected, recorded so nobody re-investigates it.
- **Dataset-wide counts** for the two candidate tests, if a future run wants a baseline:
  1,333 companies have a row with `shares_diluted/shares_outstanding` outside 0.2–5;
  1,076 have an adjacent-quarter jump beyond 5×/0.2×. Most are micro-caps and many are
  real splits or reverse splits — the S&P 500 subsets above are the useful signal.

## 9. The annual share series steps at a split, and no flag sees it

Found 9 Sep 2026 while moving the monthly re-score's valuation tilt off FMP and onto this
dataset. The tilt needs a market cap at each of six fiscal year ends, and the only share count
available for a past year is `shares_diluted` on the annual row. That series is **not on one
basis**: companyfacts carries the latest reported value for each fiscal year, and a 10-K
restates only the two or three comparative years it prints, so a split reaches back a few rows
and stops. The series steps by the split factor part-way through.

Ten of the thirty-six book holdings step inside their own six-year window:

| | step | | | step |
|---|---|---|---|---|
| FTNT | 4.79x at FY2020 | | VICI | 1.52x at FY2022 (real dilution, not a split) |
| DECK | 5.76x at FY2023 | | CMG | 49.21x at FY2023 |
| NFLX | 9.96x at FY2023 | | DXCM | 4.55x at FY2020 |
| MNST | 2.00x at FY2021 | | NVDA | 3.96x at FY2020, 9.89x at FY2023 |
| CTAS | 3.92x at FY2023 | | TPL | 2.99x at FY2022, 2.98x at FY2023 |

**`share_scale` reads `ok` for eight of the ten, and that is correct** — `levels` counts steps in
the *quarterly* series and needs more than one, because a single step is exactly what an ordinary
split looks like and flagging it would make the check noise (`tests/test_share_scale.py::
test_one_step_is_a_split_and_is_left_alone` pins that deliberately). `scale` compares diluted
against outstanding on one row at `SCALE_RATIO = 50`, aimed at the million-fold tagging error, so
a 2x mismatch passes. Neither check is wrong; neither covers this.

**Monster is the sharp case.** Its whole series — annual *and* quarterly, through 2026-06-30 —
sits near 984m, while the broker reports 1,959,051,827 shares outstanding today. A 2:1 split is
absent from the dataset entirely, under `shares: ok` and `share_scale: ok`. Its FY2021 row is
also internally inconsistent: `shares_diluted` 1,071,278,000 against `shares_outstanding`
529,323,000, the 2021 split restated into one field and not the other.

**Why it matters.** A pre-split share count multiplied by a split-adjusted price does not fail
loudly. It produces a market cap wrong by the split factor, a plausible-looking six-year median,
and a tilt multiplier pinned at one end of its 0.80–1.20 range — which sizes a real position.
Chipotle's would have been wrong by 49x, Monster's by 2x in the other direction.

**What was done.** No data changed. The consumers were taught the shape of the defect instead:
`claude/rebuild-from-scratch.md` in the book repo carries `usable_years()`, which walks the
annual series back from the latest row, stops at the first adjacent-year ratio outside
0.72–1.4, and treats everything beyond as unmeasured; it also cross-checks the latest row
against the broker's shares outstanding (25% band) and refuses the whole name when that fails.
Fewer than four surviving years means a neutral 1.00 tilt, named in the reply. Against the 36
holdings on 9 Sep 2026 that leaves 26 with a full six years, 7 with four or five, and 3 neutral
(NFLX, TPL, MNST). The same rule is stated in the monthly re-score prompt and in the runbook's
Stage 5b.

**The durable fix, not done here.** Carry an as-filed share count alongside the restated one —
the fiscal year's own 10-K value, selected on the fact's `form`/`fy`/`fp` rather than by taking
the latest — so a six-year window survives a split instead of being truncated by it. That is a
change to `build_sec_dataset.py`'s fact selection with its own tests, and it should not be made
in the same pass as a prompt migration. Until then the truncation above is the safe behaviour.
To reproduce: read `shares_diluted` across `annual` for the tickers in the table and compare
adjacent years; compare the latest against `get_equity_fundamentals`' `shares_outstanding`.

---

## Ground rules for anyone picking this up

- `SEC_USER_AGENT` is a repo secret. Never hardcode it, never print it, never send it
  anywhere but sec.gov. Do not probe www.sec.gov from a sandbox with a placeholder contact;
  dispatch the workflow instead, so the real user-agent is used.
- Other tasks read these files by field name. Do not rename, remove or change the meaning
  of any existing key. Adding a field or a new flag value is fine.
- All three workflows refuse an empty script (`test -s`). The fundamentals build refuses to write
  if fewer than 3,000 companies parse; the filing-text build refuses if Item 1 parses for under
  60% of the filings it fetched, and runs the extractor's tests before touching any data. Keep
  every one of those guards.
- Never delete files in `data/` by hand; the build script owns that directory.
- No scoring or screening logic in this repo, and no Form 4 / insider feed unless asked.
- If a test finds a builder bug, stop and report it rather than working around it.
