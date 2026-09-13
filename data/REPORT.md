# SEC dataset build — 2026-09-13T17:09:49Z

- filers scanned: 20359
- companies published: 7409
- tickers in map: 10426

## Coverage by line item (companies carrying a value in a published annual row)

The question a consumer asks. A field can resolve a tag and still carry no figure in any
of the eight years this file publishes — see the tag count below, and NOTES §18.

- acquisition_cost_amort: 134
- acquisitions: 3124
- buybacks: 3492
- capex: 5903
- cash: 6664
- claims_incurred: 146
- credit_loss_provision: 963
- current_assets: 5471
- current_liabilities: 5452
- d_and_a: 6284
- debt_current: 2832
- debt_due_1y: 2686
- debt_due_2y: 2687
- debt_due_3y: 2622
- deposits: 703
- dividends_paid: 2594
- eps_diluted: 6365
- goodwill: 3662
- gross_profit: 3343
- impairments: 4461
- income_tax: 6312
- intangibles: 3082
- interest_expense: 5511
- interest_income: 987
- inventory: 2999
- loan_loss_allowance: 781
- loans: 947
- loss_reserves: 176
- lt_debt_noncurrent: 2558
- net_income: 7407
- net_income_incl_nci: 4647
- net_income_parent: 7350
- net_interest_income: 1668
- operating_cash_flow: 7369
- operating_income: 6074
- operating_leases: 5173
- pension_funded_status: 379
- premiums_earned: 158
- pretax_income: 6179
- rd_expense: 3202
- receivables: 4182
- retained_earnings: 6497
- revenue: 6423
- sga_expense: 2417
- shares_diluted: 6705
- shares_outstanding: 5495
- stock_comp: 5988
- tier1_capital_ratio: 240
- total_assets: 6769
- total_debt: 4887
- total_equity: 6619
- total_equity_incl_nci: 2805
- total_equity_parent: 6518
- total_liabilities: 6173

## Tag resolved anywhere in the filing history

The older count, under a name that says what it measures. A company that tagged a line
in 2012 and stopped is counted here and not above.

- acquisition_cost_amort: 157
- acquisitions: 3777
- buybacks: 4113
- capex: 6135
- cash: 7325
- claims_incurred: 163
- credit_loss_provision: 1110
- current_assets: 6117
- current_liabilities: 6101
- d_and_a: 6417
- debt_current: 3424
- debt_due_1y: 3311
- debt_due_2y: 3302
- debt_due_3y: 3201
- deposits: 1031
- dividends_paid: 2913
- eps_diluted: 6687
- goodwill: 4120
- gross_profit: 3697
- impairments: 4994
- income_tax: 6521
- intangibles: 3774
- interest_expense: 5998
- interest_income: 1190
- inventory: 3566
- loan_loss_allowance: 965
- loans: 1239
- loss_reserves: 204
- lt_debt_noncurrent: 3157
- net_income: 7409
- net_income_incl_nci: 5283
- net_income_parent: 7385
- net_interest_income: 2161
- operating_cash_flow: 7381
- operating_income: 6231
- operating_leases: 5798
- pension_funded_status: 499
- premiums_earned: 170
- pretax_income: 6343
- rd_expense: 3342
- receivables: 4947
- retained_earnings: 7154
- revenue: 6561
- sga_expense: 2658
- shares_diluted: 6959
- shares_outstanding: 6852
- stock_comp: 6178
- tier1_capital_ratio: 290
- total_assets: 7399
- total_debt: 5652
- total_equity: 7266
- total_equity_incl_nci: 3662
- total_equity_parent: 7177
- total_liabilities: 6821

## Self-check: four quarters sum to the fiscal year (revenue, net income, operating cash flow, capex)

- ok: 6627
- off (one or more items miss by >3%): 37
- n/a (no fiscal year with four quarters on file): 745

Readers treat an `off` company, or one whose latest quarter is more than 150 days old (a 10-K may lawfully take 90 days; anything older means the structured feed is behind the filing), as unmeasured on its quarterly metrics.

## Share counts (added 8 Sep 2026)

- diluted count on file: 6426
- basic count only: 54
- cover-page count only: 224
- none (multi-class filers tag by class; companyfacts drops dimensioned facts): 441
- **invalid (a share count of zero or less somewhere in the file): 264**

A reader does not drop a name on a per-share test it cannot run; `shares` in the manifest says which case applies.

## Share scale (added 9 Sep 2026)

- consistent: 6007
- **suspect: 1057** (`scale` — a diluted count more than fifty times its own outstanding count, or less than a fiftieth; `levels` — the quarterly series steps between levels more than once, so no per-share figure spans it)
- no share data at all: 345

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
- snapshot date: 2026-09-13
- constituents: 503
- resolved to a CIK via the SEC ticker map: 503
- unmatched (no CIK in the SEC ticker map): none
- resolved but with no company file, so nothing to join to: HONA

Membership comes from a public constituents list, not from the SEC — it is a fact about
an index, not a company fundamental. `cik` is resolved through the SEC's own ticker map, so a
ticker the map has not caught up with is listed under `unmatched` rather than guessed at.
