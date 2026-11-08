# SEC dataset build — 2026-11-08T12:57:03Z

- filers scanned: 20559
- companies published: 14612
- of those, no longer filing (`active: false`): 7231
- tickers in map: 10429

A filer is published while it has filed within 15 years and marked
`active` while it has filed within 3. The second window was the first
until 15 Sep 2026, so a company that was acquired or failed left the dataset entirely and
every universe assembled from this file knew in advance who would survive. Inactive filers
carry no `sic` — the events build keeps 400 days and has already pruned them.

## Coverage by line item (companies carrying a value in a published annual row)

The question a consumer asks. A field can resolve a tag and still carry no figure in any
of the eight years this file publishes — see the tag count below, and NOTES §18.

- acquisition_cost_amort: 220
- acquisitions: 5646
- buybacks: 5940
- capex: 11046
- capitalized_software: 1055
- cash: 13144
- cash_and_short_term_investments: 911
- claims_incurred: 244
- commercial_paper: 293
- credit_loss_provision: 1445
- current_assets: 11153
- current_liabilities: 11113
- d_and_a: 11895
- debt_current: 5336
- debt_current_total: 1402
- debt_due_1y: 4690
- debt_due_2y: 4729
- debt_due_3y: 4592
- deposits: 1492
- dividends_paid: 4347
- eps_diluted: 9682
- finance_lease_liabilities: 2617
- goodwill: 6411
- gross_profit: 6463
- impairments: 7960
- income_tax: 11440
- intangibles: 5799
- interest_expense: 10905
- interest_income: 2002
- inventory: 5876
- loan_loss_allowance: 1256
- loans: 1905
- long_term_investments: 2039
- loss_reserves: 277
- lt_debt_current: 4918
- lt_debt_noncurrent: 5373
- net_income: 14581
- net_income_incl_nci: 8308
- net_income_parent: 14448
- net_interest_income: 3205
- operating_cash_flow: 14464
- operating_income: 11817
- operating_leases: 6218
- payments_for_intangibles: 3009
- pension_funded_status: 723
- premiums_earned: 248
- pretax_income: 11514
- rd_expense: 5362
- receivables: 8096
- retained_earnings: 12679
- revenue: 12045
- sga_expense: 4508
- shares_diluted: 12563
- shares_outstanding: 11466
- short_term_borrowings: 2835
- short_term_investments: 3681
- stock_comp: 10974
- tier1_capital_ratio: 553
- total_assets: 13650
- total_debt: 9966
- total_equity: 13232
- total_equity_incl_nci: 5813
- total_equity_parent: 13044
- total_liabilities: 12180

## Tag resolved anywhere in the filing history

The older count, under a name that says what it measures. A company that tagged a line
in 2012 and stopped is counted here and not above.

- acquisition_cost_amort: 244
- acquisitions: 6194
- buybacks: 6452
- capex: 11418
- capitalized_software: 1215
- cash: 14094
- cash_and_short_term_investments: 1091
- claims_incurred: 255
- commercial_paper: 345
- credit_loss_provision: 1622
- current_assets: 12051
- current_liabilities: 12017
- d_and_a: 12135
- debt_current: 5915
- debt_current_total: 1636
- debt_due_1y: 5194
- debt_due_2y: 5250
- debt_due_3y: 5094
- deposits: 1805
- dividends_paid: 4626
- eps_diluted: 10587
- finance_lease_liabilities: 2940
- goodwill: 7016
- gross_profit: 6971
- impairments: 8471
- income_tax: 11907
- intangibles: 6437
- interest_expense: 11427
- interest_income: 2222
- inventory: 6540
- loan_loss_allowance: 1402
- loans: 2137
- long_term_investments: 2538
- loss_reserves: 293
- lt_debt_current: 5405
- lt_debt_noncurrent: 5891
- net_income: 14601
- net_income_incl_nci: 9349
- net_income_parent: 14509
- net_interest_income: 3759
- operating_cash_flow: 14508
- operating_income: 12061
- operating_leases: 7107
- payments_for_intangibles: 3420
- pension_funded_status: 782
- premiums_earned: 256
- pretax_income: 11914
- rd_expense: 5539
- receivables: 9124
- retained_earnings: 13591
- revenue: 12443
- sga_expense: 4841
- shares_diluted: 13199
- shares_outstanding: 13600
- short_term_borrowings: 3665
- short_term_investments: 4263
- stock_comp: 11333
- tier1_capital_ratio: 575
- total_assets: 14549
- total_debt: 10044
- total_equity: 14139
- total_equity_incl_nci: 6479
- total_equity_parent: 13939
- total_liabilities: 13036

