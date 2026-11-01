# SEC dataset build — 2026-11-01T12:49:28Z

- filers scanned: 20537
- companies published: 14621
- of those, no longer filing (`active: false`): 7215
- tickers in map: 10451

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
- buybacks: 5944
- capex: 11051
- capitalized_software: 1055
- cash: 13153
- cash_and_short_term_investments: 911
- claims_incurred: 245
- commercial_paper: 294
- credit_loss_provision: 1444
- current_assets: 11162
- current_liabilities: 11122
- d_and_a: 11902
- debt_current: 5340
- debt_current_total: 1400
- debt_due_1y: 4690
- debt_due_2y: 4729
- debt_due_3y: 4592
- deposits: 1492
- dividends_paid: 4350
- eps_diluted: 9690
- finance_lease_liabilities: 2614
- goodwill: 6417
- gross_profit: 6465
- impairments: 7960
- income_tax: 11447
- intangibles: 5801
- interest_expense: 10909
- interest_income: 2002
- inventory: 5879
- loan_loss_allowance: 1256
- loans: 1905
- long_term_investments: 2041
- loss_reserves: 278
- lt_debt_current: 4923
- lt_debt_noncurrent: 5374
- net_income: 14590
- net_income_incl_nci: 8309
- net_income_parent: 14457
- net_interest_income: 3205
- operating_cash_flow: 14473
- operating_income: 11823
- operating_leases: 6216
- payments_for_intangibles: 3011
- pension_funded_status: 723
- premiums_earned: 249
- pretax_income: 11518
- rd_expense: 5365
- receivables: 8101
- retained_earnings: 12688
- revenue: 12052
- sga_expense: 4511
- shares_diluted: 12571
- shares_outstanding: 11470
- short_term_borrowings: 2833
- short_term_investments: 3680
- stock_comp: 10981
- tier1_capital_ratio: 553
- total_assets: 13659
- total_debt: 9971
- total_equity: 13240
- total_equity_incl_nci: 5814
- total_equity_parent: 13051
- total_liabilities: 12185

## Tag resolved anywhere in the filing history

The older count, under a name that says what it measures. A company that tagged a line
in 2012 and stopped is counted here and not above.

- acquisition_cost_amort: 244
- acquisitions: 6190
- buybacks: 6447
- capex: 11423
- capitalized_software: 1214
- cash: 14102
- cash_and_short_term_investments: 1090
- claims_incurred: 256
- commercial_paper: 345
- credit_loss_provision: 1616
- current_assets: 12059
- current_liabilities: 12025
- d_and_a: 12142
- debt_current: 5917
- debt_current_total: 1634
- debt_due_1y: 5194
- debt_due_2y: 5250
- debt_due_3y: 5094
- deposits: 1804
- dividends_paid: 4623
- eps_diluted: 10593
- finance_lease_liabilities: 2935
- goodwill: 7022
- gross_profit: 6971
- impairments: 8470
- income_tax: 11914
- intangibles: 6440
- interest_expense: 11428
- interest_income: 2213
- inventory: 6542
- loan_loss_allowance: 1400
- loans: 2136
- long_term_investments: 2538
- loss_reserves: 294
- lt_debt_current: 5408
- lt_debt_noncurrent: 5892
- net_income: 14610
- net_income_incl_nci: 9345
- net_income_parent: 14515
- net_interest_income: 3756
- operating_cash_flow: 14517
- operating_income: 12067
- operating_leases: 7102
- payments_for_intangibles: 3412
- pension_funded_status: 782
- premiums_earned: 257
- pretax_income: 11918
- rd_expense: 5539
- receivables: 9126
- retained_earnings: 13599
- revenue: 12447
- sga_expense: 4841
- shares_diluted: 13205
- shares_outstanding: 13609
- short_term_borrowings: 3664
- short_term_investments: 4262
- stock_comp: 11339
- tier1_capital_ratio: 575
- total_assets: 14557
- total_debt: 10047
- total_equity: 14146
- total_equity_incl_nci: 6479
- total_equity_parent: 13944
- total_liabilities: 13041

## Self-check: four quarters sum to the fiscal year (revenue, net income, operating cash flow, capex)

- ok: 13172
- off (one or more items miss by >3%): 156
- n/a (no fiscal year with four quarters on file): 1293

Readers treat an `off` company, or one whose latest quarter is more than 150 days old (a 10-K may lawfully take 90 days; anything older means the structured feed is behind the filing), as unmeasured on its quarterly metrics.

## Share counts (added 8 Sep 2026)

- diluted count on file: 9229
- basic count only: 328
- cover-page count only: 653
- none (multi-class filers tag by class; companyfacts drops dimensioned facts): 965
- **invalid (a share count of zero or less somewhere in the file): 900**

A reader does not drop a name on a per-share test it cannot run; `shares` in the manifest says which case applies.

## Share scale (added 9 Sep 2026)

- consistent: 11231
- **suspect: 2534** (`scale` — a diluted count more than fifty times its own outstanding count, or less than a fiftieth; `levels` — the quarterly series steps between levels more than once, so no per-share figure spans it)
- no share data at all: 856

`share_scale` says whether a company's share counts can all be true at once. It is not a reason to drop a name — it says the per-share metrics for that company are unmeasured. Both the flag and `shares` are in the manifest, so a reader need not open 7,411 company files to screen on them.

## Items added 8 Sep 2026

`current_assets`, `current_liabilities` (current ratio); `operating_leases` (beside `total_debt`; the gate treatment is a rule decision); `receivables`, `inventory`, `total_liabilities` (working-capital quality); `acquisitions`, `goodwill`, `intangibles`, `impairments`; `rd_expense`, `sga_expense`; `pension_funded_status`; `debt_due_1y/2y/3y`; bank items `net_interest_income`, `interest_income`, `deposits`, `loans`, `credit_loss_provision`, `loan_loss_allowance`, `tier1_capital_ratio` (thin — tagged by regulatory entity, which companyfacts drops); insurer items `premiums_earned`, `claims_incurred`, `acquisition_cost_amort`, `loss_reserves`. Segment revenue and per-class share data are dimensioned facts and cannot come from this file; the business briefs carry segments in words. Coverage per item is listed above — an item with low coverage is a tag most filers do not use, not a bug.

## Items added 23 Sep 2026

`short_term_investments`, `long_term_investments`, `cash_and_short_term_investments` (net cash beyond `cash`); `lt_debt_current`, `debt_current_total`, `short_term_borrowings`, `commercial_paper`, `finance_lease_liabilities` (the pieces `total_debt` is now built from, never counting one twice — `total_debt_basis` `components_exceed_tagged` marks a tagged total that was short of its own pieces, kept as `total_debt_tagged`); `capitalized_software` and `payments_for_intangibles` (their own fields, not in `capex`); per company `splits`, and per row `shares_diluted_filled` / `_source` / `_filed` and `shares_diluted_adj` (on the newest filing's basis). No existing key changed meaning; every as-filed value is untouched.
- rows where the pieces exceeded the tagged total: 524 companies (latest annual row)
- companies with at least one split found in their own share counts: 2479

## Stale-name fallback

- companies whose companyfacts quarterly series was behind their own filings: 124
- of those, patched from the filing's own XBRL this run: 76 (cap 600 filings)

A quarterly row carrying `"source": "filing"` was derived from the filing's own XBRL instance,
through the same tag map, picking rules and year-to-date differencing as every other row. A row
with no `source` came from the SEC's bulk companyfacts file. Only quarters missing from
companyfacts are added; the prior-year comparatives a filing also carries are left alone.
