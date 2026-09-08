# SEC dataset build — 2026-09-08T19:18:41Z

- filers scanned: 20335
- companies published: 7412
- tickers in map: 10415

## Coverage by line item (companies with at least one value)

- acquisition_cost_amort: 157
- acquisitions: 3777
- buybacks: 4114
- capex: 6137
- cash: 7328
- claims_incurred: 163
- credit_loss_provision: 1110
- current_assets: 6120
- current_liabilities: 6104
- d_and_a: 6419
- debt_current: 3423
- debt_due_1y: 3313
- debt_due_2y: 3304
- debt_due_3y: 3203
- deposits: 1032
- dividends_paid: 2912
- eps_diluted: 6690
- goodwill: 4122
- gross_profit: 3700
- impairments: 4996
- income_tax: 6522
- intangibles: 3776
- interest_expense: 6001
- interest_income: 1190
- inventory: 3568
- loan_loss_allowance: 965
- loans: 1239
- loss_reserves: 203
- lt_debt_noncurrent: 3157
- net_income: 7412
- net_interest_income: 2161
- operating_cash_flow: 7384
- operating_income: 6233
- operating_leases: 5800
- pension_funded_status: 499
- premiums_earned: 170
- pretax_income: 6344
- rd_expense: 3342
- receivables: 4949
- revenue: 6563
- sga_expense: 2660
- shares_diluted: 6962
- shares_outstanding: 6855
- stock_comp: 6181
- tier1_capital_ratio: 290
- total_assets: 7402
- total_debt: 5653
- total_equity: 7269
- total_liabilities: 6824

## Self-check: four quarters sum to the fiscal year (revenue, net income, operating cash flow, capex)

- ok: 6633
- off (one or more items miss by >3%): 34
- n/a (no fiscal year with four quarters on file): 745

Readers treat an `off` company, or one whose latest quarter is more than 150 days old (a 10-K may lawfully take 90 days; anything older means the structured feed is behind the filing), as unmeasured on its quarterly metrics.

## Share counts (added 8 Sep 2026)

- diluted count on file: 6885
- basic count only: 77
- cover-page count only: 323
- none (multi-class filers tag by class; companyfacts drops dimensioned facts): 127

A reader does not drop a name on a per-share test it cannot run; `shares` in the manifest says which case applies.

## Items added 8 Sep 2026

`current_assets`, `current_liabilities` (current ratio); `operating_leases` (beside `total_debt`; the gate treatment is a rule decision); `receivables`, `inventory`, `total_liabilities` (working-capital quality); `acquisitions`, `goodwill`, `intangibles`, `impairments`; `rd_expense`, `sga_expense`; `pension_funded_status`; `debt_due_1y/2y/3y`; bank items `net_interest_income`, `interest_income`, `deposits`, `loans`, `credit_loss_provision`, `loan_loss_allowance`, `tier1_capital_ratio` (thin — tagged by regulatory entity, which companyfacts drops); insurer items `premiums_earned`, `claims_incurred`, `acquisition_cost_amort`, `loss_reserves`. Segment revenue and per-class share data are dimensioned facts and cannot come from this file; the business briefs carry segments in words. Coverage per item is listed above — an item with low coverage is a tag most filers do not use, not a bug.
