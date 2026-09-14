# SEC dataset build — 2026-09-14T15:53:14Z

- filers scanned: 20359
- companies published: 7410
- tickers in map: 10426

## Coverage by line item (companies carrying a value in a published annual row)

The question a consumer asks. A field can resolve a tag and still carry no figure in any
of the eight years this file publishes — see the tag count below, and NOTES §18.

- acquisition_cost_amort: 141
- acquisitions: 3506
- buybacks: 3809
- capex: 6011
- cash: 6696
- claims_incurred: 158
- credit_loss_provision: 1012
- current_assets: 5502
- current_liabilities: 5485
- d_and_a: 6341
- debt_current: 3078
- debt_due_1y: 2983
- debt_due_2y: 2988
- debt_due_3y: 2904
- deposits: 789
- dividends_paid: 2784
- eps_diluted: 6408
- goodwill: 3780
- gross_profit: 3481
- impairments: 4786
- income_tax: 6395
- intangibles: 3381
- interest_expense: 5782
- interest_income: 1071
- inventory: 3146
- loan_loss_allowance: 844
- loans: 1081
- loss_reserves: 193
- lt_debt_noncurrent: 2842
- net_income: 7409
- net_income_incl_nci: 4893
- net_income_parent: 7374
- net_interest_income: 1854
- operating_cash_flow: 7375
- operating_income: 6159
- operating_leases: 5173
- pension_funded_status: 465
- premiums_earned: 165
- pretax_income: 6254
- rd_expense: 3274
- receivables: 4292
- retained_earnings: 6535
- revenue: 6477
- sga_expense: 2499
- shares_diluted: 6733
- shares_outstanding: 5666
- stock_comp: 6087
- tier1_capital_ratio: 280
- total_assets: 6779
- total_debt: 5300
- total_equity: 6640
- total_equity_incl_nci: 3229
- total_equity_parent: 6562
- total_liabilities: 6229

## Tag resolved anywhere in the filing history

The older count, under a name that says what it measures. A company that tagged a line
in 2012 and stopped is counted here and not above.

- acquisition_cost_amort: 158
- acquisitions: 3778
- buybacks: 4114
- capex: 6135
- cash: 7326
- claims_incurred: 164
- credit_loss_provision: 1110
- current_assets: 6117
- current_liabilities: 6101
- d_and_a: 6418
- debt_current: 3424
- debt_due_1y: 3312
- debt_due_2y: 3303
- debt_due_3y: 3202
- deposits: 1032
- dividends_paid: 2914
- eps_diluted: 6688
- goodwill: 4121
- gross_profit: 3697
- impairments: 4995
- income_tax: 6522
- intangibles: 3775
- interest_expense: 5999
- interest_income: 1190
- inventory: 3566
- loan_loss_allowance: 966
- loans: 1239
- loss_reserves: 204
- lt_debt_noncurrent: 3157
- net_income: 7410
- net_income_incl_nci: 5284
- net_income_parent: 7386
- net_interest_income: 2161
- operating_cash_flow: 7382
- operating_income: 6232
- operating_leases: 5798
- pension_funded_status: 500
- premiums_earned: 170
- pretax_income: 6343
- rd_expense: 3342
- receivables: 4947
- retained_earnings: 7155
- revenue: 6562
- sga_expense: 2659
- shares_diluted: 6960
- shares_outstanding: 6853
- stock_comp: 6178
- tier1_capital_ratio: 290
- total_assets: 7400
- total_debt: 5653
- total_equity: 7267
- total_equity_incl_nci: 3663
- total_equity_parent: 7178
- total_liabilities: 6822

## Self-check: four quarters sum to the fiscal year (revenue, net income, operating cash flow, capex)

- ok: 6632
- off (one or more items miss by >3%): 38
- n/a (no fiscal year with four quarters on file): 740

Readers treat an `off` company, or one whose latest quarter is more than 150 days old (a 10-K may lawfully take 90 days; anything older means the structured feed is behind the filing), as unmeasured on its quarterly metrics.

## Share counts (added 8 Sep 2026)

- diluted count on file: 6310
- basic count only: 49
- cover-page count only: 223
- none (multi-class filers tag by class; companyfacts drops dimensioned facts): 433
- **invalid (a share count of zero or less somewhere in the file): 395**

A reader does not drop a name on a per-share test it cannot run; `shares` in the manifest says which case applies.

## Share scale (added 9 Sep 2026)

- consistent: 5829
- **suspect: 1275** (`scale` — a diluted count more than fifty times its own outstanding count, or less than a fiftieth; `levels` — the quarterly series steps between levels more than once, so no per-share figure spans it)
- no share data at all: 306

`share_scale` says whether a company's share counts can all be true at once. It is not a reason to drop a name — it says the per-share metrics for that company are unmeasured. Both the flag and `shares` are in the manifest, so a reader need not open 7,411 company files to screen on them.

## Items added 8 Sep 2026

`current_assets`, `current_liabilities` (current ratio); `operating_leases` (beside `total_debt`; the gate treatment is a rule decision); `receivables`, `inventory`, `total_liabilities` (working-capital quality); `acquisitions`, `goodwill`, `intangibles`, `impairments`; `rd_expense`, `sga_expense`; `pension_funded_status`; `debt_due_1y/2y/3y`; bank items `net_interest_income`, `interest_income`, `deposits`, `loans`, `credit_loss_provision`, `loan_loss_allowance`, `tier1_capital_ratio` (thin — tagged by regulatory entity, which companyfacts drops); insurer items `premiums_earned`, `claims_incurred`, `acquisition_cost_amort`, `loss_reserves`. Segment revenue and per-class share data are dimensioned facts and cannot come from this file; the business briefs carry segments in words. Coverage per item is listed above — an item with low coverage is a tag most filers do not use, not a bug.

## Stale-name fallback

- companies whose companyfacts quarterly series was behind their own filings: 181
- of those, patched from the filing's own XBRL this run: 71 (cap 100 filings)

A quarterly row carrying `"source": "filing"` was derived from the filing's own XBRL instance,
through the same tag map, picking rules and year-to-date differencing as every other row. A row
with no `source` came from the SEC's bulk companyfacts file. Only quarters missing from
companyfacts are added; the prior-year comparatives a filing also carries are left alone.

## S&P 500 constituents

- source: https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv
- snapshot date: 2026-09-14
- constituents: 503
- resolved to a CIK via the SEC ticker map: 503
- unmatched (no CIK in the SEC ticker map): none
- resolved but with no company file, so nothing to join to: HONA

Membership comes from a public constituents list, not from the SEC — it is a fact about
an index, not a company fundamental. `cik` is resolved through the SEC's own ticker map, so a
ticker the map has not caught up with is listed under `unmatched` rather than guessed at.
