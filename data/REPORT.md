# SEC dataset build — 2026-09-23T20:08:58Z

- filers scanned: 20395
- companies published: 14609
- of those, no longer filing (`active: false`): 7203
- tickers in map: 10461

A filer is published while it has filed within 15 years and marked
`active` while it has filed within 3. The second window was the first
until 15 Sep 2026, so a company that was acquired or failed left the dataset entirely and
every universe assembled from this file knew in advance who would survive. Inactive filers
carry no `sic` — the events build keeps 400 days and has already pruned them.

## Coverage by line item (companies carrying a value in a published annual row)

The question a consumer asks. A field can resolve a tag and still carry no figure in any
of the eight years this file publishes — see the tag count below, and NOTES §18.

- acquisition_cost_amort: 220
- acquisitions: 5649
- buybacks: 5938
- capex: 11041
- capitalized_software: 1053
- cash: 13143
- cash_and_short_term_investments: 911
- claims_incurred: 245
- commercial_paper: 293
- credit_loss_provision: 1442
- current_assets: 11154
- current_liabilities: 11113
- d_and_a: 11891
- debt_current: 5339
- debt_current_total: 1399
- debt_due_1y: 4688
- debt_due_2y: 4727
- debt_due_3y: 4590
- deposits: 1490
- dividends_paid: 4347
- eps_diluted: 9674
- finance_lease_liabilities: 2611
- goodwill: 6417
- gross_profit: 6457
- impairments: 7952
- income_tax: 11437
- intangibles: 5794
- interest_expense: 10903
- interest_income: 1998
- inventory: 5878
- loan_loss_allowance: 1253
- loans: 1903
- long_term_investments: 2038
- loss_reserves: 278
- lt_debt_current: 4920
- lt_debt_noncurrent: 5372
- net_income: 14578
- net_income_incl_nci: 8298
- net_income_parent: 14444
- net_interest_income: 3203
- operating_cash_flow: 14461
- operating_income: 11814
- operating_leases: 6211
- payments_for_intangibles: 3007
- pension_funded_status: 723
- premiums_earned: 249
- pretax_income: 11503
- rd_expense: 5358
- receivables: 8097
- retained_earnings: 12679
- revenue: 12038
- sga_expense: 4512
- shares_diluted: 12559
- shares_outstanding: 11463
- short_term_borrowings: 2830
- short_term_investments: 3673
- stock_comp: 10967
- tier1_capital_ratio: 553
- total_assets: 13650
- total_debt: 9968
- total_equity: 13231
- total_equity_incl_nci: 5810
- total_equity_parent: 13042
- total_liabilities: 12175

## Tag resolved anywhere in the filing history

The older count, under a name that says what it measures. A company that tagged a line
in 2012 and stopped is counted here and not above.

- acquisition_cost_amort: 244
- acquisitions: 6186
- buybacks: 6443
- capex: 11414
- capitalized_software: 1213
- cash: 14088
- cash_and_short_term_investments: 1090
- claims_incurred: 256
- commercial_paper: 344
- credit_loss_provision: 1612
- current_assets: 12048
- current_liabilities: 12013
- d_and_a: 12132
- debt_current: 5912
- debt_current_total: 1632
- debt_due_1y: 5189
- debt_due_2y: 5244
- debt_due_3y: 5089
- deposits: 1800
- dividends_paid: 4621
- eps_diluted: 10578
- finance_lease_liabilities: 2931
- goodwill: 7021
- gross_profit: 6965
- impairments: 8462
- income_tax: 11903
- intangibles: 6428
- interest_expense: 11421
- interest_income: 2209
- inventory: 6532
- loan_loss_allowance: 1396
- loans: 2135
- long_term_investments: 2533
- loss_reserves: 293
- lt_debt_current: 5402
- lt_debt_noncurrent: 5886
- net_income: 14598
- net_income_incl_nci: 9330
- net_income_parent: 14503
- net_interest_income: 3753
- operating_cash_flow: 14505
- operating_income: 12059
- operating_leases: 7094
- payments_for_intangibles: 3407
- pension_funded_status: 781
- premiums_earned: 257
- pretax_income: 11903
- rd_expense: 5533
- receivables: 9117
- retained_earnings: 13585
- revenue: 12434
- sga_expense: 4841
- shares_diluted: 13192
- shares_outstanding: 13599
- short_term_borrowings: 3658
- short_term_investments: 4252
- stock_comp: 11326
- tier1_capital_ratio: 575
- total_assets: 14544
- total_debt: 10043
- total_equity: 14134
- total_equity_incl_nci: 6468
- total_equity_parent: 13932
- total_liabilities: 13027

