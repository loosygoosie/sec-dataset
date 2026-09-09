#!/usr/bin/env python3
"""
build_sec_dataset.py — fundamentals for EVERY SEC filer, straight from the SEC, no data vendor.

What it does, once per run:
  1. Fetches the SEC's own ticker -> CIK maps (regenerated daily from filing cover pages).
  2. Downloads the SEC's bulk XBRL "companyfacts" zip (every filer, every tagged number).
  3. Normalises the 49 line items for every operating company in it — resolving the tag
     synonyms companies use for the same line — into clean annual (last 8 fiscal years)
     and quarterly (last 12 quarters, year-to-date cash flows differenced) rows.
  4. Writes one small file per company, data/companies/<CIK>.json (a file changes only when
     the company files something new, so weekly commits stay small), plus data/manifest.json
     (every CIK with name, tickers, latest filing date), data/tickers.json (the SEC map) and
     data/REPORT.md. Who is in the S&P 500, and what is held, is decided by the reader.

Run by GitHub Actions on a schedule (see .github/workflows/sec.yml).
Needs only `requests`. The SEC asks for a descriptive User-Agent with a
contact — set the SEC_USER_AGENT environment variable (see README).
"""
from __future__ import annotations

import csv
import io
import math
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
USER_AGENT = os.environ.get("SEC_USER_AGENT", "sp500-sec-dataset research (set SEC_USER_AGENT)")
HEADERS = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}

COMPANYFACTS_ZIP = "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"
TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
SP500_CSV_URL = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
# The constituent list is the one thing here that is not an SEC file. SEC_USER_AGENT carries a
# real name and email and is sent to sec.gov and nowhere else, so this request uses its own
# plain User-Agent rather than the HEADERS above.
SP500_HEADERS = {"User-Agent": "sec-dataset build (+https://github.com/loosygoosie/sec-dataset)"}
SP500_MIN = 400         # a list shorter than this is a broken fetch, not a smaller index
CIK_OVERRIDES_PATH = Path("data/cik_overrides.json")   # hand-maintained; the build reads it, never writes it
FILING_INDEX = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{acc}-index.html"
EVENTS_DIR = Path("data/events")    # written by build_sec_events.py; read here to spot a filing the bulk file has not caught up with
STALE_DAYS = 150                    # the tolerance REPORT.md tells readers to apply
PATCH_CAP = 100                     # filings fetched per build
PATCH_PER_COMPANY = 3               # a company missing several quarters needs them filled in order
XBRLI = "http://www.xbrl.org/2003/instance"
XSI_NIL = "{http://www.w3.org/2001/XMLSchema-instance}nil"
ANNUAL_YEARS = 8        # fiscal years of annual history to keep
QUARTERS = 12           # quarters of quarterly history to keep

OUT_DIR = Path("data")
WORK_DIR = Path("work")

