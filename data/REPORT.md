# SEC dataset build — 2026-11-15T13:35:57Z

- filers scanned: 20588
- companies published: 14613
- of those, no longer filing (`active: false`): 7357
- tickers in map: 10404

A filer is published while it has filed within 15 years and marked
`active` while it has filed within 3. The second window was the first
until 15 Sep 2026, so a company that was acquired or failed left the dataset entirely and
every universe assembled from this file knew in advance who would survive. Inactive filers
carry no `sic` — the events build keeps 400 days and has already pruned them.

## Coverage by line item (companies carrying a value in a published annual row)

The question a consumer asks. A field can resolve a tag and still carry no figure in any
of the eight years this file publishes — see the tag count below, and NOTES §18.

- acquisition_cost_amort: 220
- acquisitions: 5647
- buybacks: 5941
- capex: 11045
- capitalized_software: 1055
- cash: 13145
- cash_and_short_term_investments: 913
- claims_incurred: 244
- commercial_paper: 293
- credit_loss_provision: 1445
- current_assets: 11154
- current_liabilities: 11113
- d_and_a: 11894
- debt_current: 5338
- debt_current_total: 1404
- debt_due_1y: 4691
- debt_due_2y: 4729
- debt_due_3y: 4592
- deposits: 1495
- dividends_paid: 4348
- eps_diluted: 9682
- finance_lease_liabilities: 2620
- goodwill: 6415
- gross_profit: 6463
- impairments: 7961
- income_tax: 11438
- intangibles: 5802
- interest_expense: 10906
- interest_income: 2002
- inventory: 5882
- loan_loss_allowance: 1257
- loans: 1908
- long_term_investments: 2042
- loss_reserves: 277
- lt_debt_current: 4921
- lt_debt_noncurrent: 5376
- net_income: 14582
- net_income_incl_nci: 8309
- net_income_parent: 14450
- net_interest_income: 3205
- operating_cash_flow: 14465
- operating_income: 11817
- operating_leases: 6220
- payments_for_intangibles: 3010
- pension_funded_status: 723
- premiums_earned: 248
- pretax_income: 11514
- rd_expense: 5361
- receivables: 8098
- retained_earnings: 12680
- revenue: 12044
- sga_expense: 4509
- shares_diluted: 12563
- shares_outstanding: 11470
- short_term_borrowings: 2835
- short_term_investments: 3683
- stock_comp: 10974
- tier1_capital_ratio: 553
- total_assets: 13651
- total_debt: 9973
- total_equity: 13235
- total_equity_incl_nci: 5819
- total_equity_parent: 13048
- total_liabilities: 12182

## Tag resolved anywhere in the filing history

The older count, under a name that says what it measures. A company that tagged a line
in 2012 and stopped is counted here and not above.

- acquisition_cost_amort: 244
- acquisitions: 6206
- buybacks: 6462
- capex: 11418
- capitalized_software: 1219
- cash: 14095
- cash_and_short_term_investments: 1094
- claims_incurred: 255
- commercial_paper: 345
- credit_loss_provision: 1626
- current_assets: 12052
- current_liabilities: 12018
- d_and_a: 12135
- debt_current: 5921
- debt_current_total: 1641
- debt_due_1y: 5200
- debt_due_2y: 5254
- debt_due_3y: 5098
- deposits: 1812
- dividends_paid: 4635
- eps_diluted: 10590
- finance_lease_liabilities: 2943
- goodwill: 7027
- gross_profit: 6973
- impairments: 8482
- income_tax: 11909
- intangibles: 6442
- interest_expense: 11432
- interest_income: 2227
- inventory: 6547
- loan_loss_allowance: 1405
- loans: 2142
- long_term_investments: 2545
- loss_reserves: 293
- lt_debt_current: 5409
- lt_debt_noncurrent: 5897
- net_income: 14602
- net_income_incl_nci: 9354
- net_income_parent: 14512
- net_interest_income: 3761
- operating_cash_flow: 14509
- operating_income: 12061
- operating_leases: 7112
- payments_for_intangibles: 3422
- pension_funded_status: 782
- premiums_earned: 256
- pretax_income: 11914
- rd_expense: 5542
- receivables: 9127
- retained_earnings: 13592
- revenue: 12448
- sga_expense: 4846
- shares_diluted: 13201
- shares_outstanding: 13602
- short_term_borrowings: 3666
- short_term_investments: 4267
- stock_comp: 11335
- tier1_capital_ratio: 575
- total_assets: 14550
- total_debt: 10058
- total_equity: 14142
- total_equity_incl_nci: 6486
- total_equity_parent: 13943
- total_liabilities: 13038

