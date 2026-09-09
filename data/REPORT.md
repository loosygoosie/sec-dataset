# SEC dataset build — 2026-09-09T04:28:38Z

- filers scanned: 20335
- companies published: 7411
- tickers in map: 10425

## Coverage by line item (companies with at least one value)

- acquisition_cost_amort: 157
- acquisitions: 3776
- buybacks: 4113
- capex: 6136
- cash: 7327
- claims_incurred: 163
- credit_loss_provision: 1110
- current_assets: 6119
- current_liabilities: 6103
- d_and_a: 6418
- debt_current: 3422
- debt_due_1y: 3312
- debt_due_2y: 3303
- debt_due_3y: 3202
- deposits: 1032
- dividends_paid: 2912
- eps_diluted: 6689
- goodwill: 4121
- gross_profit: 3699
- impairments: 4995
- income_tax: 6521
- intangibles: 3775
- interest_expense: 6000
- interest_income: 1190
- inventory: 3567
- loan_loss_allowance: 965
- loans: 1239
- loss_reserves: 203
- lt_debt_noncurrent: 3156
- net_income: 7411
- net_interest_income: 2161
- operating_cash_flow: 7383
- operating_income: 6232
- operating_leases: 5799
- pension_funded_status: 499
- premiums_earned: 170
- pretax_income: 6343
- rd_expense: 3341
- receivables: 4948
- revenue: 6562
- sga_expense: 2659
- shares_diluted: 6961
- shares_outstanding: 6854
- stock_comp: 6180
- tier1_capital_ratio: 290
- total_assets: 7401
- total_debt: 5652
- total_equity: 7268
- total_liabilities: 6823

## Self-check: four quarters sum to the fiscal year (revenue, net income, operating cash flow, capex)

- ok: 6630
- off (one or more items miss by >3%): 34
- n/a (no fiscal year with four quarters on file): 747

Readers treat an `off` company, or one whose latest quarter is more than 150 days old (a 10-K may lawfully take 90 days; anything older means the structured feed is behind the filing), as unmeasured on its quarterly metrics.

## Share counts (added 8 Sep 2026)

- diluted count on file: 6666
- basic count only: 71
- cover-page count only: 283
- none (multi-class filers tag by class; companyfacts drops dimensioned facts): 127
- **invalid (a share count of zero or less somewhere in the file): 264**

A reader does not drop a name on a per-share test it cannot run; `shares` in the manifest says which case applies.

## Items added 8 Sep 2026

`current_assets`, `current_liabilities` (current ratio); `operating_leases` (beside `total_debt`; the gate treatment is a rule decision); `receivables`, `inventory`, `total_liabilities` (working-capital quality); `acquisitions`, `goodwill`, `intangibles`, `impairments`; `rd_expense`, `sga_expense`; `pension_funded_status`; `debt_due_1y/2y/3y`; bank items `net_interest_income`, `interest_income`, `deposits`, `loans`, `credit_loss_provision`, `loan_loss_allowance`, `tier1_capital_ratio` (thin — tagged by regulatory entity, which companyfacts drops); insurer items `premiums_earned`, `claims_incurred`, `acquisition_cost_amort`, `loss_reserves`. Segment revenue and per-class share data are dimensioned facts and cannot come from this file; the business briefs carry segments in words. Coverage per item is listed above — an item with low coverage is a tag most filers do not use, not a bug.

## Stale-name fallback

- companies whose companyfacts quarterly series was behind their own filings: 188
- of those, patched from the filing's own XBRL this run: 71 (cap 100 filings)

A quarterly row carrying `"source": "filing"` was derived from the filing's own XBRL instance,
through the same tag map, picking rules and year-to-date differencing as every other row. A row
with no `source` came from the SEC's bulk companyfacts file. Only quarters missing from
companyfacts are added; the prior-year comparatives a filing also carries are left alone.

## S&P 500 constituents

- source: https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv
- snapshot date: 2026-09-09
- constituents: 503
- resolved to a CIK via the SEC ticker map: 503
- unmatched (no CIK in the SEC ticker map): none
- resolved but with no company file, so nothing to join to: HONA

Membership comes from a public constituents list, not from the SEC — it is a fact about
an index, not a company fundamental. `cik` is resolved through the SEC's own ticker map, so a
ticker the map has not caught up with is listed under `unmatched` rather than guessed at.