# Line items we keep, with the GAAP tags companies use for them, in order of
# preference. "flow" items are period totals (income/cash-flow statements);
# "instant" items are balances at a date (balance sheet / share counts).
CONCEPTS: dict[str, dict] = {
    "revenue": {"kind": "flow", "pick": "dominant", "tags": [   # ranked, but a lower-ranked tag ≥3× larger wins (a REIT's contract revenue is a component beside its lease income)
        "RevenuesNetOfInterestExpense",                      # banks / card issuers / brokers: the total they headline (only financials tag it)
        "Revenues",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerExcludingAssessedTax",   # for a financial this is a component (AmEx: $41bn of $66bn)
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "TotalRevenuesAndOtherIncome",
        "OperatingLeaseLeaseIncome",                         # REITs
        "RealEstateRevenueNet",
        "InterestAndDividendIncomeOperating",                # banks that tag no total
        "NoninterestIncome",
    ]},
    "gross_profit": {"kind": "flow", "tags": ["GrossProfit"]},
    "operating_income": {"kind": "flow", "tags": ["OperatingIncomeLoss"]},
    "pretax_income": {"kind": "flow", "tags": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesForeign",
        "IncomeLossAttributableToParentBeforeTax",
    ]},
    "income_tax": {"kind": "flow", "tags": ["IncomeTaxExpenseBenefit"]},
    "net_income": {"kind": "flow", "tags": [
        "NetIncomeLoss",
        "ProfitLoss",
        "NetIncomeLossAvailableToCommonStockholdersBasic",
    ]},
    "eps_diluted": {"kind": "flow", "tags": ["EarningsPerShareDiluted"], "unit": "USD/shares"},
    "operating_cash_flow": {"kind": "flow", "tags": [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ]},
    "capex": {"kind": "flow", "pick": "max", "tags": [   # utilities/REITs tag a small PP&E line AND the big construction line: take the larger
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
        "PaymentsForConstructionInProcess",                 # regulated utilities (AEP, DUK: "construction expenditures")
        "PaymentsToAcquireAndDevelopRealEstate",            # REITs
        "PaymentsToDevelopRealEstateAssets",
        "PaymentsToAcquireRealEstate",
        "PaymentsForCapitalImprovements",
        "PaymentsToAcquireOtherPropertyPlantAndEquipment",
    ]},
    "stock_comp": {"kind": "flow", "tags": [
        "ShareBasedCompensation",
        "AllocatedShareBasedCompensationExpense",
        "StockOptionPlanExpense",
    ]},
    "d_and_a": {"kind": "flow", "tags": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "DepreciationAmortizationAndAccretionNet",
        "Depreciation",
    ]},
    "interest_expense": {"kind": "flow", "tags": [
        "InterestExpense",
        "InterestExpenseDebt",
        "InterestExpenseNonoperating",
        "InterestAndDebtExpense",
    ]},
    "dividends_paid": {"kind": "flow", "tags": [
        "PaymentsOfDividendsCommonStock",
        "PaymentsOfDividends",
    ]},
    "buybacks": {"kind": "flow", "tags": ["PaymentsForRepurchaseOfCommonStock"]},
    "cash": {"kind": "instant", "tags": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ]},
    "total_debt": {"kind": "instant", "pick": "max", "tags": [   # Marriott tags a $23m LongTermDebt beside $14bn of DebtAndCapitalLeaseObligations: take the larger
        "LongTermDebt",                                     # usually total incl. current portion
        "DebtAndCapitalLeaseObligations",
        "LongTermDebtAndCapitalLeaseObligations",
        "DebtInstrumentCarryingAmount",
        "LongTermDebtAndFinanceLeases",
        "DebtLongtermAndShorttermCombinedAmount",
        "UnsecuredDebt",                                    # REITs tag their borrowings by kind, rarely a total:
        "SecuredDebt",                                      #   the largest kind is a floor on total debt, far better
        "NotesPayable",                                     #   than reading "no debt" (Realty Income, Extra Space, Digital Realty)
        "LongTermNotesPayable",
        "SeniorNotes",
        "MortgageLoansOnRealEstate",
        "OtherLongTermDebt",
        "LineOfCredit",
    ]},
    "lt_debt_noncurrent": {"kind": "instant", "tags": [
        "LongTermDebtNoncurrent",
        "LongTermDebtAndCapitalLeaseObligationsNoncurrent",
        "LongTermDebtAndFinanceLeasesNoncurrent",
    ]},
    "debt_current": {"kind": "instant", "tags": [
        "LongTermDebtCurrent",
        "DebtCurrent",
        "LongTermDebtAndCapitalLeaseObligationsCurrent",
        "LongTermDebtAndFinanceLeasesCurrent",
    ]},
    "total_assets": {"kind": "instant", "tags": ["Assets"]},
    "total_equity": {"kind": "instant", "tags": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ]},
    # A weighted-average share count has a period like a flow, but it is an AVERAGE over that
    # period, not a total accumulated across it: four quarters do not sum to the year. Differencing
    # it out of a year-to-date figure produced roughly minus twice the real count (Apple's FY2025
    # quarter read -30,150,480,000 against a true ~14.8bn), so it is taken as filed instead.
    "shares_diluted": {"kind": "flow", "additive": False, "tags": [
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        "WeightedAverageNumberOfShareOutstandingBasicAndDiluted",
        "WeightedAverageNumberOfSharesOutstandingBasic",       # basic as a floor when no diluted count is tagged
    ], "unit": "shares"},
    "shares_outstanding": {"kind": "instant", "tags": ["dei:EntityCommonStockSharesOutstanding", "CommonStockSharesOutstanding"], "unit": "shares"},
    # --- added 8 Sep 2026 (research-gap review): three balance-sheet items the screen was missing ---
    "current_assets": {"kind": "instant", "tags": ["AssetsCurrent"]},            # -> current ratio (Piotroski's 9th signal, Altman's working-capital term)
    "current_liabilities": {"kind": "instant", "tags": ["LiabilitiesCurrent"]},
    "operating_leases": {"kind": "instant", "pick": "max", "tags": [            # debt in all but name for retailers, restaurants, airlines;
        "OperatingLeaseLiability",                                               #   the total where tagged, else the non-current part as a floor
        "OperatingLeaseLiabilityNoncurrent",
    ]},
    # --- added 8 Sep 2026, afternoon (Andrew: "the absolute complete picture") ---
    # working-capital quality: receivables and inventory outrunning sales is the earliest warning the statements give
    "receivables": {"kind": "instant", "tags": ["AccountsReceivableNetCurrent", "ReceivablesNetCurrent"]},
    "inventory": {"kind": "instant", "tags": ["InventoryNet"]},
    "total_liabilities": {"kind": "instant", "tags": ["Liabilities"]},
    # acquisitions and what they leave behind
    "acquisitions": {"kind": "flow", "tags": ["PaymentsToAcquireBusinessesNetOfCashAcquired", "PaymentsToAcquireBusinessesGross"]},
    "goodwill": {"kind": "instant", "tags": ["Goodwill"]},
    "intangibles": {"kind": "instant", "tags": ["IntangibleAssetsNetExcludingGoodwill"]},
    "impairments": {"kind": "flow", "pick": "max", "tags": ["GoodwillImpairmentLoss", "AssetImpairmentCharges", "ImpairmentOfLongLivedAssetsHeldForUse"]},
    # operating expense lines the pillars were taking from FMP
    "rd_expense": {"kind": "flow", "tags": ["ResearchAndDevelopmentExpense", "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost"]},
    "sga_expense": {"kind": "flow", "tags": ["SellingGeneralAndAdministrativeExpense"]},
    # pension underfunding (negative = underfunded) and the debt wall
    "pension_funded_status": {"kind": "instant", "tags": ["DefinedBenefitPlanFundedStatusOfPlan"]},
    "debt_due_1y": {"kind": "instant", "tags": ["LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths"]},
    "debt_due_2y": {"kind": "instant", "tags": ["LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo"]},
    "debt_due_3y": {"kind": "instant", "tags": ["LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree"]},
    # banks: the yardsticks Financial Services should be judged on (the November quarterly tests these definitions)
    "net_interest_income": {"kind": "flow", "tags": ["InterestIncomeExpenseNet"]},
    "interest_income": {"kind": "flow", "tags": ["InterestAndDividendIncomeOperating", "InterestIncomeOperating"]},
    "deposits": {"kind": "instant", "tags": ["Deposits"]},
    "loans": {"kind": "instant", "tags": ["LoansAndLeasesReceivableNetReportedAmount", "NotesReceivableNet", "FinancingReceivableExcludingAccruedInterestAfterAllowanceForCreditLoss"]},
    "credit_loss_provision": {"kind": "flow", "tags": ["ProvisionForLoanLeaseAndOtherLosses", "ProvisionForLoanLossesExpensed", "ProvisionForCreditLossesFinancingReceivables"]},
    "loan_loss_allowance": {"kind": "instant", "tags": ["FinancingReceivableAllowanceForCreditLosses", "AllowanceForLoanAndLeaseLosses"]},
    "tier1_capital_ratio": {"kind": "instant", "tags": ["TierOneRiskBasedCapitalToRiskWeightedAssets"], "unit": "pure"},   # most banks tag this by regulatory entity/framework, which companyfacts drops: expect thin coverage
    # insurers: combined-ratio components
    "premiums_earned": {"kind": "flow", "tags": ["PremiumsEarnedNet"]},
    "claims_incurred": {"kind": "flow", "tags": ["PolicyholderBenefitsAndClaimsIncurredNet", "IncurredClaimsPropertyCasualtyAndLiability"]},
    "acquisition_cost_amort": {"kind": "flow", "tags": ["DeferredPolicyAcquisitionCostAmortizationExpense"]},
    "loss_reserves": {"kind": "instant", "tags": ["LiabilityForClaimsAndClaimsAdjustmentExpense"]},
}

# --------------------------------------------------------------------------
# HTTP helpers
# --------------------------------------------------------------------------
_last_get = [0.0]


def get(url: str, retries: int = 4, stream: bool = False, timeout: int = 120) -> requests.Response:
    last = None
    for i in range(retries):
        try:
            gap = time.time() - _last_get[0]
            if gap < 0.12:                        # ~8 requests/second, under the SEC's 10/s
                time.sleep(0.12 - gap)
            r = requests.get(url, headers=HEADERS, timeout=timeout, stream=stream)
            _last_get[0] = time.time()
            if r.status_code == 200:
                return r
            last = f"HTTP {r.status_code}"
        except requests.RequestException as e:  # network hiccup
            last = str(e)
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"GET {url} failed: {last}")


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  using cached {dest} ({dest.stat().st_size/1e6:.0f} MB)")
        return dest
    print(f"  downloading {url}")
    r = get(url, stream=True, timeout=600)
    tmp = dest.with_suffix(dest.suffix + ".part")
    n = 0
    with open(tmp, "wb") as f:
        for chunk in r.iter_content(chunk_size=1 << 20):
            f.write(chunk); n += len(chunk)
            if n % (100 << 20) < (1 << 20):
                print(f"    {n/1e6:.0f} MB", flush=True)
    tmp.rename(dest)
    print(f"  saved {dest} ({n/1e6:.0f} MB)")
    return dest


