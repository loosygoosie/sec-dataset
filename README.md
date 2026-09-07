# S&P 500 fundamentals from the SEC — self-built dataset

A small pipeline that rebuilds a clean fundamentals dataset for the S&P 500 straight from
the SEC's own XBRL data, on a schedule, with no data vendor in between. GitHub Actions
downloads the SEC's bulk `companyfacts` file, keeps the ~20 line items the investing
system uses, and commits the result to `data/`. Anything that can fetch a file from
GitHub can then read it.

## One-time setup (about five minutes)

1. Create a new **public** repository (public keeps the scheduled runner free and lets the
   data be fetched without a token; the content is public filings, reorganised).
2. Add these three files, keeping the paths exactly:
   - `build_sec_dataset.py`
   - `.github/workflows/sec.yml`
   - `README.md` (this file)
3. Tell the SEC who is calling — they require it. In the repo:
   **Settings → Secrets and variables → Actions → Secrets → New repository secret** (a secret, so it is masked in the public run logs)
   - Name: `SEC_USER_AGENT`
   - Value: `Your Name your@email.com` (any real contact; it is sent only to sec.gov)
4. Go to the **Actions** tab. If GitHub asks you to enable workflows, enable them.
5. Open the workflow "Build S&P 500 SEC dataset" and press **Run workflow** once.
   The first run takes 3–8 minutes (the bulk file is about 1.2 GB). When it finishes,
   `data/` contains:
   - `sec_facts.json` — the dataset (a few MB): every company, 8 fiscal years annual,
     12 quarters, with the tags used and a coverage count
   - `sec_facts_annual.csv`, `sec_facts_quarterly.csv` — the same as flat tables
   - `REPORT.md` — counts, unresolved tickers, coverage by line item

After that it re-runs itself every Sunday. You never need to touch it.

## Reading the data from elsewhere

Raw file URL (replace `USER` and `REPO`):

```
https://raw.githubusercontent.com/USER/REPO/main/data/sec_facts.json
```

Shape:

```json
{
  "generated_utc": "2026-09-14T06:04:11Z",
  "counts": {"constituents": 503, "resolved": 503, "with_facts": 503},
  "coverage_by_item": {"revenue": 503, "operating_cash_flow": 503, "...": 0},
  "companies": {
    "DECK": {
      "cik": 910521, "name": "DECKERS OUTDOOR CORP", "sector": "Consumer Discretionary",
      "annual":    [{"fiscal_year": 2026, "period_end": "2026-03-31", "filed": "2026-05-22",
                     "revenue": 5.2e9, "operating_income": 1.2e9, "net_income": 9.7e8,
                     "operating_cash_flow": 1.1e9, "capex": 6.0e7, "stock_comp": 5.0e7, "...": "..."}],
      "quarterly": [{"period_end": "2026-06-30", "form": "10-Q", "filed": "2026-07-30", "revenue": 9.6e8, "...": "..."}],
      "tags_used": {"revenue": "RevenueFromContractWithCustomerExcludingAssessedTax", "...": "..."}
    }
  }
}
```

## What the numbers are, and are not

- Every value is the company's own tagged figure from its 10-K or 10-Q, as filed with the
  SEC. Where a period was reported more than once (restated comparatives), the most
  recently filed value wins.
- Quarterly rows are true three-month values. Q4 is not tagged by most companies; it is
  derived as the fiscal-year total minus the nine-month year-to-date (or minus Q1–Q3).
  The `form` field says when that happened.
- Fiscal years are labelled by the calendar year the period ends in. Deckers' year ending
  31 March 2026 is `2026`; Costco's ending 31 August 2025 is `2025`.
- Line items are resolved through a short list of tag synonyms (see `CONCEPTS` in the
  script and `tags_used` per company). A company using an unusual custom tag will show a
  gap for that item — `coverage_by_item` in the report makes those visible, and the
  synonym list is the place to fix them.
- Free cash flow is not stored; compute it as `operating_cash_flow − capex`. Net debt is
  `total_debt − cash` (fall back to `lt_debt_noncurrent + debt_current` when `total_debt`
  is empty). EBITDA is `operating_income + d_and_a`.
- Definitions to know: for banks and card issuers `revenue` is the net-of-interest-expense
  figure the company headlines (American Express ≈ $41bn, not the ~$80bn gross that some vendors
  show); `net_income` is net income attributable to the parent (before preferred dividends of
  subsidiaries, so a utility's figure can sit ~3% above the per-share-reconciling number); `d_and_a`
  is the cash-flow-statement figure (includes accretion and regulatory amortisation for
  utilities), which is the right add-back for cash-flow work; `capex` follows the tag list in
  the script (PP&E purchases, then utilities' construction expenditures, then REIT development).
- The SEC's structured data can trail a filing by weeks: on 7 Sep 2026 about 60 of 503
  companies' June-quarter 10-Qs were on EDGAR but not yet in the XBRL feed. Quarterly rows
  therefore lag press releases; annual rows are complete.
- No prices, no market caps, no estimates, no analyst data. Membership comes from the
  iShares IVV holdings file (falls back to Wikipedia's list if that is unavailable).

## Sources

- SEC bulk facts: https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip
- SEC ticker→CIK map: https://www.sec.gov/files/company_tickers.json
- Index membership: iShares Core S&P 500 ETF (IVV) daily holdings CSV
