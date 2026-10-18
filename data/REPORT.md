# SEC dataset build — 2026-10-18T10:34:21Z

- filers scanned: 20472
- companies published: 14617
- of those, no longer filing (`active: false`): 7209
- tickers in map: 10449

A filer is published while it has filed within 15 years and marked
`active` while it has filed within 3. The second window was the first
until 15 Sep 2026, so a company that was acquired or failed left the dataset entirely and
every universe assembled from this file knew in advance who would survive. Inactive filers
carry no `sic` — the events build keeps 400 days and has already pruned them.

## Coverage by line item (companies carrying a value in a published annual row)

The question a consumer asks. A field can resolve a tag and still carry no figure in any
of the eight years this file publishes — see the tag count below, and NOTES §18.

- acquisition_cost_amort: 220
- acquisitions: 5652
- buybacks: 5943
- capex: 11049
- capitalized_software: 1055
- cash: 13152
- cash_and_short_term_investments: 910
- claims_incurred: 245
- commercial_paper: 293
- credit_loss_provision: 1443
- current_assets: 11160
- current_liabilities: 11120
- d_and_a: 11897
- debt_current: 5339
- debt_current_total: 1399
- debt_due_1y: 4690
- debt_due_2y: 4729
- debt_due_3y: 4592
- deposits: 1491
- dividends_paid: 4348
- eps_diluted: 9686
- finance_lease_liabilities: 2613
- goodwill: 6417
- gross_profit: 6462
- impairments: 7960
- income_tax: 11446
- intangibles: 5796
- interest_expense: 10907
- interest_income: 2002
- inventory: 5878
- loan_loss_allowance: 1255
- loans: 1904
- long_term_investments: 2039
- loss_reserves: 278
- lt_debt_current: 4920
- lt_debt_noncurrent: 5372
- net_income: 14586
- net_income_incl_nci: 8306
- net_income_parent: 14453
- net_interest_income: 3204
- operating_cash_flow: 14469
- operating_income: 11820
- operating_leases: 6215
- payments_for_intangibles: 3009
- pension_funded_status: 723
- premiums_earned: 249
- pretax_income: 11513
- rd_expense: 5361
- receivables: 8101
- retained_earnings: 12686
- revenue: 12047
- sga_expense: 4511
- shares_diluted: 12566
- shares_outstanding: 11468
- short_term_borrowings: 2833
- short_term_investments: 3674
- stock_comp: 10974
- tier1_capital_ratio: 553
- total_assets: 13657
- total_debt: 9969
- total_equity: 13238
- total_equity_incl_nci: 5812
- total_equity_parent: 13049
- total_liabilities: 12183

## Tag resolved anywhere in the filing history

The older count, under a name that says what it measures. A company that tagged a line
in 2012 and stopped is counted here and not above.

- acquisition_cost_amort: 244
- acquisitions: 6189
- buybacks: 6445
- capex: 11422
- capitalized_software: 1214
- cash: 14098
- cash_and_short_term_investments: 1089
- claims_incurred: 256
- commercial_paper: 344
- credit_loss_provision: 1612
- current_assets: 12055
- current_liabilities: 12021
- d_and_a: 12138
- debt_current: 5913
- debt_current_total: 1633
- debt_due_1y: 5191
- debt_due_2y: 5247
- debt_due_3y: 5091
- deposits: 1802
- dividends_paid: 4621
- eps_diluted: 10588
- finance_lease_liabilities: 2935
- goodwill: 7021
- gross_profit: 6970
- impairments: 8468
- income_tax: 11912
- intangibles: 6432
- interest_expense: 11426
- interest_income: 2212
- inventory: 6535
- loan_loss_allowance: 1398
- loans: 2135
- long_term_investments: 2536
- loss_reserves: 294
- lt_debt_current: 5402
- lt_debt_noncurrent: 5886
- net_income: 14606
- net_income_incl_nci: 9337
- net_income_parent: 14511
- net_interest_income: 3755
- operating_cash_flow: 14513
- operating_income: 12064
- operating_leases: 7099
- payments_for_intangibles: 3409
- pension_funded_status: 781
- premiums_earned: 257
- pretax_income: 11913
- rd_expense: 5536
- receivables: 9123
- retained_earnings: 13594
- revenue: 12443
- sga_expense: 4841
- shares_diluted: 13199
- shares_outstanding: 13605
- short_term_borrowings: 3662
- short_term_investments: 4254
- stock_comp: 11333
- tier1_capital_ratio: 575
- total_assets: 14553
- total_debt: 10044
- total_equity: 14142
- total_equity_incl_nci: 6474
- total_equity_parent: 13940
- total_liabilities: 13037