# --------------------------------------------------------------------------
# Step 1 — S&P 500 membership
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
def _days(a: str, b: str) -> int:
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def _years_ago(d: date, years: int) -> date:
    """The same calendar day `years` back. 29 February has no counterpart in a non-leap
    year — and the year three back from a leap year never is one — so it lands on 28 Feb
    rather than raising ValueError and killing the build on that one day."""
    try:
        return d.replace(year=d.year - years)
    except ValueError:
        return d.replace(year=d.year - years, day=28)


def _pick_latest(cands: list[dict], pick: str = "rank") -> dict | None:
    """Same period from several tags/filings.
    pick="rank": prefer the most-preferred tag, then a 10-K over a 10-Q for a full-year period
    (a 10-Q occasionally carries a mis-dated full-year comparative), then the latest filing
    (restated comparatives win over the original).
    pick="max": within each tag take the latest filing, then the largest value across tags —
    for capex, where a utility tags a token PP&E line next to its real construction spend."""
    if not cands:
        return None
    def _k(f):
        full_year = f.get("start") and _days(f["start"], f["end"]) >= 340
        form_pen = 1 if (full_year and not str(f.get("form", "")).startswith("10-K")) else 0
        return (f.get("_rank", 0), form_pen, -_filed_key(f))
    if pick in ("max", "dominant"):
        per_tag = {}
        for f in cands:
            r = f.get("_rank", 0)
            if r not in per_tag or _k(f) < _k(per_tag[r]):
                per_tag[r] = f
        if pick == "max":
            return max(per_tag.values(), key=lambda f: (f.get("val") or 0))
        best = per_tag[min(per_tag)]                       # the most-preferred tag that has a value...
        big = max(per_tag.values(), key=lambda f: abs(f.get("val") or 0))
        if abs(big.get("val") or 0) >= 3 * abs(best.get("val") or 0):   # ...unless it is plainly a component of a larger one
            return big
        return best
    return min(cands, key=_k)


def _filed_key(f: dict) -> int:
    return int((f.get("filed") or "0000-00-00").replace("-", "") or 0)


def extract_series(facts: dict, tags: list[str], unit_pref: str | None) -> tuple[list[dict], str | None]:
    """Return the facts of EVERY listed tag, each fact annotated with its tag's preference rank,
    so later steps can pick, per period, the value from the most-preferred tag that has one.
    (Companies switch tags over time — e.g. Revenues before 2018, RevenueFromContract… after —
    so 'first tag with any data' silently drops recent years.)"""
    us = facts.get("facts", {}).get("us-gaap", {})
    dei = facts.get("facts", {}).get("dei", {})
    out, used = [], []
    for rank, tag in enumerate(tags):
        src, key = (dei, tag[4:]) if tag.startswith("dei:") else (us, tag)
        node = src.get(key)
        if not node:
            continue
        units = node.get("units", {})
        unit = unit_pref if unit_pref in units else next((u for u in ("USD", "shares", "USD/shares") if u in units), None)
        if unit and units[unit]:
            used.append(tag)
            for f in units[unit]:
                g = dict(f); g["_rank"] = rank; out.append(g)
    return out, (",".join(used) if used else None)


def annual_rows(series: list[dict], kind: str, pick: str = "rank") -> dict[int, dict]:
    """fy -> fact, from 10-K filings. Flow items only — a balance-sheet or cover-page instant is
    attached to the annual row later, by matching the row's period end (a cover-page share count is
    dated the filing date, which would otherwise create a phantom fiscal year)."""
    if kind != "flow":
        return {}
    by_fy: dict[int, list[dict]] = defaultdict(list)
    for f in series:
        if f.get("form") not in ("10-K", "10-K/A", "20-F", "40-F") or f.get("fp") != "FY":
            continue
        if not f.get("start") or not (340 <= _days(f["start"], f["end"]) <= 380):
            continue
        by_fy[_fy_of_period(f, f.get("fy"))].append(f)
    return {fy: _pick_latest(v, pick) for fy, v in by_fy.items()}


def _fy_of_period(f: dict, filing_fy: int) -> int:
    """A 10-K for fy=2025 also restates 2024 and 2023; label each fact by the calendar year its
    period ENDS in (Deckers' year ending 2026-03-31 is 2026; Costco's ending 2025-08-31 is 2025)."""
    y, m, d = int(f["end"][:4]), int(f["end"][5:7]), int(f["end"][8:10])
    return y - 1 if (m == 1 and d <= 7) else y          # Snap-on's year ending 3 Jan 2026 is fiscal 2025


def _dur(f: dict) -> int | None:
    return _days(f["start"], f["end"]) if f.get("start") else None


def quarterly_rows(series: list[dict], kind: str, pick: str = "rank", additive: bool = True) -> dict[str, dict]:
    """period_end -> fact for the value of ONE quarter.

    Instant items: the balance at each 10-Q / 10-K date.
    Flow items: income-statement lines are usually tagged per quarter, but cash-flow lines in a
    10-Q are year-to-date only (3, 6, 9 months). So, per fiscal year, take the cumulative facts
    that start at the fiscal-year start and difference them:
        Q1 = 3M · Q2 = 6M − 3M · Q3 = 9M − 6M · Q4 = FY − 9M
    A genuine 3-month fact for a period, when the company tagged one, wins over the derivation.

    `additive` is False for an item that carries a period but is not accumulated over it — a
    weighted-average share count is the average of the year, not the sum of its quarters. For
    those, the cumulative figure is taken as the filing reports it rather than differenced.
    """
    by_end: dict[str, list[dict]] = defaultdict(list)
    if kind == "instant":
        for f in series:
            if f.get("form") in ("10-Q", "10-Q/A", "10-K", "10-K/A"):
                by_end[f["end"]].append(f)
        return {end: _pick_latest(v, pick) for end, v in by_end.items()}

    # 1. genuine ~3-month facts
    for f in series:
        if f.get("form") in ("10-Q", "10-Q/A", "10-K", "10-K/A") and f.get("start") and 80 <= _dur(f) <= 100:
            by_end[f["end"]].append(f)
    out = {end: _pick_latest(v, pick) for end, v in by_end.items()}

    # 2. cumulative (year-to-date) facts grouped by their start date = fiscal-year start
    cum: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))   # start -> end -> facts
    for f in series:
        if f.get("form") in ("10-Q", "10-Q/A", "10-K", "10-K/A") and f.get("start"):
            d = _dur(f)
            if d is not None and 80 <= d <= 380:
                cum[f["start"]][f["end"]].append(f)
    for fy_start, ends in cum.items():
        pts = sorted(((e, _pick_latest(v, pick)) for e, v in ends.items()), key=lambda ev: ev[0])
        # keep one fact per ~quarter bucket (3M, 6M, 9M, 12M) — the longest-duration first
        for e, f in pts:
            d = _dur(f)
            if d < 80 or (e in out and out[e].get("_derived") is None):
                continue                          # a genuine 3-month fact exists
            if d <= 100 or not additive:
                # d <= 100: the first quarter of the year, where year-to-date IS the quarter.
                # not additive: an average, which cannot be differenced — take it as filed.
                q = f["val"]
            else:
                # subtract the quarters already known for this fiscal year (genuine or derived);
                # require exactly the expected number so a missing quarter never silently inflates one
                prior = [out[x]["val"] for x in out if fy_start < x < e]
                if len(prior) != round(d / 91) - 1:
                    continue
                q = f["val"] - sum(prior)
            g = dict(f); g["val"] = q
            if additive:
                g["_derived"] = f"{d}d YTD − prior"    # a value taken as filed is not a derivation
            out[e] = g
    return out


