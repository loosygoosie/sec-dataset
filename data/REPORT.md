# SEC dataset build — 2026-10-04T11:28:13Z

- filers scanned: 20428
- companies published: 14614
- of those, no longer filing (`active: false`): 7203
- tickers in map: 10434

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
- buybacks: 5942
- capex: 11046
- capitalized_software: 1053
- cash: 13149
- cash_and_short_term_investments: 911
- claims_incurred: 245
- commercial_paper: 293
- credit_loss_provision: 1443
- current_assets: 11159
- current_liabilities: 11118
- d_and_a: 11896
- debt_current: 5339
- debt_current_total: 1399
- debt_due_1y: 4690
- debt_due_2y: 4729
- debt_due_3y: 4592
- deposits: 1490
- dividends_paid: 4349
- eps_diluted: 9683
- finance_lease_liabilities: 2612
- goodwill: 6417
- gross_profit: 6460
- impairments: 7959
- income_tax: 11441
- intangibles: 5796
- interest_expense: 10905
- interest_income: 2001
- inventory: 5878
- loan_loss_allowance: 1254
- loans: 1904
- long_term_investments: 2039
- loss_reserves: 278
- lt_debt_current: 4920
- lt_debt_noncurrent: 5372
- net_income: 14583
- net_income_incl_nci: 8305
- net_income_parent: 14449
- net_interest_income: 3204
- operating_cash_flow: 14466
- operating_income: 11816
- operating_leases: 6213
- payments_for_intangibles: 3009
- pension_funded_status: 723
- premiums_earned: 249
- pretax_income: 11511
- rd_expense: 5360
- receivables: 8101
- retained_earnings: 12684
- revenue: 12043
- sga_expense: 4512
- shares_diluted: 12564
- shares_outstanding: 11467
- short_term_borrowings: 2830
- short_term_investments: 3674
- stock_comp: 10972
- tier1_capital_ratio: 553
- total_assets: 13655
- total_debt: 9968
- total_equity: 13236
- total_equity_incl_nci: 5812
- total_equity_parent: 13046
- total_liabilities: 12181

## Tag resolved anywhere in the filing history

The older count, under a name that says what it measures. A company that tagged a line
in 2012 and stopped is counted here and not above.

- acquisition_cost_amort: 244
- acquisitions: 6188
- buybacks: 6444
- capex: 11418
- capitalized_software: 1213
- cash: 14094
- cash_and_short_term_investments: 1090
- claims_incurred: 256
- commercial_paper: 344
- credit_loss_provision: 1612
- current_assets: 12053
- current_liabilities: 12018
- d_and_a: 12137
- debt_current: 5913
- debt_current_total: 1633
- debt_due_1y: 5190
- debt_due_2y: 5246
- debt_due_3y: 5090
- deposits: 1800
- dividends_paid: 4622
- eps_diluted: 10585
- finance_lease_liabilities: 2933
- goodwill: 7021
- gross_profit: 6968
- impairments: 8468
- income_tax: 11907
- intangibles: 6431
- interest_expense: 11424
- interest_income: 2211
- inventory: 6533
- loan_loss_allowance: 1397
- loans: 2135
- long_term_investments: 2535
- loss_reserves: 294
- lt_debt_current: 5402
- lt_debt_noncurrent: 5886
- net_income: 14603
- net_income_incl_nci: 9336
- net_income_parent: 14508
- net_interest_income: 3754
- operating_cash_flow: 14510
- operating_income: 12061
- operating_leases: 7097
- payments_for_intangibles: 3409
- pension_funded_status: 781
- premiums_earned: 257
- pretax_income: 11911
- rd_expense: 5535
- receivables: 9122
- retained_earnings: 13591
- revenue: 12438
- sga_expense: 4841
- shares_diluted: 13196
- shares_outstanding: 13603
- short_term_borrowings: 3659
- short_term_investments: 4253
- stock_comp: 11331
- tier1_capital_ratio: 575
- total_assets: 14549
- total_debt: 10042
- total_equity: 14139
- total_equity_incl_nci: 6472
- total_equity_parent: 13936
- total_liabilities: 13034

## Self-check: four quarters sum to the fiscal year (revenue, net income, operating cash flow, capex)

- ok: 13169
- off (one or more items miss by >3%): 156
- n/a (no fiscal year with four quarters on file): 1289

Readers treat an `off` company, or one whose latest quarter is more than 150 days old (a 10-K may lawfully take 90 days; anything older means the structured feed is behind the filing), as unmeasured on its quarterly metrics.

## Share counts (added 8 Sep 2026)

- diluted count on file: 9226
- basic count only: 327
- cover-page count only: 655
- none (multi-class filers tag by class; companyfacts drops dimensioned facts): 964
- **invalid (a share count of zero or less somewhere in the file): 898**

A reader does not drop a name on a per-share test it cannot run; `shares` in the manifest says which case applies.

## Share scale (added 9 Sep 2026)

- consistent: 11226
- **suspect: 2533** (`scale` — a diluted count more than fifty times its own outstanding count, or less than a fiftieth; `levels` — the quarterly series steps between levels more than once, so no per-share figure spans it)
- no share data at all: 855

`share_scale` says whether a company's share counts can all be true at once. It is not a reason to drop a name — it says the per-share metrics for that company are unmeasured. Both the flag and `shares` are in the manifest, so a reader need not open 7,411 company files to screen on them.

## Items added 8 Sep 2026

`current_assets`, `current_liabilities` (current ratio); `operating_leases` (beside `total_debt`; the gate treatment is a rule decision); `receivables`, `inventory`, `total_liabilities` (working-capital quality); `acquisitions`, `goodwill`, `intangibles`, `impairments`; `rd_expense`, `sga_expense`; `pension_funded_status`; `debt_due_1y/2y/3y`; bank items `net_interest_income`, `interest_income`, `deposits`, `loans`, `credit_loss_provision`, `loan_loss_allowance`, `tier1_capital_ratio` (thin — tagged by regulatory entity, which companyfacts drops); insurer items `premiums_earned`, `claims_incurred`, `acquisition_cost_amort`, `loss_reserves`. Segment revenue and per-class share data are dimensioned facts and cannot come from this file; the business briefs carry segments in words. Coverage per item is listed above — an item with low coverage is a tag most filers do not use, not a bug.

## Items added 23 Sep 2026

`short_term_investments`, `long_term_investments`, `cash_and_short_term_investments` (net cash beyond `cash`); `lt_debt_current`, `debt_current_total`, `short_term_borrowings`, `commercial_paper`, `finance_lease_liabilities` (the pieces `total_debt` is now built from, never counting one twice — `total_debt_basis` `components_exceed_tagged` marks a tagged total that was short of its own pieces, kept as `total_debt_tagged`); `capitalized_software` and `payments_for_intangibles` (their own fields, not in `capex`); per company `splits`, and per row `shares_diluted_filled` / `_source` / `_filed` and `shares_diluted_adj` (on the newest filing's basis). No existing key changed meaning; every as-filed value is untouched.
- rows where the pieces exceeded the tagged total: 524 companies (latest annual row)
- companies with at least one split found in their own share counts: 2469

## Stale-name fallback

- companies whose companyfacts quarterly series was behind their own filings: 217
- of those, patched from the filing's own XBRL this run: 168 (cap 600 filings)

A quarterly row carrying `"source": "filing"` was derived from the filing's own XBRL instance,
through the same tag map, picking rules and year-to-date differencing as every other row. A row
with no `source` came from the SEC's bulk companyfacts file. Only quarters missing from
companyfacts are added; the prior-year comparatives a filing also carries are left alone.
