# SEC dataset build — 2026-09-15T03:55:58Z

- filers scanned: 20359
- companies published: 14608
- of those, no longer filing (`active: false`): 7199
- tickers in map: 10422

A filer is published while it has filed within 15 years and marked
`active` while it has filed within 3. The second window was the first
until 15 Sep 2026, so a company that was acquired or failed left the dataset entirely and
every universe assembled from this file knew in advance who would survive. Inactive filers
carry no `sic` — the events build keeps 400 days and has already pruned them.

## Coverage by line item (companies carrying a value in a published annual row)

The question a consumer asks. A field can resolve a tag and still carry no figure in any
of the eight years this file publishes — see the tag count below, and NOTES §18.

- acquisition_cost_amort: 220
- acquisitions: 5648
- buybacks: 5937
- capex: 11040
- cash: 13142
- claims_incurred: 245
- credit_loss_provision: 1442
- current_assets: 11153
- current_liabilities: 11112
- d_and_a: 11890
- debt_current: 5336
- debt_due_1y: 4687
- debt_due_2y: 4726
- debt_due_3y: 4589
- deposits: 1490
- dividends_paid: 4347
- eps_diluted: 9674
- goodwill: 6416
- gross_profit: 6455
- impairments: 7951
- income_tax: 11435
- intangibles: 5793
- interest_expense: 10902
- interest_income: 1998
- inventory: 5877
- loan_loss_allowance: 1253
- loans: 1903
- loss_reserves: 278
- lt_debt_noncurrent: 4828
- net_income: 14577
- net_income_incl_nci: 8297
- net_income_parent: 14443
- net_interest_income: 3203
- operating_cash_flow: 14460
- operating_income: 11813
- operating_leases: 6210
- pension_funded_status: 723
- premiums_earned: 249
- pretax_income: 11502
- rd_expense: 5358
- receivables: 8096
- retained_earnings: 12678
- revenue: 12037
- sga_expense: 4511
- shares_diluted: 12559
- shares_outstanding: 11463
- stock_comp: 10966
- tier1_capital_ratio: 553
- total_assets: 13649
- total_debt: 9591
- total_equity: 13230
- total_equity_incl_nci: 5808
- total_equity_parent: 13041
- total_liabilities: 12173

## Tag resolved anywhere in the filing history

The older count, under a name that says what it measures. A company that tagged a line
in 2012 and stopped is counted here and not above.

- acquisition_cost_amort: 244
- acquisitions: 6185
- buybacks: 6442
- capex: 11413
- cash: 14087
- claims_incurred: 256
- credit_loss_provision: 1612
- current_assets: 12047
- current_liabilities: 12012
- d_and_a: 12130
- debt_current: 5909
- debt_due_1y: 5187
- debt_due_2y: 5242
- debt_due_3y: 5087
- deposits: 1800
- dividends_paid: 4621
- eps_diluted: 10578
- goodwill: 7019
- gross_profit: 6964
- impairments: 8461
- income_tax: 11901
- intangibles: 6424
- interest_expense: 11419
- interest_income: 2209
- inventory: 6531
- loan_loss_allowance: 1396
- loans: 2135
- loss_reserves: 293
- lt_debt_noncurrent: 5308
- net_income: 14597
- net_income_incl_nci: 9328
- net_income_parent: 14502
- net_interest_income: 3753
- operating_cash_flow: 14504
- operating_income: 12058
- operating_leases: 7093
- pension_funded_status: 781
- premiums_earned: 257
- pretax_income: 11901
- rd_expense: 5533
- receivables: 9116
- retained_earnings: 13584
- revenue: 12433
- sga_expense: 4840
- shares_diluted: 13191
- shares_outstanding: 13599
- stock_comp: 11325
- tier1_capital_ratio: 575
- total_assets: 14543
- total_debt: 10041
- total_equity: 14133
- total_equity_incl_nci: 6465
- total_equity_parent: 13931
- total_liabilities: 13025

## Self-check: four quarters sum to the fiscal year (revenue, net income, operating cash flow, capex)

- ok: 13161
- off (one or more items miss by >3%): 154
- n/a (no fiscal year with four quarters on file): 1293

Readers treat an `off` company, or one whose latest quarter is more than 150 days old (a 10-K may lawfully take 90 days; anything older means the structured feed is behind the filing), as unmeasured on its quarterly metrics.

## Share counts (added 8 Sep 2026)

- diluted count on file: 9222
- basic count only: 330
- cover-page count only: 653
- none (multi-class filers tag by class; companyfacts drops dimensioned facts): 965
- **invalid (a share count of zero or less somewhere in the file): 898**

A reader does not drop a name on a per-share test it cannot run; `shares` in the manifest says which case applies.

## Share scale (added 9 Sep 2026)

- consistent: 11223
- **suspect: 2529** (`scale` — a diluted count more than fifty times its own outstanding count, or less than a fiftieth; `levels` — the quarterly series steps between levels more than once, so no per-share figure spans it)
- no share data at all: 856

`share_scale` says whether a company's share counts can all be true at once. It is not a reason to drop a name — it says the per-share metrics for that company are unmeasured. Both the flag and `shares` are in the manifest, so a reader need not open 7,411 company files to screen on them.

## Items added 8 Sep 2026

`current_assets`, `current_liabilities` (current ratio); `operating_leases` (beside `total_debt`; the gate treatment is a rule decision); `receivables`, `inventory`, `total_liabilities` (working-capital quality); `acquisitions`, `goodwill`, `intangibles`, `impairments`; `rd_expense`, `sga_expense`; `pension_funded_status`; `debt_due_1y/2y/3y`; bank items `net_interest_income`, `interest_income`, `deposits`, `loans`, `credit_loss_provision`, `loan_loss_allowance`, `tier1_capital_ratio` (thin — tagged by regulatory entity, which companyfacts drops); insurer items `premiums_earned`, `claims_incurred`, `acquisition_cost_amort`, `loss_reserves`. Segment revenue and per-class share data are dimensioned facts and cannot come from this file; the business briefs carry segments in words. Coverage per item is listed above — an item with low coverage is a tag most filers do not use, not a bug.

## Stale-name fallback

- companies whose companyfacts quarterly series was behind their own filings: 216
- of those, patched from the filing's own XBRL this run: 73 (cap 100 filings)

A quarterly row carrying `"source": "filing"` was derived from the filing's own XBRL instance,
through the same tag map, picking rules and year-to-date differencing as every other row. A row
with no `source` came from the SEC's bulk companyfacts file. Only quarters missing from
companyfacts are added; the prior-year comparatives a filing also carries are left alone.

## S&P 500 constituents

- source: https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv
- snapshot date: 2026-09-15
- constituents: 503
- resolved to a CIK via the SEC ticker map: 503
- unmatched (no CIK in the SEC ticker map): none
- resolved but with no company file, so nothing to join to: HONA

Membership comes from a public constituents list, not from the SEC — it is a fact about
an index, not a company fundamental. `cik` is resolved through the SEC's own ticker map, so a
ticker the map has not caught up with is listed under `unmatched` rather than guessed at.