def normalise_company(facts: dict) -> dict:
    out_annual: dict[int, dict] = defaultdict(dict)
    out_q: dict[str, dict] = defaultdict(dict)
    tags_used: dict[str, str | None] = {}
    fy_end_dates: dict[int, str] = {}

    for name, spec in CONCEPTS.items():
        series, tag = extract_series(facts, spec["tags"], spec.get("unit"))
        tags_used[name] = tag
        if not series:
            continue
        kind = spec["kind"]

        # annual
        pick = spec.get("pick", "rank")
        ann = annual_rows(series, kind, pick)
        for fy, f in ann.items():
            out_annual[fy][name] = f["val"]
            if name == "revenue" or name == "net_income":
                fy_end_dates.setdefault(fy, f["end"])
            out_annual[fy].setdefault("_end", f["end"])
            out_annual[fy].setdefault("_filed", f.get("filed"))

        # quarterly (true 3-month values)
        q = quarterly_rows(series, kind, pick, spec.get("additive", True))
        for end, f in q.items():
            out_q[end][name] = f["val"]
            out_q[end].setdefault("_form", f.get("form") + (" (derived from YTD)" if f.get("_derived") else ""))
            out_q[end].setdefault("_filed", f.get("filed"))

    # instant items at FY end also belong to the FY row (balance sheet at year end)
    for fy, row in out_annual.items():
        end = row.get("_end")
        if end and end in out_q:
            for k, v in out_q[end].items():
                if not k.startswith("_") and CONCEPTS.get(k, {}).get("kind") == "instant":
                    row.setdefault(k, v)
    # drop quarterly rows that carry only instant items on a non-statement date (cover-page share
    # counts dated the filing date) — a real quarter-end row always has at least one flow item
    flow_names = {n for n, sp in CONCEPTS.items() if sp["kind"] == "flow"}
    out_q = {end: row for end, row in out_q.items() if any(k in flow_names for k in row)}

    annual = [dict(fiscal_year=fy, period_end=row.pop("_end", None), filed=row.pop("_filed", None), **row)
              for fy, row in sorted(out_annual.items())][-ANNUAL_YEARS:]
    quarterly = [dict(period_end=end, form=row.pop("_form", None), filed=row.pop("_filed", None), **row)
                 for end, row in sorted(out_q.items())][-QUARTERS:]
    return {"annual": annual, "quarterly": quarterly, "tags_used": tags_used}


CHECK_ITEMS = ("revenue", "net_income", "operating_cash_flow", "capex")
SHARE_ITEMS = ("shares_diluted", "shares_outstanding")
RECON_TOL = 0.03         # four quarters must sum to the fiscal year within 3% (or $5m on small lines)



# The largest stock split in this dataset is Amazon's 20:1, so a diluted count fifty times its own
# outstanding count is not a split — it is a scale error, and they are common enough to matter.
SCALE_RATIO = 50
# A step this large between adjacent quarters is a change of level. One of them is a stock split,
# which happens and stays. Two or more means the series comes back — some periods carry a restated
# or mis-scaled figure and the rest do not — and no per-share figure spans it.
STEP_RATIO = 3


def share_scale(ann: list[dict], qtr: list[dict]) -> str:
    """Whether a company's share counts are all on the same scale — "ok", "n/a", or "suspect:<why>".

    Filers get this wrong in two shapes, and the non-positive test that `shares` runs catches
    neither. Some tag the figure in millions against a `shares` unit, so the count is a million
    times too small — McDonald's files 716.4 for 716 million shares — or, where only some periods
    are wrong, far too large: Waters files 98,204,000,000 against 98m outstanding. Others mix
    split-adjusted and unadjusted figures in one series, so it sawtooths: Netflix alternates 437m
    and 4,392m across its 10:1 split, Booking runs two quarters near 33m then two near 800m, and
    KLA's fiscal-year rows are ten times its own interim quarters.

    "scale"  — a diluted count more than fifty times its own outstanding count, or less than a
               fiftieth. No split is that large.
    "levels" — the quarterly series steps between levels more than once. A split steps once and
               stays; anything that comes back is an inconsistency, and which side is right is not
               knowable from the numbers alone, so the whole series is suspect rather than some
               rows of it.

    A flagged company is not wrong about its business. It is unusable for anything per-share until
    a human looks, exactly as `shares: invalid` is. Never drop a name on it. It is a separate key
    because it measures something `shares` and `reconciles` do not, and because adding a key is
    safe where changing the meaning of one is not."""
    why, rows = [], ann + qtr
    if any(d and o and o > 0 and not (1 / SCALE_RATIO <= d / o <= SCALE_RATIO)
           for d, o in ((r.get("shares_diluted"), r.get("shares_outstanding")) for r in rows)):
        why.append("scale")
    # Adjacent ratios, not rounded magnitudes: a company sitting near a power of ten (Goldman at
    # ~3.1e8) would otherwise cross a rounding boundary on a 3% move and look broken.
    q = [r["shares_diluted"] for r in sorted(qtr, key=lambda r: r.get("period_end") or "")
         if r.get("period_end") and r.get("shares_diluted") and r["shares_diluted"] > 0]
    steps = sum(1 for a, b in zip(q, q[1:]) if b / a > STEP_RATIO or b / a < 1 / STEP_RATIO)
    if steps > 1:
        why.append("levels")
    if why:
        return "suspect:" + ",".join(why)
    return "ok" if any(r.get("shares_diluted") or r.get("shares_outstanding") for r in rows) else "n/a"