## Self-check: four quarters sum to the fiscal year (revenue, net income, operating cash flow, capex)

- ok: 13201
- off (one or more items miss by >3%): 158
- n/a (no fiscal year with four quarters on file): 1254

Readers treat an `off` company, or one whose latest quarter is more than 150 days old (a 10-K may lawfully take 90 days; anything older means the structured feed is behind the filing), as unmeasured on its quarterly metrics.

## Share counts (added 8 Sep 2026)

- diluted count on file: 9222
- basic count only: 327
- cover-page count only: 653
- none (multi-class filers tag by class; companyfacts drops dimensioned facts): 967
- **invalid (a share count of zero or less somewhere in the file): 897**

A reader does not drop a name on a per-share test it cannot run; `shares` in the manifest says which case applies.

## Share scale (added 9 Sep 2026)

- consistent: 11218
- **suspect: 2543** (`scale` — a diluted count more than fifty times its own outstanding count, or less than a fiftieth; `levels` — the quarterly series steps between levels more than once, so no per-share figure spans it)
- no share data at all: 852

`share_scale` says whether a company's share counts can all be true at once. It is not a reason to drop a name — it says the per-share metrics for that company are unmeasured. Both the flag and `shares` are in the manifest, so a reader need not open 7,411 company files to screen on them.

## Items added 8 Sep 2026

`current_assets`, `current_liabilities` (current ratio); `operating_leases` (beside `total_debt`; the gate treatment is a rule decision); `receivables`, `inventory`, `total_liabilities` (working-capital quality); `acquisitions`, `goodwill`, `intangibles`, `impairments`; `rd_expense`, `sga_expense`; `pension_funded_status`; `debt_due_1y/2y/3y`; bank items `net_interest_income`, `interest_income`, `deposits`, `loans`, `credit_loss_provision`, `loan_loss_allowance`, `tier1_capital_ratio` (thin — tagged by regulatory entity, which companyfacts drops); insurer items `premiums_earned`, `claims_incurred`, `acquisition_cost_amort`, `loss_reserves`. Segment revenue and per-class share data are dimensioned facts and cannot come from this file; the business briefs carry segments in words. Coverage per item is listed above — an item with low coverage is a tag most filers do not use, not a bug.

## Items added 23 Sep 2026

`short_term_investments`, `long_term_investments`, `cash_and_short_term_investments` (net cash beyond `cash`); `lt_debt_current`, `debt_current_total`, `short_term_borrowings`, `commercial_paper`, `finance_lease_liabilities` (the pieces `total_debt` is now built from, never counting one twice — `total_debt_basis` `components_exceed_tagged` marks a tagged total that was short of its own pieces, kept as `total_debt_tagged`); `capitalized_software` and `payments_for_intangibles` (their own fields, not in `capex`); per company `splits`, and per row `shares_diluted_filled` / `_source` / `_filed` and `shares_diluted_adj` (on the newest filing's basis). No existing key changed meaning; every as-filed value is untouched.
- rows where the pieces exceeded the tagged total: 526 companies (latest annual row)
- companies with at least one split found in their own share counts: 2502

## Stale-name fallback

- companies whose companyfacts quarterly series was behind their own filings: 109
- of those, patched from the filing's own XBRL this run: 64 (cap 600 filings)

A quarterly row carrying `"source": "filing"` was derived from the filing's own XBRL instance,
through the same tag map, picking rules and year-to-date differencing as every other row. A row
with no `source` came from the SEC's bulk companyfacts file. Only quarters missing from
companyfacts are added; the prior-year comparatives a filing also carries are left alone.