## Self-check: four quarters sum to the fiscal year (revenue, net income, operating cash flow, capex)

- ok: 13172
- off (one or more items miss by >3%): 156
- n/a (no fiscal year with four quarters on file): 1289

Readers treat an `off` company, or one whose latest quarter is more than 150 days old (a 10-K may lawfully take 90 days; anything older means the structured feed is behind the filing), as unmeasured on its quarterly metrics.

## Share counts (added 8 Sep 2026)

- diluted count on file: 9228
- basic count only: 327
- cover-page count only: 654
- none (multi-class filers tag by class; companyfacts drops dimensioned facts): 965
- **invalid (a share count of zero or less somewhere in the file): 899**

A reader does not drop a name on a per-share test it cannot run; `shares` in the manifest says which case applies.

## Share scale (added 9 Sep 2026)

- consistent: 11226
- **suspect: 2535** (`scale` — a diluted count more than fifty times its own outstanding count, or less than a fiftieth; `levels` — the quarterly series steps between levels more than once, so no per-share figure spans it)
- no share data at all: 856

`share_scale` says whether a company's share counts can all be true at once. It is not a reason to drop a name — it says the per-share metrics for that company are unmeasured. Both the flag and `shares` are in the manifest, so a reader need not open 7,411 company files to screen on them.

## Items added 8 Sep 2026

`current_assets`, `current_liabilities` (current ratio); `operating_leases` (beside `total_debt`; the gate treatment is a rule decision); `receivables`, `inventory`, `total_liabilities` (working-capital quality); `acquisitions`, `goodwill`, `intangibles`, `impairments`; `rd_expense`, `sga_expense`; `pension_funded_status`; `debt_due_1y/2y/3y`; bank items `net_interest_income`, `interest_income`, `deposits`, `loans`, `credit_loss_provision`, `loan_loss_allowance`, `tier1_capital_ratio` (thin — tagged by regulatory entity, which companyfacts drops); insurer items `premiums_earned`, `claims_incurred`, `acquisition_cost_amort`, `loss_reserves`. Segment revenue and per-class share data are dimensioned facts and cannot come from this file; the business briefs carry segments in words. Coverage per item is listed above — an item with low coverage is a tag most filers do not use, not a bug.

## Items added 23 Sep 2026

`short_term_investments`, `long_term_investments`, `cash_and_short_term_investments` (net cash beyond `cash`); `lt_debt_current`, `debt_current_total`, `short_term_borrowings`, `commercial_paper`, `finance_lease_liabilities` (the pieces `total_debt` is now built from, never counting one twice — `total_debt_basis` `components_exceed_tagged` marks a tagged total that was short of its own pieces, kept as `total_debt_tagged`); `capitalized_software` and `payments_for_intangibles` (their own fields, not in `capex`); per company `splits`, and per row `shares_diluted_filled` / `_source` / `_filed` and `shares_diluted_adj` (on the newest filing's basis). No existing key changed meaning; every as-filed value is untouched.
- rows where the pieces exceeded the tagged total: 523 companies (latest annual row)
- companies with at least one split found in their own share counts: 2471

## Stale-name fallback

- companies whose companyfacts quarterly series was behind their own filings: 217
- of those, patched from the filing's own XBRL this run: 168 (cap 600 filings)

A quarterly row carrying `"source": "filing"` was derived from the filing's own XBRL instance,
through the same tag map, picking rules and year-to-date differencing as every other row. A row
with no `source` came from the SEC's bulk companyfacts file. Only quarters missing from
companyfacts are added; the prior-year comparatives a filing also carries are left alone.