def data_checks(ann: list[dict], qtr: list[dict], tags_used: dict | None = None) -> dict:
    """Self-check written into every company file and the manifest, so a reader can refuse a row
    the pipeline itself cannot vouch for, instead of scoring a data gap as if it were the business.

    latest_quarter_end / quarter_age_days: how current the quarterly series is (the SEC's structured
        feed trails some filings by weeks; a reader treats a series older than its tolerance as unmeasured).
    reconciles: for the most recent fiscal year whose four quarters are all present, whether their sum
        matches the annual figure for each of CHECK_ITEMS — "ok", "off:<items>", or "n/a" when no fiscal
        year has four quarters on file. A miss means a tag, a YTD derivation or a restatement is wrong
        for that company, and its quarterly-based metrics should not be trusted until it is."""
    q_ends = [r["period_end"] for r in qtr if r.get("period_end")]
    latest_q = max(q_ends) if q_ends else None
    age = None
    if latest_q:
        y, m, d = (int(x) for x in latest_q.split("-"))
        age = (date.today() - date(y, m, d)).days
    result, checked_fy, off = "n/a", None, []
    q_by_end = {r["period_end"]: r for r in qtr if r.get("period_end")}
    for a in reversed(ann):
        end = a.get("period_end")
        if not end:
            continue
        # the four quarter-ends inside this fiscal year: the FY end and the three before it within 12 months
        y, m, d = (int(x) for x in end.split("-"))
        start = (date(y, m, d) - timedelta(days=330)).isoformat()   # after the prior FY end, before Q1's end
        ends = sorted(e for e in q_by_end if start < e <= end)
        if len(ends) != 4:
            continue
        checked_fy, off = a.get("fiscal_year"), []
        for item in CHECK_ITEMS:
            av = a.get(item)
            qs = [q_by_end[e].get(item) for e in ends]
            if av is None or any(v is None for v in qs):
                continue                                  # not on file for every quarter: nothing to compare
            diff = abs(sum(qs) - av)
            if diff > max(RECON_TOL * abs(av), 5e6):
                off.append(item)
        result = "ok" if not off else "off:" + ",".join(off)
        break
    # share count: some multi-class filers (Visa, Berkshire) tag every per-share and share-count fact by class of
    # stock, and the SEC's companyfacts file carries no dimensioned facts, so the count is simply absent. A reader
    # must not drop such a name on a test it cannot run (revenue per share); it flags it instead.
    #
    # This is measured on the VALUES, not on which tag resolved. Until 9 Sep 2026 it read the tag map, so a
    # company whose diluted tag matched but whose rows were all empty reported "ok" — ERIE, BKR, HSY and LYB
    # in the S&P 500, 76 companies dataset-wide, every one of them promising a per-share figure it could not
    # supply. The vocabulary is unchanged; the values are now true.
    rows = ann + qtr
    has_dil = any(r.get("shares_diluted") is not None for r in rows)
    has_out = any(r.get("shares_outstanding") is not None for r in rows)
    st = (tags_used or {}).get("shares_diluted")
    if has_dil:
        shares = "ok" if (st and "Diluted" in st) else "basic-only"
    elif has_out:
        shares = "outstanding-only"
    else:
        shares = "none"
    # A share count of zero or less is never a real one — it is a pipeline artefact or a filer
    # tagging nothing. Either way no per-share figure can be computed from it, so the flag says
    # so rather than reporting "ok" over the top of it, which is how a whole index of negative
    # counts went unnoticed.
    bad = sorted({item for rows in (ann, qtr) for r in rows for item in SHARE_ITEMS
                  if r.get(item) is not None and r[item] <= 0})
    if bad:
        shares = "invalid:" + ",".join(bad)
    return {"latest_quarter_end": latest_q, "quarter_age_days": age, "reconciles": result,
            "reconciled_fy": checked_fy, "shares": shares, "share_scale": share_scale(ann, qtr)}


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def parse_xbrl_instance(xml_text: str, form: str, filed: str) -> dict:
    """One filing's XBRL instance, reshaped into the companyfacts layout the normaliser reads.

    The SEC's bulk companyfacts file trails some filers by months. The filing itself carries the
    same facts on the day it lands, so for a company that has fallen behind we read its instance
    document and feed it through the very same tag map, picking rules and YTD differencing.

    Only consolidated facts survive: a context carrying a <segment> is a breakdown by business
    segment or class of stock, and companyfacts drops dimensioned facts too, so keeping them
    would put a segment's revenue where the company's total belongs. Namespaces are matched by
    URI, not by prefix, because filers choose their own prefixes."""
    root = ET.fromstring(xml_text)

    ctx: dict[str, dict] = {}
    for c in root.findall(f"{{{XBRLI}}}context"):
        if c.find(f".//{{{XBRLI}}}segment") is not None:
            continue
        per = c.find(f"{{{XBRLI}}}period")
        if per is None:
            continue
        inst = per.find(f"{{{XBRLI}}}instant")
        if inst is not None and inst.text:
            ctx[c.get("id")] = {"end": inst.text}
            continue
        sd, ed = per.find(f"{{{XBRLI}}}startDate"), per.find(f"{{{XBRLI}}}endDate")
        if sd is not None and ed is not None and sd.text and ed.text:
            ctx[c.get("id")] = {"start": sd.text, "end": ed.text}

    units: dict[str, str] = {}
    for u in root.findall(f"{{{XBRLI}}}unit"):
        m = u.find(f"{{{XBRLI}}}measure")
        if m is not None and m.text:
            units[u.get("id")] = m.text.split(":")[-1]          # iso4217:USD -> USD
            continue
        num = u.find(f".//{{{XBRLI}}}unitNumerator/{{{XBRLI}}}measure")
        den = u.find(f".//{{{XBRLI}}}unitDenominator/{{{XBRLI}}}measure")
        if num is not None and den is not None and num.text and den.text:
            units[u.get("id")] = f"{num.text.split(':')[-1]}/{den.text.split(':')[-1]}"

    fp = "FY" if form.startswith("10-K") else "Q"
    out: dict[str, dict] = {"us-gaap": {}, "dei": {}}
    seen: set = set()
    for el in root.iter():
        if not el.tag.startswith("{"):
            continue
        uri, tag = el.tag[1:].split("}", 1)
        if "us-gaap" in uri:
            ns = "us-gaap"
        elif "/dei" in uri:
            ns = "dei"
        else:
            continue                                            # the filer's own extension tags mean nothing to CONCEPTS
        if el.get(XSI_NIL) == "true" or not (el.text or "").strip():
            continue
        c, unit = ctx.get(el.get("contextRef") or ""), units.get(el.get("unitRef") or "")
        if c is None or unit is None:
            continue
        try:
            val = float(el.text)
        except ValueError:
            continue
        if val.is_integer():
            val = int(val)
        key = (ns, tag, unit, c.get("start"), c["end"], val)
        if key in seen:
            continue                                            # one fact is tagged in several places in a document
        seen.add(key)
        f = {"end": c["end"], "val": val, "form": form, "filed": filed, "fp": fp, "fy": int(c["end"][:4])}
        if "start" in c:
            f["start"] = c["start"]
        out[ns].setdefault(tag, {"units": {}})["units"].setdefault(unit, []).append(f)
    return {"facts": out}


def merge_facts(base: dict, extra: dict) -> None:
    """Fold a filing's facts into a company's companyfacts record, in place. `base` is read fresh
    from the zip for this one company and thrown away after, so mutating it is safe. The
    normaliser's own rules then decide which value wins per period — the filing's facts carry a
    later `filed`, so where they restate something they take precedence, as a restatement should."""
    for ns, tags in extra.get("facts", {}).items():
        b = base.setdefault("facts", {}).setdefault(ns, {})
        for tag, node in tags.items():
            bu = b.setdefault(tag, {"units": {}}).setdefault("units", {})
            for unit, facts in node["units"].items():
                bu.setdefault(unit, []).extend(facts)


def filing_instance_url(cik: int, accession: str) -> str | None:
    """The filing's XBRL instance document, from its index page: the row EDGAR labels
    'EXTRACTED XBRL INSTANCE DOCUMENT'."""
    r = get(FILING_INDEX.format(cik=cik, acc_nodash=accession.replace("-", ""), acc=accession), retries=2, timeout=60)
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", r.text, re.S):
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]
        if len(cells) >= 4 and "INSTANCE" in cells[1].upper():
            m = re.search(r'href="([^"]+)"', row)
            if m:
                return "https://www.sec.gov" + m.group(1)
    return None


