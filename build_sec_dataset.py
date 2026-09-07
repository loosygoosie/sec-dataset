#!/usr/bin/env python3
"""
build_sec_dataset.py — S&P 500 fundamentals straight from the SEC, no data vendor.

What it does, once per run:
  1. Pulls the current S&P 500 membership from the iShares IVV holdings file
     (the ETF that tracks the index publishes its holdings daily, free).
  2. Maps each ticker to its SEC registrant number (CIK) via the SEC's own
     company_tickers.json.
  3. Downloads the SEC's bulk XBRL "companyfacts" zip (every filer, every
     tagged number) and reads only the ~503 files we need out of it.
  4. Normalises ~18 line items per company — resolving the tag synonyms
     companies use for the same line — into clean annual (last 8 fiscal
     years) and quarterly (last 12 quarters, Q4 derived from the 10-K)
     rows, always taking the most recently filed value for a period.
  5. Writes data/sec_facts.json (and a flat data/sec_facts_annual.csv /
     data/sec_facts_quarterly.csv) plus a coverage report.

Run by GitHub Actions on a schedule (see .github/workflows/sec.yml).
Needs only `requests`. The SEC asks for a descriptive User-Agent with a
contact — set the SEC_USER_AGENT environment variable (see README).
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
import time
import zipfile
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import requests

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
USER_AGENT = os.environ.get("SEC_USER_AGENT", "sp500-sec-dataset research (set SEC_USER_AGENT)")
HEADERS = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}

COMPANYFACTS_ZIP = "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"
TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
IVV_HOLDINGS_URL = (
    "https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf/"
    "1467271812596.ajax?fileType=csv&fileName=IVV_holdings&dataType=fund"
)
WIKI_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"  # fallback only

ANNUAL_YEARS = 8        # fiscal years of annual history to keep
QUARTERS = 12           # quarters of quarterly history to keep

OUT_DIR = Path("data")
WORK_DIR = Path("work")

# Line items we keep, with the GAAP tags companies use for them, in order of
# preference. "flow" items are period totals (income/cash-flow statements);
# "instant" items are balances at a date (balance sheet / share counts).
CONCEPTS: dict[str, dict] = {
    "revenue": {"kind": "flow", "tags": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "RevenuesNetOfInterestExpense",                      # banks / brokers
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "TotalRevenuesAndOtherIncome",
    ]},
    "gross_profit": {"kind": "flow", "tags": ["GrossProfit"]},
    "operating_income": {"kind": "flow", "tags": ["OperatingIncomeLoss"]},
    "pretax_income": {"kind": "flow", "tags": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic",
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
    "capex": {"kind": "flow", "tags": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
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
    "total_debt": {"kind": "instant", "tags": [
        "LongTermDebt",                                     # usually total incl. current portion
        "DebtAndCapitalLeaseObligations",
        "LongTermDebtAndCapitalLeaseObligations",
        "DebtInstrumentCarryingAmount",
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
    "shares_diluted": {"kind": "flow", "tags": ["WeightedAverageNumberOfDilutedSharesOutstanding"], "unit": "shares"},
    "shares_outstanding": {"kind": "instant", "tags": ["dei:EntityCommonStockSharesOutstanding", "CommonStockSharesOutstanding"], "unit": "shares"},
}

# --------------------------------------------------------------------------
# HTTP helpers
# --------------------------------------------------------------------------
def get(url: str, retries: int = 4, stream: bool = False, timeout: int = 120) -> requests.Response:
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout, stream=stream)
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
def sp500_from_ishares() -> list[dict]:
    r = get(IVV_HOLDINGS_URL)
    text = r.content.decode("utf-8-sig", errors="replace")
    # The file has a preamble; the table starts at the line beginning with "Ticker,"
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("Ticker,"))
    rows = list(csv.DictReader(io.StringIO("\n".join(lines[start:]))))
    out = []
    for row in rows:
        if (row.get("Asset Class") or "").strip() != "Equity":
            continue
        t = (row.get("Ticker") or "").strip()
        if not t or t in {"-", "USD"}:
            continue
        out.append({"ticker": t, "name": (row.get("Name") or "").strip(),
                    "sector": (row.get("Sector") or "").strip(),
                    "weight": float((row.get("Weight (%)") or "0").replace(",", "") or 0)})
    return out


def sp500_from_wikipedia() -> list[dict]:
    r = get(WIKI_SP500_URL)
    html = r.text
    table = html.split('id="constituents"', 1)[1].split("</table>", 1)[0]
    rows = re.findall(r"<tr>(.*?)</tr>", table, flags=re.S)
    out = []
    for tr in rows[1:]:
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)]
        if len(cells) >= 4:
            out.append({"ticker": cells[0].replace(".", "-"), "name": cells[1], "sector": cells[2], "weight": None})
    return out


def sp500_members() -> tuple[list[dict], str]:
    try:
        m = sp500_from_ishares()
        if len(m) >= 480:
            return m, "iShares IVV holdings"
        print(f"  iShares returned only {len(m)} equities; falling back")
    except Exception as e:
        print(f"  iShares fetch failed: {e}; falling back")
    m = sp500_from_wikipedia()
    return m, "Wikipedia list (fallback)"


# --------------------------------------------------------------------------
# Step 2 — ticker -> CIK
# --------------------------------------------------------------------------
def ticker_to_cik() -> dict[str, tuple[int, str]]:
    data = get(TICKER_MAP_URL).json()
    out = {}
    for _, v in data.items():
        out[v["ticker"].upper()] = (int(v["cik_str"]), v["title"])
    return out


def norm_ticker(t: str) -> list[str]:
    """iShares uses BRKB / BF.B style; SEC uses BRK-B / BF-B. Try the variants."""
    t = t.upper().strip()
    cands = [t, t.replace(".", "-"), t.replace("-", "."), t.replace(".", ""), t.replace("-", "")]
    if len(t) == 5 and t[-1] in "AB" and "-" not in t and "." not in t:
        cands.append(t[:4] + "-" + t[4])
    seen, out = set(), []
    for c in cands:
        if c not in seen:
            seen.add(c); out.append(c)
    return out


# --------------------------------------------------------------------------
# Step 4 — normalise one company's facts
# --------------------------------------------------------------------------
def _days(a: str, b: str) -> int:
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def _pick_latest(cands: list[dict]) -> dict | None:
    """Same period reported in several filings (restatements, comparatives): take the latest filed."""
    if not cands:
        return None
    return max(cands, key=lambda f: (f.get("filed", ""), f.get("accn", "")))


def extract_series(facts: dict, tags: list[str], unit_pref: str | None) -> tuple[list[dict], str | None]:
    """Return the facts list for the first tag that has data, in the preferred unit."""
    us = facts.get("facts", {}).get("us-gaap", {})
    dei = facts.get("facts", {}).get("dei", {})
    for tag in tags:
        src, key = (dei, tag[4:]) if tag.startswith("dei:") else (us, tag)
        node = src.get(key)
        if not node:
            continue
        units = node.get("units", {})
        unit = unit_pref if unit_pref in units else next((u for u in ("USD", "shares", "USD/shares") if u in units), None)
        if unit and units[unit]:
            return units[unit], tag
    return [], None


def annual_rows(series: list[dict], kind: str) -> dict[int, dict]:
    """fy -> {value, end, filed, form} from 10-K filings."""
    by_fy: dict[int, list[dict]] = defaultdict(list)
    for f in series:
        if f.get("form") not in ("10-K", "10-K/A", "20-F", "40-F"):
            continue
        if f.get("fp") != "FY":
            continue
        if kind == "flow":
            if not f.get("start") or _days(f["start"], f["end"]) < 340 or _days(f["start"], f["end"]) > 380:
                continue           # skip cumulative / partial-year durations
        fy = f.get("fy")
        if fy is None:
            continue
        # 10-Ks carry 3 years of comparatives; key each by ITS OWN period end, not the filing's fy
        end_year = int(f["end"][:4])
        by_fy[end_year if kind == "instant" else _fy_of_period(f, fy)].append(f)
    return {fy: _pick_latest(v) for fy, v in by_fy.items()}


def _fy_of_period(f: dict, filing_fy: int) -> int:
    """A 10-K for fy=2025 also restates 2024 and 2023; label each fact by the calendar year its
    period ENDS in (Deckers' year ending 2026-03-31 is 2026; Costco's ending 2025-08-31 is 2025)."""
    return int(f["end"][:4])


def quarterly_rows(series: list[dict], kind: str) -> dict[str, dict]:
    """period_end -> fact for genuine 3-month (flow) or instant (balance) values from 10-Q/10-K."""
    by_end: dict[str, list[dict]] = defaultdict(list)
    for f in series:
        if f.get("form") not in ("10-Q", "10-Q/A", "10-K", "10-K/A"):
            continue
        if kind == "flow":
            if not f.get("start"):
                continue
            d = _days(f["start"], f["end"])
            if d < 80 or d > 100:
                continue           # only true quarters; YTD and annual are excluded
        by_end[f["end"]].append(f)
    return {end: _pick_latest(v) for end, v in by_end.items()}


def ytd_rows(series: list[dict]) -> dict[str, dict]:
    """period_end -> 9-month YTD fact (used to derive Q4 when a company reports YTD only)."""
    by_end: dict[str, list[dict]] = defaultdict(list)
    for f in series:
        if f.get("form") not in ("10-Q", "10-Q/A") or not f.get("start"):
            continue
        d = _days(f["start"], f["end"])
        if 260 <= d <= 290:
            by_end[f["end"]].append(f)
    return {end: _pick_latest(v) for end, v in by_end.items()}


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
        ann = annual_rows(series, kind)
        for fy, f in ann.items():
            out_annual[fy][name] = f["val"]
            if name == "revenue" or name == "net_income":
                fy_end_dates.setdefault(fy, f["end"])
            out_annual[fy].setdefault("_end", f["end"])
            out_annual[fy].setdefault("_filed", f.get("filed"))

        # quarterly (true 3-month values)
        q = quarterly_rows(series, kind)
        for end, f in q.items():
            out_q[end][name] = f["val"]
            out_q[end].setdefault("_form", f.get("form"))
            out_q[end].setdefault("_filed", f.get("filed"))

        # derive Q4 for flow items: FY total minus the three quarters (or minus 9-month YTD)
        if kind == "flow":
            ytd = ytd_rows(series)
            for fy, f in ann.items():
                fy_end = f["end"]
                if fy_end in out_q and name in out_q[fy_end]:
                    continue       # company tagged Q4 explicitly (rare) — keep it
                # 9-month YTD ending ~3 months before FY end
                y = next((v for e, v in ytd.items() if 80 <= _days(e, fy_end) <= 100), None)
                if y is not None:
                    out_q[fy_end][name] = f["val"] - y["val"]
                    out_q[fy_end].setdefault("_form", "10-K (Q4 derived: FY − 9M YTD)")
                    out_q[fy_end].setdefault("_filed", f.get("filed"))
                    continue
                # else: three genuine quarters inside the fiscal year
                qs = [v[name] for e, v in out_q.items()
                      if name in v and f.get("start") and f["start"] <= e < fy_end and _days(e, fy_end) >= 80]
                if len(qs) == 3:
                    out_q[fy_end][name] = f["val"] - sum(qs)
                    out_q[fy_end].setdefault("_form", "10-K (Q4 derived: FY − Q1..Q3)")
                    out_q[fy_end].setdefault("_filed", f.get("filed"))

    # instant items at FY end also belong to the FY row (balance sheet at year end)
    for fy, row in out_annual.items():
        end = row.get("_end")
        if end and end in out_q:
            for k, v in out_q[end].items():
                if not k.startswith("_") and CONCEPTS.get(k, {}).get("kind") == "instant":
                    row.setdefault(k, v)

    annual = [dict(fiscal_year=fy, period_end=row.pop("_end", None), filed=row.pop("_filed", None), **row)
              for fy, row in sorted(out_annual.items())][-ANNUAL_YEARS:]
    quarterly = [dict(period_end=end, form=row.pop("_form", None), filed=row.pop("_filed", None), **row)
                 for end, row in sorted(out_q.items())][-QUARTERS:]
    return {"annual": annual, "quarterly": quarterly, "tags_used": tags_used}


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main() -> int:
    t0 = time.time()
    OUT_DIR.mkdir(exist_ok=True); WORK_DIR.mkdir(exist_ok=True)

    print("1. S&P 500 membership")
    members, src = sp500_members()
    print(f"  {len(members)} equities from {src}")

    print("2. ticker -> CIK")
    cmap = ticker_to_cik()
    resolved, unresolved = {}, []
    for m in members:
        hit = None
        for t in norm_ticker(m["ticker"]):
            if t in cmap:
                hit = cmap[t]; break
        if hit:
            resolved[m["ticker"]] = {"cik": hit[0], "sec_name": hit[1], **m}
        else:
            unresolved.append(m["ticker"])
    print(f"  resolved {len(resolved)}; unresolved: {unresolved}")

    print("3. companyfacts bulk zip")
    zpath = download(COMPANYFACTS_ZIP, WORK_DIR / "companyfacts.zip")

    print("4. normalise")
    companies, missing, coverage = {}, [], defaultdict(int)
    with zipfile.ZipFile(zpath) as z:
        names = set(z.namelist())
        for i, (tick, meta) in enumerate(sorted(resolved.items()), 1):
            fname = f"CIK{meta['cik']:010d}.json"
            if fname not in names:
                missing.append(tick); continue
            with z.open(fname) as fh:
                facts = json.load(fh)
            norm = normalise_company(facts)
            companies[tick] = {"cik": meta["cik"], "name": meta["name"], "sec_name": facts.get("entityName", meta["sec_name"]),
                               "sector": meta["sector"], "index_weight": meta.get("weight"), **norm}
            for k, v in norm["tags_used"].items():
                if v: coverage[k] += 1
            if i % 50 == 0:
                print(f"  {i}/{len(resolved)}", flush=True)
    print(f"  {len(companies)} companies; no facts file for: {missing}")

    generated = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    out = {
        "generated_utc": generated,
        "sources": {"facts": COMPANYFACTS_ZIP, "constituents": src, "cik_map": TICKER_MAP_URL},
        "concepts": {k: {"kind": v["kind"], "tags": v["tags"]} for k, v in CONCEPTS.items()},
        "counts": {"constituents": len(members), "resolved": len(resolved), "with_facts": len(companies)},
        "unresolved_tickers": unresolved, "missing_facts": missing,
        "coverage_by_item": dict(sorted(coverage.items())),
        "companies": companies,
    }
    (OUT_DIR / "sec_facts.json").write_text(json.dumps(out, separators=(",", ":")))

    # flat CSVs for anything that prefers tables
    items = list(CONCEPTS.keys())
    with open(OUT_DIR / "sec_facts_annual.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["ticker", "cik", "sector", "fiscal_year", "period_end", "filed"] + items)
        for t, c in sorted(companies.items()):
            for r in c["annual"]:
                w.writerow([t, c["cik"], c["sector"], r["fiscal_year"], r["period_end"], r["filed"]] + [r.get(k) for k in items])
    with open(OUT_DIR / "sec_facts_quarterly.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["ticker", "cik", "sector", "period_end", "form", "filed"] + items)
        for t, c in sorted(companies.items()):
            for r in c["quarterly"]:
                w.writerow([t, c["cik"], c["sector"], r["period_end"], r["form"], r["filed"]] + [r.get(k) for k in items])

    report = [f"# SEC dataset build — {generated}", "",
              f"- constituents: {len(members)} ({src})", f"- resolved to CIK: {len(resolved)}",
              f"- with facts: {len(companies)}", f"- unresolved tickers: {unresolved}", f"- no facts file: {missing}", "",
              "## Coverage by line item (companies with at least one value)", ""]
    report += [f"- {k}: {v}" for k, v in sorted(coverage.items())]
    (OUT_DIR / "REPORT.md").write_text("\n".join(report) + "\n")
    print(f"done in {time.time()-t0:.0f}s -> {OUT_DIR}/sec_facts.json ({(OUT_DIR/'sec_facts.json').stat().st_size/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