## Self-check: four quarters sum to the fiscal year (revenue, net income, operating cash flow, capex)

- ok: 13174
- off (one or more items miss by >3%): 158
- n/a (no fiscal year with four quarters on file): 1280

Readers treat an `off` company, or one whose latest quarter is more than 150 days old (a 10-K may lawfully take 90 days; anything older means the structured feed is behind the filing), as unmeasured on its quarterly metrics.

## Share counts (added 8 Sep 2026)

- diluted count on file: 9220
- basic count only: 328
- cover-page count only: 653
- none (multi-class filers tag by class; companyfacts drops dimensioned facts): 964
- **invalid (a share count of zero or less somewhere in the file): 900**

A reader does not drop a name on a per-share test it cannot run; `shares` in the manifest says which case applies.

## Share scale (added 9 Sep 2026)

- consistent: 11223
- **suspect: 2536** (`scale` — a diluted count more than fifty times its own outstanding count, or less than a fiftieth; `levels` — the quarterly series steps between levels more than once, so no per-share figure spans it)
- no share data at all: 853

`share_scale` says whether a company's share counts can all be true at once. It is not a reason to drop a name — it says the per-share metrics for that company are unmeasured. Both the flag and `shares` are in the manifest, so a reader need not open 7,411 company files to screen on them.

## Items added 8 Sep 2026

`current_assets`, `current_liabilities` (current ratio); `operating_leases` (beside `total_debt`; the gate treatment is a rule decision); `receivables`, `inventory`, `total_liabilities` (working-capital quality); `acquisitions`, `goodwill`, `intangibles`, `impairments`; `rd_expense`, `sga_expense`; `pension_funded_status`; `debt_due_1y/2y/3y`; bank items `net_interest_income`, `interest_income`, `deposits`, `loans`, `credit_loss_provision`, `loan_loss_allowance`, `tier1_capital_ratio` (thin — tagged by regulatory entity, which companyfacts drops); insurer items `premiums_earned`, `claims_incurred`, `acquisition_cost_amort`, `loss_reserves`. Segment revenue and per-class share data are dimensioned facts and cannot come from this file; the business briefs carry segments in words. Coverage per item is listed above — an item with low coverage is a tag most filers do not use, not a bug.

## Items added 23 Sep 2026

`short_term_investments`, `long_term_investments`, `cash_and_short_term_investments` (net cash beyond `cash`); `lt_debt_current`, `debt_current_total`, `short_term_borrowings`, `commercial_paper`, `finance_lease_liabilities` (the pieces `total_debt` is now built from, never counting one twice — `total_debt_basis` `components_exceed_tagged` marks a tagged total that was short of its own pieces, kept as `total_debt_tagged`); `capitalized_software` and `payments_for_intangibles` (their own fields, not in `capex`); per company `splits`, and per row `shares_diluted_filled` / `_source` / `_filed` and `shares_diluted_adj` (on the newest filing's basis). No existing key changed meaning; every as-filed value is untouched.
- rows where the pieces exceeded the tagged total: 524 companies (latest annual row)
- companies with at least one split found in their own share counts: 2487

## Stale-name fallback

- companies whose companyfacts quarterly series was behind their own filings: 114
- of those, patched from the filing's own XBRL this run: 67 (cap 600 filings)

A quarterly row carrying `"source": "filing"` was derived from the filing's own XBRL instance,
through the same tag map, picking rules and year-to-date differencing as every other row. A row
with no `source` came from the SEC's bulk companyfacts file. Only quarters missing from
companyfacts are added; the prior-year comparatives a filing also carries are left alone.