def patch_targets(manifest: dict, priority: set[int]) -> list[tuple[int, list[dict]]]:
    """Companies whose companyfacts quarterly series has fallen behind a filing the events feed
    already knows about: stale beyond STALE_DAYS, with a 10-Q or 10-K on file for a period later
    than the last quarter we hold. Filings come back oldest first, because deriving a quarter from
    a year-to-date figure needs the earlier quarters of that year to exist. S&P 500 constituents
    are served first, then the most stale, so a capped run spends its budget where it is read."""
    out: list[tuple[int, list[dict]]] = []
    for cik_s, v in manifest.items():
        age, lq = v.get("quarter_age_days"), v.get("latest_quarter_end")
        if age is None or age <= STALE_DAYS or not lq:
            continue
        p = EVENTS_DIR / f"{cik_s}.json"
        if not p.exists():
            continue
        try:
            evs = json.loads(p.read_text()).get("events", [])
        except Exception:  # noqa: BLE001
            continue
        newer = [e for e in evs if str(e.get("form", "")).startswith(("10-Q", "10-K"))
                 and e.get("period") and e["period"] > lq and e.get("accession")]
        if not newer:
            continue
        newer.sort(key=lambda e: e["period"])
        out.append((int(cik_s), newer[:PATCH_PER_COMPANY]))
    out.sort(key=lambda t: (t[0] not in priority, -(manifest[str(t[0])]["quarter_age_days"] or 0)))
    return out


def load_cik_overrides() -> dict[str, dict]:
    """Hand-maintained ticker -> CIK corrections, for when the SEC's map points a ticker at a
    freshly registered shell and leaves the operating company — with all the history — carrying
    no ticker. Returns {} when the file is absent, and skips (rather than dies on) a bad entry:
    a typo in a hand-edited file must not take a build down."""
    try:
        j = json.loads(CIK_OVERRIDES_PATH.read_text())
    except FileNotFoundError:
        return {}
    except Exception as e:  # noqa: BLE001
        print(f"  cik_overrides.json unreadable ({type(e).__name__}); ignoring it")
        return {}
    out: dict[str, dict] = {}
    for t, v in (j.get("overrides") or {}).items():
        cik = v.get("cik") if isinstance(v, dict) else v
        try:
            out[t.upper().replace(".", "-")] = {"cik": int(cik),
                                                "name": (v.get("name") if isinstance(v, dict) else None)}
        except (TypeError, ValueError):
            print(f"  cik_overrides.json: skipping {t!r}, its cik is not a number")
    return out


def _sp500_csv() -> str | None:
    """The constituents CSV, or None if it cannot be had. Never raises: a build must not
    fail because a list of index members was unreachable."""
    last = None
    for i in range(3):
        try:
            r = requests.get(SP500_CSV_URL, headers=SP500_HEADERS, timeout=60)
            if r.status_code == 200:
                return r.text
            last = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            last = type(e).__name__
        time.sleep(2 * (i + 1))
    print(f"  constituents fetch failed: {last}")
    return None


def sp500_snapshot(by_ticker: dict[str, dict], generated: str,
                   published: set[int] | None = None) -> tuple[dict | None, str]:
    """Who is in the index today, each ticker resolved to a CIK through the SEC's own ticker
    map. Membership is a fact about an index, not a fundamental — every number in the company
    files still comes from the filer's own filing.

    `published` is the set of CIKs this build actually wrote a company file for. A constituent
    can resolve to a CIK cleanly and still have no fundamentals behind it — a reorganisation
    moves a ticker to a new registrant, a spinoff has not filed yet — so those are named in
    `no_fundamentals` rather than left to fail silently when a reader joins on cik.

    Returns (record, note). The record is None when the list could not be fetched or came back
    implausibly short; main then leaves the previous data/sp500.json alone and REPORT.md says
    the snapshot is stale, because a reader acting on a silently empty index is worse off than
    one acting on last week's."""
    text = _sp500_csv()
    if text is None:
        return None, "the fetch failed"

    def cell(row: dict, *names: str) -> str:
        for n in names:
            for k, v in row.items():
                if k and k.strip().lower() == n:
                    return (v or "").strip()
        return ""

    companies, unmatched, seen = [], [], set()
    for row in csv.DictReader(io.StringIO(text)):
        raw = cell(row, "symbol", "ticker")
        if not raw:
            continue
        t = raw.upper().replace(".", "-")        # the SEC map's own spelling: BRK.B -> BRK-B
        if t in seen:
            continue
        seen.add(t)
        hit = by_ticker.get(t)
        if hit:
            companies.append({"ticker": t, "cik": hit["cik"],
                              "name": cell(row, "security", "name", "company") or hit["name"]})
        else:
            unmatched.append(t)                  # a fresh addition the SEC map has not caught up with

    total = len(companies) + len(unmatched)
    if total < SP500_MIN:
        print(f"  constituents list came back with only {total} tickers; keeping the previous file")
        return None, f"the list came back with only {total} tickers"
    no_fundamentals = sorted(c["ticker"] for c in companies
                             if published is not None and c["cik"] not in published)
    return {"generated_utc": generated, "date": generated[:10], "source": SP500_CSV_URL,
            "constituents": total, "matched": len(companies),
            "companies": sorted(companies, key=lambda c: c["ticker"]),
            "unmatched": sorted(unmatched), "no_fundamentals": no_fundamentals}, "ok"


def load_ticker_maps() -> tuple[dict[str, dict], dict[int, list[str]]]:
    """SEC's own ticker map (regenerated daily from filing cover pages): ticker -> {cik, name}, and cik -> [tickers].
    The exchange-listed variant is merged in when reachable — it carries a few tickers the plain map lacks."""
    by_ticker: dict[str, dict] = {}
    j = get(TICKER_MAP_URL).json()
    for v in (j.values() if isinstance(j, dict) else j):
        by_ticker[v["ticker"].upper().replace(".", "-")] = {"cik": int(v["cik_str"]), "name": v["title"]}
    try:
        jx = get(TICKER_MAP_URL.replace("company_tickers.json", "company_tickers_exchange.json")).json()
        cols = jx["fields"]; ci, ni, ti = cols.index("cik"), cols.index("name"), cols.index("ticker")
        for row in jx["data"]:
            if row[ti]:
                by_ticker.setdefault(row[ti].upper().replace(".", "-"), {"cik": int(row[ci]), "name": row[ni]})
    except Exception as e:  # noqa: BLE001
        print(f"  exchange map skipped: {e}")
    for t, ov in load_cik_overrides().items():
        was = by_ticker.get(t, {}).get("cik")
        if was == ov["cik"]:
            continue                                  # the SEC map has caught up; the entry is now a no-op
        by_ticker[t] = {"cik": ov["cik"], "name": ov["name"] or by_ticker.get(t, {}).get("name") or t}
        print(f"  override: {t} -> CIK {ov['cik']}" + (f" (SEC map says {was})" if was else ""))

    by_cik: dict[int, list[str]] = defaultdict(list)
    for t, v in sorted(by_ticker.items()):
        by_cik[v["cik"]].append(t)
    return by_ticker, dict(by_cik)