## Self-check: four quarters sum to the fiscal year (revenue, net income, operating cash flow, capex)

- ok: 13154
- off (one or more items miss by >3%): 155
- n/a (no fiscal year with four quarters on file): 1300

Readers treat an `off` company, or one whose latest quarter is more than 150 days old (a 10-K may lawfully take 90 days; anything older means the structured feed is behind the filing), as unmeasured on its quarterly metrics.

## Share counts (added 8 Sep 2026)

- diluted count on file: 9225
- basic count only: 331
- cover-page count only: 652
- none (multi-class filers tag by class; companyfacts drops dimensioned facts): 965
- **invalid (a share count of zero or less somewhere in the file): 896**

A reader does not drop a name on a per-share test it cannot run; `shares` in the manifest says which case applies.

## Share scale (added 9 Sep 2026)

- consistent: 11224
- **suspect: 2531** (`scale` — a diluted count more than fifty times its own outstanding count, or less than a fiftieth; `levels` — the quarterly series steps between levels more than once, so no per-share figure spans it)
- no share data at all: 854

`share_scale` says whether a company's share counts can all be true at once. It is not a reason to drop a name — it says the per-share metrics for that company are unmeasured. Both the flag and `shares` are in the manifest, so a reader need not open 7,411 company files to screen on them.

## Items added 8 Sep 2026

`current_assets`, `current_liabilities` (current ratio); `operating_leases` (beside `total_debt`; the gate treatment is a rule decision); `receivables`, `inventory`, `total_liabilities` (working-capital quality); `acquisitions`, `goodwill`, `intangibles`, `impairments`; `rd_expense`, `sga_expense`; `pension_funded_status`; `debt_due_1y/2y/3y`; bank items `net_interest_income`, `interest_income`, `deposits`, `loans`, `credit_loss_provision`, `loan_loss_allowance`, `tier1_capital_ratio` (thin — tagged by regulatory entity, which companyfacts drops); insurer items `premiums_earned`, `claims_incurred`, `acquisition_cost_amort`, `loss_reserves`. Segment revenue and per-class share data are dimensioned facts and cannot come from this file; the business briefs carry segments in words. Coverage per item is listed above — an item with low coverage is a tag most filers do not use, not a bug.

## Items added 23 Sep 2026

`short_term_investments`, `long_term_investments`, `cash_and_short_term_investments` (net cash beyond `cash`); `lt_debt_current`, `debt_current_total`, `short_term_borrowings`, `commercial_paper`, `finance_lease_liabilities` (the pieces `total_debt` is now built from, never counting one twice — `total_debt_basis` `components_exceed_tagged` marks a tagged total that was short of its own pieces, kept as `total_debt_tagged`); `capitalized_software` and `payments_for_intangibles` (their own fields, not in `capex`); per company `splits`, and per row `shares_diluted_filled` / `_source` / `_filed` and `shares_diluted_adj` (on the newest filing's basis). No existing key changed meaning; every as-filed value is untouched.
- rows where the pieces exceeded the tagged total: 524 companies (latest annual row)
- companies with at least one split found in their own share counts: 2465

## Stale-name fallback

- companies whose companyfacts quarterly series was behind their own filings: 218
- of those, patched from the filing's own XBRL this run: 193 (cap 600 filings)

A quarterly row carrying `"source": "filing"` was derived from the filing's own XBRL instance,
through the same tag map, picking rules and year-to-date differencing as every other row. A row
with no `source` came from the SEC's bulk companyfacts file. Only quarters missing from
companyfacts are added; the prior-year comparatives a filing also carries are left alone.

## S&P 500 constituents

- source: https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv
- snapshot date: 2026-09-23
- constituents: 503
- resolved to a CIK via the SEC ticker map: 503
- unmatched (no CIK in the SEC ticker map): none
- resolved but with no company file, so nothing to join to: HONA

Membership comes from a public constituents list, not from the SEC — it is a fact about
an index, not a company fundamental. `cik` is resolved through the SEC's own ticker map, so a
ticker the map has not caught up with is listed under `unmatched` rather than guessed at.