def main() -> int:
    """The everything-build: no index filter. Every operating filer in the SEC bulk file is normalised and
    published as its own file; who is in the S&P 500, and what is held, is decided by the reader."""
    t0 = time.time()
    OUT_DIR.mkdir(exist_ok=True); WORK_DIR.mkdir(exist_ok=True)
    comp_dir = OUT_DIR / "companies"; comp_dir.mkdir(exist_ok=True)

    print("1. SEC ticker maps")
    by_ticker, by_cik = load_ticker_maps()
    print(f"  {len(by_ticker)} tickers, {len(by_cik)} CIKs")

    print("2. companyfacts bulk zip")
    zpath = download(COMPANYFACTS_ZIP, WORK_DIR / "companyfacts.zip")

    print("3. normalise every filer")
    cutoff = _years_ago(date.today(), 3).isoformat()   # drop filers silent for 3+ years
    manifest, coverage, written, recon = {}, defaultdict(int), set(), defaultdict(int)
    n_seen = n_kept = 0
    with zipfile.ZipFile(zpath) as z:
        entries = sorted(n for n in z.namelist() if n.startswith("CIK") and n.endswith(".json"))
        for n in entries:
            n_seen += 1
            if n_seen % 2000 == 0:
                print(f"  {n_seen}/{len(entries)} scanned, {n_kept} kept", flush=True)
            try:
                with z.open(n) as fh:
                    facts = json.load(fh)
                if not isinstance(facts, dict) or not facts.get("facts", {}).get("us-gaap"):
                    continue                               # funds, trusts, foreign private issuers on IFRS
                norm = normalise_company(facts)
            except Exception as e:  # noqa: BLE001
                print(f"  skipped {n}: {type(e).__name__}: {e}")
                continue
            ann, qtr = norm["annual"], norm["quarterly"]
            if not ann or not any(r.get("revenue") is not None or r.get("net_income") is not None for r in ann):
                continue                                   # nothing an investor can read
            latest_filed = max([r.get("filed") or "" for r in ann + qtr] or [""])
            if latest_filed < cutoff:
                continue
            cik = int(facts.get("cik") or n[3:13])     # the CIK is in the file name; a few records omit the field
            checks = data_checks(ann, qtr, norm["tags_used"])
            rec = {"cik": cik, "sec_name": facts.get("entityName"), "tickers": by_cik.get(cik, []),
                   "annual": ann, "quarterly": qtr, "tags_used": norm["tags_used"], "checks": checks}
            path = comp_dir / f"{cik}.json"
            body = json.dumps(rec, separators=(",", ":"), sort_keys=True)
            if not path.exists() or path.read_text() != body:      # unchanged files stay untouched -> small commits
                path.write_text(body)
            written.add(path.name)
            manifest[str(cik)] = {"name": facts.get("entityName"), "tickers": rec["tickers"], "latest_filed": latest_filed,
                                  "fiscal_year_end": ann[-1].get("period_end"), "annual_rows": len(ann), "quarterly_rows": len(qtr),
                                  "latest_quarter_end": checks["latest_quarter_end"], "quarter_age_days": checks["quarter_age_days"],
                                  "reconciles": checks["reconciles"], "shares": checks["shares"],
                                  "share_scale": checks["share_scale"]}
            recon[checks["reconciles"].split(":")[0]] += 1
            recon["shares:" + checks["shares"].split(":")[0]] += 1
            recon["share_scale:" + checks["share_scale"].split(":")[0]] += 1
            for k, v in norm["tags_used"].items():
                if v: coverage[k] += 1
            n_kept += 1
    print(f"  {n_kept} companies kept of {n_seen} filers")
    if n_kept < 3000:
        raise SystemExit(f"REFUSING TO WRITE — only {n_kept} companies normalised; the bulk file or the parser is broken")

    # remove files for filers that dropped out, and the old single-file outputs
    for p in comp_dir.iterdir():
        if p.name not in written:
            p.unlink()
    for stale in ("sec_facts.json", "sec_facts_annual.csv", "sec_facts_quarterly.csv"):
        if (OUT_DIR / stale).exists():
            (OUT_DIR / stale).unlink()

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    print("4. S&P 500 constituents")
    sp500_path = OUT_DIR / "sp500.json"
    sp500, sp500_note = sp500_snapshot(by_ticker, generated, {int(k) for k in manifest})
    if sp500 is not None:
        sp500_path.write_text(json.dumps(sp500, separators=(",", ":"), sort_keys=True))
        print(f"  {sp500['matched']}/{sp500['constituents']} tickers resolved to a CIK")

    print("5. stale-name fallback")
    patched: list[int] = []
    targets = patch_targets(manifest, {c["cik"] for c in (sp500 or {}).get("companies", [])})
    print(f"  {len(targets)} companies are behind their own filings; budget {PATCH_CAP} filings")
    budget = PATCH_CAP
    with zipfile.ZipFile(zpath) as z:
        for cik, filings in targets:
            if budget <= 0:
                break
            path = comp_dir / f"{cik}.json"
            try:
                with z.open(f"CIK{cik:010d}.json") as fh:
                    facts = json.load(fh)
                rec = json.loads(path.read_text())
            except (KeyError, OSError, ValueError):
                continue
            before = {r["period_end"] for r in rec["quarterly"]}
            used = 0
            for e in filings:
                if budget <= 0:
                    break
                budget -= 1
                try:
                    url = filing_instance_url(cik, e["accession"])
                    if not url:
                        continue                      # a filing with no XBRL instance: nothing to read
                    merge_facts(facts, parse_xbrl_instance(get(url, retries=2, timeout=180).text,
                                                           e["form"], e.get("date") or ""))
                    used += 1
                except Exception as ex:  # noqa: BLE001
                    print(f"  {cik} {e['accession']}: {type(ex).__name__}: {ex}")
            if not used:
                continue
            try:
                norm = normalise_company(facts)
            except Exception as ex:  # noqa: BLE001
                print(f"  {cik}: re-normalise failed: {type(ex).__name__}")
                continue
            # Only genuinely new quarters are taken. The filing also carries prior-year
            # comparatives, and rewriting settled history from it is not what this is for.
            fresh = [r for r in norm["quarterly"] if r["period_end"] not in before]
            if not fresh:
                continue
            for r in fresh:
                r["source"] = "filing"                # absent on a row means it came from companyfacts
            rec["quarterly"] = sorted(rec["quarterly"] + fresh, key=lambda r: r["period_end"])[-QUARTERS:]
            # Every counter the checks feed has to move, not just reconciles: patching a company
            # with figures read from its filing can change its shares flag too, and REPORT.md's
            # shares tallies were counting the pre-patch value for all 71 patched companies.
            was = {k: rec["checks"][k].split(":")[0] for k in ("reconciles", "shares", "share_scale")}
            rec["checks"] = data_checks(rec["annual"], rec["quarterly"], rec["tags_used"])
            path.write_text(json.dumps(rec, separators=(",", ":"), sort_keys=True))
            recon[was["reconciles"]] -= 1
            recon[rec["checks"]["reconciles"].split(":")[0]] += 1
            for k in ("shares", "share_scale"):
                recon[f"{k}:{was[k]}"] -= 1
                recon[f"{k}:" + rec["checks"][k].split(":")[0]] += 1
            manifest[str(cik)].update(quarterly_rows=len(rec["quarterly"]),
                                      latest_quarter_end=rec["checks"]["latest_quarter_end"],
                                      quarter_age_days=rec["checks"]["quarter_age_days"],
                                      reconciles=rec["checks"]["reconciles"], shares=rec["checks"]["shares"],
                                      patched_from_filing=True)
            patched.append(cik)
    print(f"  patched {len(patched)} companies from their own filings ({PATCH_CAP - budget} filings fetched)")

    (OUT_DIR / "tickers.json").write_text(json.dumps(by_ticker, separators=(",", ":"), sort_keys=True))
    (OUT_DIR / "manifest.json").write_text(json.dumps({
        "generated_utc": generated, "sources": {"facts": COMPANYFACTS_ZIP, "cik_map": TICKER_MAP_URL},
        "concepts": {k: {"kind": v["kind"], "tags": v["tags"], "pick": v.get("pick", "rank")} for k, v in CONCEPTS.items()},
        "counts": {"filers_scanned": n_seen, "companies": n_kept, "tickers": len(by_ticker)},
        "coverage_by_item": dict(sorted(coverage.items())),
        "companies": manifest}, separators=(",", ":"), sort_keys=True))
    report = [f"# SEC dataset build — {generated}", "", f"- filers scanned: {n_seen}", f"- companies published: {n_kept}",
              f"- tickers in map: {len(by_ticker)}", "", "## Coverage by line item (companies with at least one value)", ""]
    report += [f"- {k}: {v}" for k, v in sorted(coverage.items())]
    report += ["", "## Self-check: four quarters sum to the fiscal year (revenue, net income, operating cash flow, capex)", "",
               f"- ok: {recon.get('ok', 0)}", f"- off (one or more items miss by >3%): {recon.get('off', 0)}",
               f"- n/a (no fiscal year with four quarters on file): {recon.get('n/a', 0)}", "",
               "Readers treat an `off` company, or one whose latest quarter is more than 150 days old (a 10-K may lawfully take 90 days; anything older means the structured feed is behind the filing), as unmeasured on its quarterly metrics.",
               "", "## Share counts (added 8 Sep 2026)", "",
               f"- diluted count on file: {recon.get('shares:ok', 0)}", f"- basic count only: {recon.get('shares:basic-only', 0)}",
               f"- cover-page count only: {recon.get('shares:outstanding-only', 0)}", f"- none (multi-class filers tag by class; companyfacts drops dimensioned facts): {recon.get('shares:none', 0)}",
               f"- **invalid (a share count of zero or less somewhere in the file): {recon.get('shares:invalid', 0)}**", "",
               "A reader does not drop a name on a per-share test it cannot run; `shares` in the manifest says which case applies.",
               "", "## Share scale (added 9 Sep 2026)", "",
               f"- consistent: {recon.get('share_scale:ok', 0)}",
               f"- **suspect: {sum(v for k, v in recon.items() if k.startswith('share_scale:suspect'))}** "
               f"(`scale` — a diluted count more than fifty times its own outstanding count, or less than a "
               f"fiftieth; `levels` — the quarterly series steps between levels more than once, so no per-share "
               f"figure spans it)",
               f"- no share data at all: {recon.get('share_scale:n/a', 0)}", "",
               "`share_scale` says whether a company's share counts can all be true at once. It is not a reason "
               "to drop a name — it says the per-share metrics for that company are unmeasured. Both the flag "
               "and `shares` are in the manifest, so a reader need not open 7,411 company files to screen on them.",
               "", "## Items added 8 Sep 2026", "",
               "`current_assets`, `current_liabilities` (current ratio); `operating_leases` (beside `total_debt`; the gate treatment is a rule decision); `receivables`, `inventory`, `total_liabilities` (working-capital quality); `acquisitions`, `goodwill`, `intangibles`, `impairments`; `rd_expense`, `sga_expense`; `pension_funded_status`; `debt_due_1y/2y/3y`; bank items `net_interest_income`, `interest_income`, `deposits`, `loans`, `credit_loss_provision`, `loan_loss_allowance`, `tier1_capital_ratio` (thin — tagged by regulatory entity, which companyfacts drops); insurer items `premiums_earned`, `claims_incurred`, `acquisition_cost_amort`, `loss_reserves`. Segment revenue and per-class share data are dimensioned facts and cannot come from this file; the business briefs carry segments in words. Coverage per item is listed above — an item with low coverage is a tag most filers do not use, not a bug."]
    report += ["", "## Stale-name fallback", "",
               f"- companies whose companyfacts quarterly series was behind their own filings: {len(targets)}",
               f"- of those, patched from the filing's own XBRL this run: {len(patched)} (cap {PATCH_CAP} filings)",
               "",
               "A quarterly row carrying `\"source\": \"filing\"` was derived from the filing's own XBRL instance,",
               "through the same tag map, picking rules and year-to-date differencing as every other row. A row",
               "with no `source` came from the SEC's bulk companyfacts file. Only quarters missing from",
               "companyfacts are added; the prior-year comparatives a filing also carries are left alone.",
               "", "## S&P 500 constituents", ""]
    if sp500 is not None:
        report += [f"- source: {SP500_CSV_URL}", f"- snapshot date: {sp500['date']}",
                   f"- constituents: {sp500['constituents']}",
                   f"- resolved to a CIK via the SEC ticker map: {sp500['matched']}",
                   f"- unmatched (no CIK in the SEC ticker map): {', '.join(sp500['unmatched']) if sp500['unmatched'] else 'none'}",
                   f"- resolved but with no company file, so nothing to join to: {', '.join(sp500['no_fundamentals']) if sp500['no_fundamentals'] else 'none'}"]
    elif sp500_path.exists():
        report += [f"- **NOT REFRESHED THIS RUN** — {sp500_note}; `data/sp500.json` is unchanged from the previous build.",
                   "- Membership is therefore as of the last successful fetch. Every fundamental in this build",
                   "  comes from the filings as usual and is unaffected; only the index list is stale."]
    else:
        report += [f"- **NOT WRITTEN** — {sp500_note}, and there is no earlier snapshot to fall back on,",
                   "  so `data/sp500.json` is absent from this build.",
                   "- A reader must treat the file as missing, not as an empty index. Every fundamental in this",
                   "  build comes from the filings as usual and is unaffected."]
    report += ["", "Membership comes from a public constituents list, not from the SEC — it is a fact about",
               "an index, not a company fundamental. `cik` is resolved through the SEC's own ticker map, so a",
               "ticker the map has not caught up with is listed under `unmatched` rather than guessed at."]

    (OUT_DIR / "REPORT.md").write_text("\n".join(report) + "\n")
    print(f"done in {time.time()-t0:.0f}s -> {n_kept} files in {comp_dir}/, manifest.json, tickers.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
