"""Pipeline v2 (owner, 24 Sep 2026): one nightly job for fmp's S&P 500-sized pool, run IN PARALLEL with the old jobs
for a week. It writes ONLY under data/v2/ (and the `library` release assets) and never touches data/companies,
data/events or data/tickers.json, which fmp's live autopilot still reads.

Why: fmp now reads deeply every US company worth >= $22.7B and buys by market value. The old weekly build (every SEC
filer, one tag per concept) kept giving those reads wrong inputs: total_debt = long-term only (CNP, VST, DUK, AEE,
SNPS, ATI, WEC, EXR) or double-counted (NXPI +$2B of commercial paper already inside its current debt); capex missing
where the filer uses its own tag (COP 2023-25, NEE); revenue from a segment or gross line (NTAP $6.24B vs $6.93B,
RSG before eliminations, DTE $61M of lease income, bank revenue); a mislabelled context losing a year (LHX FY2025);
and companyfacts' single share class (HEICO, Carvana) that goes stale around splits.

Steps (main()):
 1. SEC bulk files, 2 requests: submissions.zip and companyfacts.zip (streamed to work/v2, read entry by entry).
    ONLY_TICKERS=AAPL,HEI (a development run) uses the per-company APIs instead, cached in work/v2/api.
 2. Universe: a 10-Q in the last 400 days, a listed common-stock ticker (no preferred / warrant / unit / right
    lines, no OTC), not a partnership (L.P.), not a commodity trust (SIC 6221), revenue on file, market value >=
    UNIVERSE_MIN ($15B, a cushion under S&P's $22.7B). Market value = Yahoo close x shares from the latest 10-Q/10-K
    COVER, every class added up (dei:EntityCommonStockSharesOutstanding by class in the filing's XBRL), times the
    Yahoo splits after the cover date, class weights (data/v2/share_class_weights.csv: Berkshire A = 1,500 B) and
    ADS ratios (data/v2/ads_ratio.csv). Checked against Yahoo's market cap: beyond 3x Yahoo's is used and flagged.
 3. Filing library (library.py, 25 Sep 2026): EVERY filing of the last 3 years and every document in it, for every
    universe company, as release assets on the `library` tag (one <cik>.tar.gz each), checked against EDGAR's count.
    The per-company filing lists come from submissions.zip (step 1), so finding the new filings costs no requests.
 4. Fundamentals from companyfacts, point in time (each value keeps the form and the date it was first public, and
    the first-filed value when later restated), annual + quarterly + TTM, with the tag used per field. The latest
    10-K and 10-Q XBRL instances (from the library) fill a quarter companyfacts lacks (CNP's Q2) and supply the
    company's own capex tag when no us-gaap one exists (COP, NEE).
 5. data/v2/: companies/<cik>.json, universe.csv, changes.jsonl (appended), report.md, compare.md (v2 vs the old
    data/companies file: debt, capex, revenue and shares that differ by > 5%; the parallel week is judged on it).

Env: SEC_USER_AGENT (required), ONLY_TICKERS, LIMIT (largest n companies), UNIVERSE_MIN, LIBRARY=false (skip step 3),
LIBRARY_MINUTES / MAX_NEW_FILINGS / LIBRARY_YEARS / LIBRARY_TAG (library.py), GH_TOKEN (to publish the library;
without it the assets stay in work/library/assets), SEC_MIN_GAP (seconds between SEC requests; 0.5 when sharing
the limit from a workstation), V2_OUT (default data/v2), V2_WORK (default work/v2).
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import json
import os
import re
import sys
import time
import zipfile
from collections import defaultdict
from pathlib import Path

import build_sec_events as _ev
import fetch_filings as ff
import library as lib

OUT = Path(os.environ.get("V2_OUT", "data/v2"))
WORK = Path(os.environ.get("V2_WORK", "work/v2"))
OLD = Path("data/companies")
CONF = Path("data/v2")                 # the two hand-kept CSVs (copied from fmp/owner/data), whatever V2_OUT is
STORE = Path(os.environ.get("FILINGS_STORE", "filings-store"))
UNIVERSE_MIN = float(os.environ.get("UNIVERSE_MIN", "15e9"))
SP_MIN = 22.7e9                        # S&P's minimum market value for adding a company (fmp's pool line)
PRELIM_MIN = 3e9                       # companyfacts-shares estimate (one class only) that earns a Yahoo check
ONLY = [t.strip().upper() for t in os.environ.get("ONLY_TICKERS", "").split(",") if t.strip()]
LIMIT = int(os.environ.get("LIMIT", "0") or 0)
LIBRARY = os.environ.get("LIBRARY", "true").strip().lower() not in ("0", "false", "no")
MIN_GAP = float(os.environ.get("SEC_MIN_GAP", "0") or 0)
TODAY = dt.date.today()
# The two bulk files live in DIFFERENT folders (the first v2 run asked for bulkdata/companyfacts.zip: 403).
BULK = {"submissions": "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip",
        "companyfacts": "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"}
FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A", "10-KT", "10-KT/A", "10-QT"}
PERIODIC = ("10-K", "10-Q", "10-KT", "10-QT")
COVER = "dei:EntityCommonStockSharesOutstanding"

if MIN_GAP > 0.12:                     # slower than build_sec_events' 8/s, for runs that share the SEC limit
    _raw_get, _last = _ev.get, [0.0]

    def _slow_get(url, *a, **k):
        time.sleep(max(0.0, MIN_GAP - (time.time() - _last[0])))
        try:
            return _raw_get(url, *a, **k)
        finally:
            _last[0] = time.time()
    _ev.get = _slow_get


# ================================================================ tags
RFCWC = "RevenueFromContractWithCustomerExcludingAssessedTax"
RNFC = "RevenueNotFromContractWithCustomer"
REV_TOTAL = ["Revenues", "RegulatedAndUnregulatedOperatingRevenue"]
REV_OTHER = ["SalesRevenueNet", "SalesRevenueGoodsNet", "RevenuesNetOfInterestExpense", "RealEstateRevenueNet",
             "OperatingLeasesIncomeStatementLeaseRevenue", "ElectricUtilityRevenue", "RegulatedOperatingRevenue",
             "RevenueFromContractWithCustomerIncludingAssessedTax"]
BANK_NET = "InterestIncomeExpenseNet+NoninterestIncome"
BANK_GROSS = "InterestAndDividendIncomeOperating+NoninterestIncome"
REV_BANK = ["RevenuesNetOfInterestExpense", BANK_NET, BANK_GROSS, "Revenues"]
TOTAL_OVER_606 = 1.25   # "Revenues" beats the ASC 606 line only when >25% bigger (lease, insurance, finance income);
                        # a smaller excess is a gross-before-eliminations or segment sum (RSG 19.0 vs 16.6)

FLOWS = {
    "net_income": ["NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic", "ProfitLoss"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities",
                            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets",
              "PaymentsForCapitalImprovements", "PaymentsToAcquireOilAndGasPropertyAndEquipment",
              "PaymentsToAcquireOilAndGasProperty", "PaymentsToExploreAndDevelopOilAndGasProperties",
              "PaymentsToAcquireOtherPropertyPlantAndEquipment", "PaymentsForConstructionInProcess",
              "PaymentsToDevelopRealEstateAssets"],
    "stock_comp": ["ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"],
    "shares_diluted": ["WeightedAverageNumberOfDilutedSharesOutstanding",
                       "WeightedAverageNumberOfShareOutstandingBasicAndDiluted"],
}
AVERAGES = {"shares_diluted"}          # never differenced from year-to-date figures, never summed into a TTM
# the company's own capex concept (only when no us-gaap one covers the period): the largest per period, which is the
# total when a filer tags pieces too (NEE: FPL 8.7B inside 24.6B; DTE: utility 4.3B next to non-utility 0.1B)
EXT_CAPEX = re.compile(r"CapitalExpenditure|PlantAndEquipmentExpenditure|PaymentsToAcquireProductiveAssets|"
                       r"PaymentsToAcquirePropertyPlantAndEquipment|AdditionsToPropertyPlantAndEquipment|"
                       r"PaymentsForPropertyPlantAndEquipment", re.I)
EXT_CAPEX_NOT = re.compile(r"Planned|Estimat|Commitment|Incurred|NotYetPaid|Accrued|Future|AFUDC|Remainder|Year|"
                           r"Proceeds|Budget|Forecast|Guidance|Percent|Ratio|Business", re.I)
INSTANTS = {
    "cash": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
             "Cash"],
    "short_term_investments": ["ShortTermInvestments", "MarketableSecuritiesCurrent",
                               "AvailableForSaleSecuritiesDebtSecuritiesCurrent"],
    "cash_and_sti_tagged": ["CashCashEquivalentsAndShortTermInvestments"],
    "equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
}
DEBT_NONCURRENT = ["LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations", "LongTermDebt",
                   "LongTermNotesPayable", "SeniorLongTermNotes", "UnsecuredLongTermDebt", "OtherLongTermDebtNoncurrent"]
DEBT_CURRENT_LTD = ["LongTermDebtCurrent", "LongTermDebtAndCapitalLeaseObligationsCurrent", "OtherLongTermDebtCurrent"]
DEBT_SHORT = ["ShortTermBorrowings", "CommercialPaper", "OtherShortTermBorrowings"]
LEASES = ["FinanceLeaseLiability", "FinanceLeaseLiabilityNoncurrent", "FinanceLeaseLiabilityCurrent"]
DEBT_TAGS = DEBT_NONCURRENT + DEBT_CURRENT_LTD + DEBT_SHORT + ["DebtCurrent"] + LEASES


# ================================================================ small helpers
def _d(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def _days(a: str, b: str) -> int:
    return (_d(b) - _d(a)).days


def _num(v):
    v = float(v)
    return int(v) if v.is_integer() else v


def _collapse(fs: list[dict]) -> dict:
    """Every fact for one period -> one record: the latest-filed value, dated by the FIRST filing that showed that
    value (when it became public), plus the first-filed value and date when a later filing restated it."""
    fs = sorted(fs, key=lambda f: (f["filed"], f.get("accn") or ""))
    last = fs[-1]
    same = next(f for f in fs if f["val"] == last["val"])
    r = {"val": _num(last["val"]), "form": same["form"], "filed": same["filed"], "accn": same.get("accn")}
    if fs[0]["val"] != last["val"]:
        r["first_val"], r["first_filed"] = _num(fs[0]["val"]), fs[0]["filed"]
    return r


# ================================================================ periods
def flow_series(fs: list[dict], additive: bool = True) -> tuple[dict, dict, dict]:
    """(annual, quarterly, ytd_ttm), each {end: rec}, from one tag's duration facts. Quarters come straight from
    ~3-month facts or, when additive, as the difference of two year-to-date facts with the same start (Q2 = H1 - Q1,
    Q4 = FY - 9M). ytd_ttm: last fiscal year + this year-to-date - last year's same year-to-date, the TTM when single
    quarters are missing (a company's own capex tag is only in the latest 10-K and 10-Q). A 10-K 'annual' fact on a
    ~3-month context whose value exceeds the 9 months before it (LHX FY2025: 21.9B on Oct-Jan) is read as the year,
    and its quarter as the difference."""
    per = defaultdict(list)
    for f in fs:
        if f.get("start") and f.get("end") and f.get("val") is not None:
            per[(f["start"], f["end"])].append(f)
    P = {k: dict(_collapse(v), start=k[0], end=k[1]) for k, v in per.items()}
    ann, q = {}, {}
    for (s, e), r in sorted(P.items()):
        n = _days(s, e)
        if 340 <= n <= 380 and (e not in ann or abs(n - 365) < abs(_days(ann[e]["start"], e) - 365)):
            ann[e] = r
        elif 80 <= n <= 100:
            q[e] = r
    if not additive:
        return ann, q, {}
    for (s, e), r in P.items():
        if 80 <= _days(s, e) <= 100 and r["form"].startswith("10-K") and e not in ann and r["val"] > 0:
            nine = [p for (s2, e2), p in P.items() if 250 <= _days(s2, e2) <= 290 and 0 < _days(e2, s) <= 7
                    and p["val"] >= 0]
            if nine and r["val"] > nine[0]["val"] * 1.1:
                ann[e] = dict(r, start=nine[0]["start"], note="year reported on a quarter context")
                q[e] = dict(r, val=_num(r["val"] - nine[0]["val"]), derived=True)
    for (s, e), r in P.items():
        if e in q or _days(s, e) <= 100:
            continue
        prev = [p for (s2, e2), p in P.items() if abs(_days(s2, s)) <= 3 and 80 <= _days(e2, e) <= 100]
        if prev:
            p = prev[0]
            q[e] = dict(val=_num(r["val"] - p["val"]), start=str(_d(p["end"]) + dt.timedelta(days=1)), end=e,
                        form=r["form"], filed=max(r["filed"], p["filed"]), accn=r["accn"], derived=True)
    ytd = {}
    for (s, e), r in P.items():
        n = _days(s, e)
        if not 100 < n < 340:
            continue
        a = next((x for ae, x in ann.items() if 0 < _days(ae, s) <= 7), None)
        prior = next((p for (s2, e2), p in P.items() if abs(_days(e2, e) - 365) <= 7 and abs(_days(s2, e2) - n) <= 7
                      and a and _days(a["start"], s2) >= -7 and _days(s2, a["start"]) <= 7), None)
        if a and prior:
            ytd[e] = dict(val=_num(a["val"] + r["val"] - prior["val"]), start=a["start"], end=e, form=r["form"],
                          filed=max(a["filed"], r["filed"], prior["filed"]), accn=r["accn"], derived=True)
    return ann, q, ytd


def instant_series(fs: list[dict]) -> dict:
    per = defaultdict(list)
    for f in fs:
        if not f.get("start") and f.get("end") and f.get("val") is not None:
            per[f["end"]].append(f)
    return {e: dict(_collapse(v), end=e) for e, v in per.items()}


def _sum_series(a: tuple, b: tuple) -> tuple:
    """Two tags' (annual, quarterly) series added period by period (bank revenue = interest + noninterest)."""
    out = []
    for x, y in zip(a, b):
        out.append({e: dict(x[e], val=_num(x[e]["val"] + y[e]["val"]), filed=max(x[e]["filed"], y[e]["filed"]))
                    for e in x if e in y and x[e].get("start") == y[e].get("start")})
    return tuple(out)


# ================================================================ choosing a tag per period
def choose_revenue(c: dict, bank: bool) -> str | None:
    """The revenue tag for one period, from {tag: value}. Banks: net revenue (net interest + noninterest income,
    what RevenuesNetOfInterestExpense means), gross only when net interest income is missing. Others: the ASC 606
    line, unless a total line ('Revenues', utilities' regulated + unregulated) is > 25% bigger (lease, insurance or
    finance income 606 leaves out) or equals it plus RevenueNotFromContractWithCustomer (COP: 51.8 + 7.2 = 58.9);
    otherwise a larger or smaller total is a gross or segment figure (RSG, NTAP)."""
    if bank:
        return next((t for t in REV_BANK if t in c), None) or next((t for t in [RFCWC] + REV_OTHER if t in c), None)
    total = next((t for t in REV_TOTAL if t in c), None)
    if RFCWC in c and total:
        adds_up = RNFC in c and abs(c[RFCWC] + c[RNFC] - c[total]) <= 0.02 * abs(c[total] or 1)
        return total if adds_up or c[total] > c[RFCWC] * TOTAL_OVER_606 else RFCWC
    return (RFCWC if RFCWC in c else total) or next((t for t in REV_OTHER if t in c), None)


def choose_capex(c: dict) -> str | None:
    t = next((t for t in FLOWS["capex"] if t in c), None)
    if t:
        return t
    ext = [t for t in c if t.startswith("ext:")]
    return max(ext, key=lambda t: c[t]) if ext else None


def _pick_per_period(series: dict, chooser) -> tuple[dict, dict, dict]:
    out = ({}, {}, {})
    for k in (0, 1, 2):
        ends = {e for s in series.values() for e in s[k]}
        for e in ends:
            cands = {t: s[k][e] for t, s in series.items() if e in s[k]}
            t = chooser({t: r["val"] for t, r in cands.items()})
            if t:
                out[k][e] = dict(cands[t], tag=t)
    return out


# ================================================================ debt
def assemble_debt(v: dict) -> dict | None:
    """Total debt at one balance-sheet date from {tag: value}, every piece once:
      non-current  LongTermDebtNoncurrent, else LongTermDebtAndCapitalLeaseObligations (non-current by definition),
                   else LongTermDebt MINUS the tagged current portion (LongTermDebt includes it), else a notes tag
      current      DebtCurrent when tagged: it is the whole current side, so commercial paper and short-term
                   borrowings are NOT added again (NXPI: 0.75B DebtCurrent + 2B paper tagged elsewhere was +2B);
                   otherwise the current portion of long-term debt plus short-term borrowings, where short-term =
                   the larger of ShortTermBorrowings and CommercialPaper + OtherShortTermBorrowings, and it is added
                   to the current portion only when it is plainly paper (no ShortTermBorrowings, or one within 5% of
                   the paper); a ShortTermBorrowings line often already holds current maturities (build_sec_dataset
                   debt_build: PepsiCo, Applied Materials), so then the larger of the two is taken, a floor.
    Finance leases are a separate field, never in the total (LongTermDebtAndCapitalLeaseObligations already holds
    the non-current part for some filers)."""
    def first(tags):
        return next(((t, v[t]) for t in tags if v.get(t) is not None), (None, None))
    nt, nonc = first(DEBT_NONCURRENT)
    lt, ltc = first(DEBT_CURRENT_LTD)
    used = [nt] if nt else []
    if nt == "LongTermDebt" and ltc is not None:
        nonc -= ltc
        used.append(lt)
    if v.get("DebtCurrent") is not None:
        cur, cur_tags = v["DebtCurrent"], ["DebtCurrent"]
    else:
        stb = v.get("ShortTermBorrowings")
        paper_tags = [t for t in ("CommercialPaper", "OtherShortTermBorrowings") if v.get(t) is not None]
        paper = sum(v[t] for t in paper_tags) if paper_tags else None
        st_opts = [(x, t) for x, t in ((stb, ["ShortTermBorrowings"]), (paper, paper_tags)) if x is not None]
        st, st_tags = max(st_opts, key=lambda x: x[0]) if st_opts else (None, [])
        only_paper = stb is None or (paper is not None and stb <= paper * 1.05)
        if ltc is not None and st is not None:
            if only_paper:
                cur, cur_tags = ltc + st, [lt] + st_tags
            else:
                cur, cur_tags = (ltc, [lt]) if ltc >= st else (st, st_tags)
        else:
            cur, cur_tags = (ltc, [lt]) if ltc is not None else (st, st_tags)
    if nonc is None and cur is None:
        return None
    used += [t for t in cur_tags if t not in used]
    lease = v.get("FinanceLeaseLiability")
    if lease is None and (v.get("FinanceLeaseLiabilityNoncurrent") is not None
                          or v.get("FinanceLeaseLiabilityCurrent") is not None):
        lease = (v.get("FinanceLeaseLiabilityNoncurrent") or 0) + (v.get("FinanceLeaseLiabilityCurrent") or 0)
    return {"total_debt": _num((nonc or 0) + (cur or 0)), "debt_noncurrent": None if nonc is None else _num(nonc),
            "debt_current": None if cur is None else _num(cur), "finance_leases": None if lease is None else _num(lease),
            "tags": used, "both_sides": nonc is not None and cur is not None}


# ================================================================ companyfacts -> fundamentals
def load_facts(cf: dict) -> dict:
    """{tag: [facts]} from a companyfacts document: us-gaap, the USD (or shares) unit, 10-K/10-Q forms only."""
    out = {}
    for tag, v in ((cf or {}).get("facts", {}).get("us-gaap") or {}).items():
        units = v.get("units", {})
        u = "USD" if "USD" in units else "shares" if "shares" in units else None
        if u:
            fs = [f for f in units[u] if f.get("form") in FORMS]
            if fs:
                out[tag] = fs
    return out


def merge_instance(F: dict, xfacts: dict, form: str, filed: str, accn: str) -> int:
    """Adds one filing's XBRL instance (fetch_filings.xbrl_facts shape) to F: every undimensioned us-gaap fact when
    companyfacts does not have that filing yet, and always the company's own capex concepts (as 'ext:<name>'),
    which companyfacts never carries. Returns the number of facts added."""
    have = any(f.get("accn") == accn for fs in F.values() for f in fs)
    n = 0
    for concept, rows in (xfacts or {}).items():
        prefix, _, name = concept.partition(":")
        ext = prefix not in ("us-gaap", "dei", "srt", "ifrs-full") and EXT_CAPEX.search(name) \
            and not EXT_CAPEX_NOT.search(name)
        if not ext and (prefix != "us-gaap" or have):
            continue
        key = f"ext:{name}" if ext else name
        seen = {(f.get("start"), f["end"], f.get("accn")) for f in F.get(key, [])}
        for val, unit, start, end, dims in rows:
            if dims or not isinstance(val, (int, float)) or unit not in ("USD", "shares") or not end:
                continue
            if ext and not start:
                continue
            if (start, end, accn) in seen:
                continue
            seen.add((start, end, accn))
            f = {"val": val, "end": end, "form": form, "filed": filed, "accn": accn}
            if start:
                f["start"] = start
            F.setdefault(key, []).append(f)
            n += 1
    return n


def is_bank(F: dict) -> bool:
    return "NoninterestIncome" in F and ("InterestIncomeExpenseNet" in F or "InterestAndDividendIncomeOperating" in F)


def _ttm(q: dict, ann: dict, ytd: dict, average: bool = False) -> dict | None:
    """Trailing twelve months at the latest period on file: the fiscal year when it ends there, else the last four
    contiguous quarters, else last year + year-to-date - last year's year-to-date, else the latest year (marked
    stale). Averages (share counts) take the latest period."""
    if not q and not ann:
        return None
    ends = sorted(q)
    last_q = ends[-1] if ends else None
    last_a = max(ann) if ann else None
    latest = max([e for e in (last_q, last_a) if e] + ([] if average else list(ytd)))
    if last_a == latest:
        r = ann[last_a]
        return {"val": r["val"], "end": last_a, "method": "fiscal_year", "filed": r["filed"], "tags": [r["tag"]]}
    if average and last_q == latest:
        r = q[last_q]
        return {"val": r["val"], "end": last_q, "method": "latest_quarter", "filed": r["filed"], "tags": [r["tag"]]}
    four = ends[-4:]
    if not average and last_q == latest and len(four) == 4 and \
            all(80 <= _days(a, b) <= 100 for a, b in zip(four, four[1:])):
        rs = [q[e] for e in four]
        return {"val": _num(sum(r["val"] for r in rs)), "end": last_q, "method": "four_quarters",
                "filed": max(r["filed"] for r in rs), "tags": sorted({r["tag"] for r in rs})}
    if latest in ytd:
        r = ytd[latest]
        return {"val": r["val"], "end": latest, "method": "year_to_date", "filed": r["filed"], "tags": [r["tag"]]}
    if last_a:
        r = ann[last_a]
        return {"val": r["val"], "end": last_a, "method": "fiscal_year_stale", "filed": r["filed"], "tags": [r["tag"]]}
    return None


def _src(r: dict) -> dict:
    s = {k: r[k] for k in ("tag", "form", "filed", "accn", "first_val", "first_filed", "derived", "note") if k in r}
    return s


def fundamentals(F: dict) -> dict:
    """Annual and quarterly rows, TTM and the latest balance sheet from load_facts() (+ merge_instance()) output.
    Each row: {end, start, <field>: value, ..., src: {<field>: {tag, form, filed, accn[, first_val, first_filed,
    derived]}}}. Debt pieces sit in the row next to total_debt, their tags in src.total_debt.tags."""
    flows = {}
    bank = is_bank(F)
    rev_tags = [RFCWC, RNFC] + REV_TOTAL + REV_OTHER + ["InterestIncomeExpenseNet", "InterestAndDividendIncomeOperating",
                                                  "NoninterestIncome"]
    rs = {t: flow_series(F[t]) for t in rev_tags if t in F}
    if bank:
        for name, (a, b) in ((BANK_NET, ("InterestIncomeExpenseNet", "NoninterestIncome")),
                             (BANK_GROSS, ("InterestAndDividendIncomeOperating", "NoninterestIncome"))):
            if a in rs and b in rs:
                rs[name] = _sum_series(rs[a], rs[b])
    for t in ("InterestIncomeExpenseNet", "InterestAndDividendIncomeOperating", "NoninterestIncome"):
        rs.pop(t, None)
    flows["revenue"] = _pick_per_period(rs, lambda c: choose_revenue(c, bank))
    for field, tags in FLOWS.items():
        ser = {t: flow_series(F[t], additive=field not in AVERAGES) for t in tags if t in F}
        if field == "capex":
            ser.update({t: flow_series(fs) for t, fs in F.items() if t.startswith("ext:")})
            flows[field] = _pick_per_period(ser, choose_capex)
        else:
            flows[field] = _pick_per_period(ser, lambda c, tags=tags: next((t for t in tags if t in c), None))
    inst = {t: instant_series(F[t]) for t in set(DEBT_TAGS) | {t for ts in INSTANTS.values() for t in ts} if t in F}

    def balance(row: dict, e: str):
        for field, tags in INSTANTS.items():
            t = next((t for t in tags if e in inst.get(t, {})), None)
            if t:
                row[field] = inst[t][e]["val"]
                row["src"][field] = _src(dict(inst[t][e], tag=t))
        cs = row.pop("cash_and_sti_tagged", None)
        row["src"].pop("cash_and_sti_tagged", None)
        if cs is None and row.get("cash") is not None:
            cs = row["cash"] + (row.get("short_term_investments") or 0)
        if cs is not None:
            row["cash_and_sti"] = _num(cs)
        vals = {t: inst[t][e] for t in DEBT_TAGS if e in inst.get(t, {})}
        debt = assemble_debt({t: r["val"] for t, r in vals.items()})
        if debt:
            tags = debt.pop("tags")
            both = debt.pop("both_sides")
            row.update({k: x for k, x in debt.items() if x is not None})
            row["src"]["total_debt"] = {"tags": tags, "values": {t: vals[t]["val"] for t in tags},
                                        "filed": max(vals[t]["filed"] for t in tags),
                                        **({} if both else {"note": "one side only (a floor)"})}

    def rows(k: int) -> list[dict]:
        ends = sorted({e for f in ("revenue", "net_income", "operating_cash_flow") for e in flows[f][k]})
        out = []
        for e in ends:
            row = {"end": e, "src": {}}
            for field, ser in flows.items():
                r = ser[k].get(e)
                if r:
                    row[field] = r["val"]
                    row.setdefault("start", r.get("start"))
                    row["src"][field] = _src(r)
            if row.get("operating_cash_flow") is not None and row.get("capex") is not None:
                row["fcf"] = _num(row["operating_cash_flow"] - row["capex"])
            balance(row, e)
            out.append(row)
        return out

    annual, quarterly = rows(0), rows(1)
    ttm = {f: _ttm(flows[f][1], flows[f][0], flows[f][2], f in AVERAGES) for f in flows}
    ttm = {f: v for f, v in ttm.items() if v}
    if "operating_cash_flow" in ttm and "capex" in ttm and ttm["operating_cash_flow"]["end"] == ttm["capex"]["end"]:
        ttm["fcf"] = {"val": _num(ttm["operating_cash_flow"]["val"] - ttm["capex"]["val"]),
                      "end": ttm["capex"]["end"], "method": ttm["capex"]["method"]}
    bal_rows = [r for r in annual + quarterly if "total_debt" in r or "equity" in r or "cash_and_sti" in r]
    latest = max(bal_rows, key=lambda r: r["end"]) if bal_rows else {}
    bal = {k: latest[k] for k in ("end", "cash_and_sti", "total_debt", "debt_noncurrent", "debt_current",
                                  "finance_leases", "equity") if k in latest}
    tags = {f: sorted({r["tag"] for k in (0, 1, 2) for r in ser[k].values()}) for f, ser in flows.items()}
    flags = [f"no_{f}" for f in ("revenue", "operating_cash_flow", "capex") if f not in ttm]
    newest = max([r["end"] for r in annual + quarterly] or [""])
    for f, v in ttm.items():                         # a field its filer stopped tagging (MTB capex after 2023)
        if newest and v.get("end") and _days(v["end"], newest) > 200:
            v["stale"] = True
            flags.append(f"stale_{f}")
    if not bal.get("total_debt") and bal:
        flags.append("no_debt_tagged")
    if latest and latest.get("src", {}).get("total_debt", {}).get("note"):
        flags.append("debt_one_side_only")
    return {"bank": bank, "annual": annual, "quarterly": quarterly, "ttm": ttm, "balance": bal,
            "tags_used": tags, "flags": flags}


# ================================================================ shares and market value
def cover_classes(xfacts: dict) -> tuple[str | None, dict]:
    """(cover date, {class: shares}) from a 10-Q/10-K instance's dei:EntityCommonStockSharesOutstanding. Rows on
    dei:LegalEntityAxis are co-registrant subsidiaries (CNP's Houston Electric: 1,000 shares) and are dropped when the
    parent's own rows exist; an undimensioned total next to the classes is not counted twice."""
    rows = [r for r in (xfacts or {}).get(COVER, []) if isinstance(r[0], (int, float))]
    own = [r for r in rows if not any("LegalEntityAxis" in a for a in r[4])]
    rows = own or rows
    got, date = {}, None
    for val, _u, _s, end, dims in rows:
        cls = "|".join(sorted(m.split(":")[-1] for m in dims.values())) or "common"
        got[cls] = max(got.get(cls, 0), float(val))
        date = max(date or "", end or "") or None
    if len(got) > 1 and "common" in got:
        rest = sum(v for k, v in got.items() if k != "common")
        if abs(got["common"] - rest) / max(rest, 1) < 0.02:
            got.pop("common")
    return date, got


def load_weights(path: Path) -> dict:
    """ticker -> [(class substring, weight)]"""
    out = defaultdict(list)
    if path.exists():
        for r in csv.DictReader(path.open()):
            out[r["ticker"]].append((r["class_match"], float(r["weight"])))
    return dict(out)


def load_ads(path: Path) -> dict:
    return {r["ticker"]: float(r["ordinary_per_ads"]) for r in csv.DictReader(path.open())} if path.exists() else {}


def shares_total(by_class: dict, ticker: str, weights: dict, ads: dict, split: float = 1.0) -> float | None:
    """Shares in units of the listed ticker: every class added up, a class worth N listed shares counted N times,
    times the splits after the cover date, divided by the ADS ratio when the listing is an ADS."""
    if not by_class:
        return None
    n = 0.0
    for cls, v in by_class.items():
        w = next((w for m, w in weights.get(ticker, []) if m.lower() in cls.lower()), 1.0)
        n += v * w
    return n * (split or 1.0) / ads.get(ticker, 1.0)


def mcap_check(own: float | None, yahoo: float | None) -> tuple[float | None, str]:
    """(market value used, check). Ours unless it is more than 3x off Yahoo's (a wrong class, scale or ADS: use
    Yahoo's and flag); a gap over 15% is flagged either way."""
    if not own and not yahoo:
        return None, "no_value"
    if not yahoo:
        return own, "no_yahoo"
    if not own:
        return yahoo, "own_missing_used_yahoo"
    r = own / yahoo
    if r > 3 or r < 1 / 3:
        return yahoo, f"off_{r:.2f}x_used_yahoo"
    return own, ("ok" if abs(r - 1) <= 0.15 else f"gap_{(r - 1) * 100:+.0f}pct")


# ================================================================ universe filters
_PARTNERSHIP = re.compile(r"(\bL\.?\s?P\.?|\bLLLP|\bLIMITED PARTNERSHIP)\s*$", re.I)
_NOT_COMMON = re.compile(r"(-P[A-Z]?|-W[ST]?|-WI|-U|-R|-RT|-CL|\.PR[A-Z]?|-PR[A-Z]?)$")
COMMODITY_SIC = {"6221"}


def is_partnership(name: str) -> bool:
    return bool(_PARTNERSHIP.search((name or "").strip().rstrip(",")))


def primary_ticker(tickers: list, exchanges: list) -> str | None:
    """The first listed (non-OTC) ticker that is not a preferred, warrant, unit or right line. A 5-letter Nasdaq
    symbol ending in W/U/R next to its 4-letter base is the base's warrant / unit / right."""
    ts = [t for t, x in zip(tickers or [], (exchanges or []) + [None] * len(tickers or []))
          if t and x and x.upper() != "OTC" and not _NOT_COMMON.search(t.upper())]
    ts = [t for t in ts if not (len(t) == 5 and t[-1] in "WUR" and t[:4] in ts)]
    return ts[0].upper().replace(".", "-") if ts else None


def latest_periodic(sub: dict) -> dict | None:
    r = sub.get("filings", {}).get("recent", {})
    rows = [dict(form=f, filed=d, accn=a, report=p) for f, d, a, p in
            zip(r.get("form", []), r.get("filingDate", []), r.get("accessionNumber", []), r.get("reportDate", []))
            if f in PERIODIC]
    return max(rows, key=lambda x: (x["filed"], x["accn"])) if rows else None


def candidate(sub: dict, today: dt.date = TODAY) -> tuple[dict | None, str]:
    """(candidate, '') for a US 10-Q filer with a listed common ticker, else (None, reason)."""
    r = sub.get("filings", {}).get("recent", {})
    since = str(today - dt.timedelta(days=400))
    if not any(f == "10-Q" and d >= since for f, d in zip(r.get("form", []), r.get("filingDate", []))):
        return None, "no_recent_10q"
    t = primary_ticker(sub.get("tickers") or [], sub.get("exchanges") or [])
    if not t:
        return None, "no_listed_common_ticker"
    if is_partnership(sub.get("name")):
        return None, "partnership"
    if str(sub.get("sic")) in COMMODITY_SIC:
        return None, "commodity_trust"
    return {"cik": int(sub["cik"]), "ticker": t, "tickers": sub.get("tickers"), "name": sub.get("name"),
            "sic": sub.get("sic"), "sic_description": sub.get("sicDescription"), "fye": sub.get("fiscalYearEnd"),
            "latest": latest_periodic(sub)}, ""


def cf_shares(cf: dict) -> float | None:
    """companyfacts' latest cover count (ONE class for multi-class filers: only a pre-screen)."""
    fs = [f for f in (cf or {}).get("facts", {}).get("dei", {}).get("EntityCommonStockSharesOutstanding", {})
          .get("units", {}).get("shares", []) if f.get("val")]
    if not fs:
        return None
    last = max(f["end"] for f in fs)
    return float(max(f["val"] for f in fs if f["end"] == last))


# ================================================================ change log and comparison
HEADLINE = ("revenue", "net_income", "operating_cash_flow", "capex")


def headline(rec: dict) -> dict:
    h = {f"{f}_ttm": (rec.get("ttm", {}).get(f) or {}).get("val") for f in HEADLINE}
    h.update({k: rec.get("balance", {}).get(k) for k in ("total_debt", "equity", "cash_and_sti")})
    h["shares_total"] = rec.get("market", {}).get("shares_total")
    return h


def company_changes(prev: dict | None, new: dict) -> list[dict]:
    base = {"date": str(TODAY), "cik": new["cik"], "ticker": new["ticker"]}
    if not prev:
        return []
    out = []
    pf, nf = prev.get("latest_filing") or {}, new.get("latest_filing") or {}
    if nf.get("accn") and nf.get("accn") != pf.get("accn"):
        out.append(dict(base, type="new_filing", form=nf.get("form"), filed=nf.get("filed"), accession=nf["accn"]))
    ph, nh = headline(prev), headline(new)
    for k, v in nh.items():
        if v != ph.get(k) and not (k == "shares_total" and v and ph.get(k) and abs(v / ph[k] - 1) < 0.001):
            out.append(dict(base, type="fact_change", field=k, old=ph.get(k), new=v))
    return out


def universe_changes(prev: dict, new: dict) -> list[dict]:
    """prev/new: {cik: universe row}. Entering/leaving, and market value crossing S&P's $22.7B line."""
    out = []
    for cik in sorted(set(prev) | set(new)):
        p, n = prev.get(cik), new.get(cik)
        row = {"date": str(TODAY), "cik": int(cik), "ticker": (n or p)["ticker"]}
        if p is None:
            out.append(dict(row, type="entered_universe", mcap=n["mcap_used"]))
        elif n is None:
            out.append(dict(row, type="left_universe", mcap=p["mcap_used"]))
        else:
            a, b = float(p["mcap_used"] or 0), float(n["mcap_used"] or 0)
            if (a >= SP_MIN) != (b >= SP_MIN):
                out.append(dict(row, type="crossed_sp500_line", direction="up" if b >= SP_MIN else "down",
                                old=a, new=b))
    return out


def _pct(a, b):
    return None if not a or b is None else (b - a) / abs(a) * 100


def compare_company(old: dict, new: dict) -> list[dict]:
    """Where v2 and the old data/companies record differ by > 5% (or one side is missing): revenue and capex of
    the latest fiscal year both have, debt at the latest balance date both have (else each side's latest), and
    shares (old latest quarterly shares_outstanding vs v2's cover total before class weights)."""
    out = []

    def add(field, period, a, b):
        p = _pct(a, b)
        if (a is None) != (b is None) or (p is not None and abs(p) > 5) or (a == 0 and b):
            out.append({"field": field, "period": period, "old": a, "v2": b, "pct": None if p is None else round(p, 1)})
    oa = {r.get("period_end"): r for r in old.get("annual", []) if r.get("period_end")}
    na = {r["end"]: r for r in new.get("annual", [])}
    both = sorted(set(oa) & set(na))
    if both:
        e = both[-1]
        for f in ("revenue", "capex"):
            add(f, e, oa[e].get(f), na[e].get(f))
    oq = {r.get("period_end"): r for r in old.get("quarterly", []) + old.get("annual", [])
          if r.get("period_end") and r.get("total_debt") is not None}
    nq = {r["end"]: r for r in new.get("quarterly", []) + new.get("annual", []) if r.get("total_debt") is not None}
    common = sorted(set(oq) & set(nq))
    if common:
        add("total_debt", common[-1], oq[common[-1]].get("total_debt"), nq[common[-1]].get("total_debt"))
    elif oq or nq:
        a, b = (oq[max(oq)] if oq else {}), (nq[max(nq)] if nq else {})
        add("total_debt", f"{max(oq) if oq else '-'} / {max(nq) if nq else '-'}", a.get("total_debt"),
            b.get("total_debt"))
    osh = next((r.get("shares_outstanding") for r in sorted(old.get("quarterly", []),
                key=lambda r: r.get("period_end", ""), reverse=True) if r.get("shares_outstanding")), None)
    add("shares", (new.get("market") or {}).get("cover_date"), osh, (new.get("market") or {}).get("shares_cover"))
    return out


# ================================================================ I/O: SEC sources
def download(name: str) -> Path:
    import requests
    dest = WORK / f"{name}.zip"
    if dest.exists() and dest.stat().st_size and time.time() - dest.stat().st_mtime < 20 * 3600:
        return dest
    WORK.mkdir(parents=True, exist_ok=True)
    print(f"downloading {name}.zip", flush=True)
    for k in range(4):                                             # a refused or cut download is retried
        try:
            with requests.get(BULK[name], headers=_ev.HEADERS, stream=True, timeout=600) as r:
                r.raise_for_status()
                tmp = dest.with_suffix(".part")
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            break
        except Exception as e:                                     # noqa: BLE001
            print(f"  {name}.zip attempt {k + 1}: {type(e).__name__}: {e}", flush=True)
            if k == 3:
                raise
            time.sleep(60 * (k + 1))
    tmp.rename(dest)
    print(f"  {dest.stat().st_size / 1e6:.0f} MB", flush=True)
    return dest


class Sources:
    """submissions + companyfacts: the two bulk zips, or (ONLY_TICKERS) the per-company APIs cached in work/v2/api."""

    def __init__(self):
        self.only = None
        if ONLY:
            tick = json.loads(Path("data/tickers.json").read_text())
            self.only = [int(tick[t]["cik"]) for t in ONLY if t in tick]
        else:
            self.sub_zip = zipfile.ZipFile(download("submissions"))
            self.cf_zip = zipfile.ZipFile(download("companyfacts"))

    def _api(self, url: str, key: str):
        p = WORK / "api" / key
        if p.exists():
            return json.loads(p.read_text())
        r = ff.get(url)
        if r is None:
            return None
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(r.text)
        return r.json()

    def submissions(self):
        if self.only is not None:
            for cik in self.only:
                s = self._api(_ev.SUBMISSIONS.format(cik=cik), f"sub_{cik}.json")
                if s:
                    yield s
            return
        for n in self.sub_zip.namelist():
            if not re.fullmatch(r"CIK\d{10}\.json", n):
                continue
            raw = self.sub_zip.read(n)
            if b'"tickers":[]' in raw[:6000] or b'"10-Q"' not in raw:
                continue
            yield json.loads(raw)

    def submission(self, cik: int) -> dict | None:
        """One company's submissions JSON (library step): from the bulk zip, else the API."""
        if self.only is None:
            try:
                return json.loads(self.sub_zip.read(f"CIK{cik:010d}.json"))
            except KeyError:
                pass
        return self._api(_ev.SUBMISSIONS.format(cik=cik), f"sub_{cik}.json")

    def submission_page(self, name: str) -> dict | None:
        """An older submissions page (CIK##########-submissions-001.json): from the bulk zip, else the API."""
        if self.only is None:
            try:
                return json.loads(self.sub_zip.read(name))
            except KeyError:
                pass
        return self._api("https://data.sec.gov/submissions/" + name, name)

    def facts(self, cik: int) -> dict | None:
        if self.only is not None:
            return self._api(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json", f"cf_{cik}.json")
        try:
            return json.loads(self.cf_zip.read(f"CIK{cik:010d}.json"))
        except KeyError:
            return None


def instance(cik: int, accn: str) -> dict | None:
    """A filing's XBRL facts: from the library when it has them, else work/v2/xbrl, else fetched (2 requests)."""
    for p in (STORE / str(cik) / f"{accn}_xbrl.json.gz", WORK / "xbrl" / f"{cik}_{accn}.json.gz"):
        if p.exists():
            try:
                with gzip.open(p, "rt") as fh:
                    return json.load(fh)
            except Exception:                                       # noqa: BLE001
                pass
    u = ff.instance_url(cik, accn)
    r = ff.get(u) if u else None
    if r is None:
        return None
    try:
        facts = ff.xbrl_facts(r.content)
    except Exception as e:                                          # noqa: BLE001
        print(f"  {cik} {accn}: instance unreadable ({type(e).__name__})")
        return None
    p = WORK / "xbrl" / f"{cik}_{accn}.json.gz"
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, "wt") as fh:
        json.dump(facts, fh, separators=(",", ":"))
    return facts


def latest_two(sub: dict) -> list[dict]:
    """The latest 10-K (or 10-KT) and the latest 10-Q: both instances feed fundamentals."""
    r = sub.get("filings", {}).get("recent", {})
    rows = [dict(form=f, filed=d, accn=a) for f, d, a in
            zip(r.get("form", []), r.get("filingDate", []), r.get("accessionNumber", []))]
    out = []
    for forms in (("10-K", "10-KT"), ("10-Q", "10-QT")):
        c = [x for x in rows if x["form"] in forms]
        if c:
            out.append(max(c, key=lambda x: (x["filed"], x["accn"])))
    return out


# ================================================================ I/O: Yahoo
def yahoo_prices(tickers: list[str]) -> dict:
    """{ticker: (close, date, [(split date, ratio)])} from batched yfinance downloads (1 year, with actions)."""
    import yfinance as yf
    out = {}
    for i in range(0, len(tickers), 100):
        b = tickers[i:i + 100]
        try:
            h = yf.download(b, period="1y", progress=False, auto_adjust=False, actions=True, threads=True,
                            group_by="column")
        except Exception as e:                                      # noqa: BLE001
            print(f"  price batch {i}: {type(e).__name__}"); continue
        for t in b:
            try:
                c = h["Close"][t].dropna() if len(b) > 1 or t in h["Close"] else h["Close"].dropna()
                if not len(c):
                    continue
                sp = h["Stock Splits"][t].fillna(0) if "Stock Splits" in h else None
                splits = [(str(d.date()), float(x)) for d, x in sp.items() if x and x > 0] if sp is not None else []
                out[t] = (float(c.iloc[-1]), str(c.index[-1].date()), splits)
            except Exception:                                       # noqa: BLE001
                pass
    return out


def yahoo_mcap(t: str) -> float | None:
    try:
        import yfinance as yf
        v = yf.Ticker(t).fast_info["market_cap"]
        return float(v) if v else None
    except Exception:                                               # noqa: BLE001
        return None


def split_after(splits: list, date: str | None) -> float:
    f = 1.0
    for d, r in splits or []:
        if date and d > date:
            f *= r
    return f


# ================================================================ main
def build_universe(src: Sources, weights: dict, ads: dict, report: dict) -> list[dict]:
    cands, dropped = [], defaultdict(int)
    for sub in src.submissions():
        c, why = candidate(sub)
        if c:
            c["_two"] = latest_two(sub)                             # not the whole record: thousands are held
            cands.append(c)
        else:
            dropped[why] += 1
    print(f"candidates: {len(cands)} US 10-Q filers with a listed common ticker", flush=True)
    for c in cands:
        c["cf_shares"] = cf_shares(src.facts(c["cik"])) if not ONLY else None
    px = yahoo_prices(sorted({c["ticker"] for c in cands}))
    uni = []
    for c in cands:
        p = px.get(c["ticker"])
        c["price"], c["price_date"], c["_splits"] = (p if p else (None, None, []))
        pre = (c["price"] or 0) * (c["cf_shares"] or 0)
        if ONLY or pre >= PRELIM_MIN or c["cf_shares"] is None:
            c["mcap_yahoo"] = yahoo_mcap(c["ticker"])
        else:
            c["mcap_yahoo"] = None
        if not ONLY and max(pre, c["mcap_yahoo"] or 0) < UNIVERSE_MIN * 0.66:
            dropped["under_value_prescreen"] += 1
            continue
        cov_date, classes, cov = None, {}, c["latest"]
        if cov:
            x = instance(c["cik"], cov["accn"])
            cov_date, classes = cover_classes(x) if x else (None, {})
        c["cover_date"], c["classes"] = cov_date, classes
        c["split"] = split_after(c["_splits"], cov_date)
        raw = sum(classes.values()) if classes else None
        c["shares_cover"] = raw
        c["shares_total"] = shares_total(classes, c["ticker"], weights, ads, c["split"])
        own = c["price"] * c["shares_total"] if c["price"] and c["shares_total"] else None
        if own is None and c["price"] and c["cf_shares"]:
            own = c["price"] * c["cf_shares"] / ads.get(c["ticker"], 1.0)
            c["cover_note"] = "cover unreadable: companyfacts shares"
        c["mcap_own"] = own
        c["mcap_used"], c["mcap_check"] = mcap_check(own, c["mcap_yahoo"])
        if (c["mcap_used"] or 0) >= UNIVERSE_MIN:
            uni.append(c)
        else:
            dropped["under_value"] += 1
    uni.sort(key=lambda c: -(c["mcap_used"] or 0))
    if LIMIT:
        uni = uni[:LIMIT]
    report["dropped"] = dict(dropped)
    return uni


def run_library(uni: list[dict], changes: list, src: Sources) -> dict:
    """library.run for the universe; its new-filing entries join data/v2/changes.jsonl with source=library."""
    lib_changes: list = []
    stats = lib.run([dict(cik=c["cik"], ticker=c["ticker"], name=c["name"], mcap=c["mcap_used"]) for c in uni],
                    lib_changes, src.submission, src.submission_page, full=not LIMIT and not ONLY)
    changes += [dict(ch, source="library") for ch in lib_changes]
    return stats


def company_record(c: dict, src: Sources) -> dict | None:
    cf = src.facts(c["cik"])
    F = load_facts(cf)
    merged = []
    for f in c["_two"]:
        x = instance(c["cik"], f["accn"])
        if x and merge_instance(F, x, f["form"], f["filed"], f["accn"]):
            merged.append(f["accn"])
    fund = fundamentals(F)
    lf = c["latest"] or {}
    return {"cik": c["cik"], "ticker": c["ticker"], "tickers": c["tickers"], "name": c["name"], "sic": c["sic"],
            "sic_description": c["sic_description"], "fiscal_year_end": c["fye"],
            "latest_filing": lf, "instances_merged": merged,
            "market": {"shares_total": c["shares_total"], "shares_cover": c["shares_cover"], "classes": c["classes"],
                       "cover_date": c["cover_date"], "cover_accession": lf.get("accn"), "split_after_cover": c["split"],
                       "ads_ratio": None, "note": c.get("cover_note")},
            **fund}


UNI_COLS = ["ticker", "cik", "name", "price", "shares_total", "classes", "mcap_own", "mcap_yahoo", "mcap_used",
            "mcap_check", "price_date", "cover_date", "cover_form", "split_after_cover", "sic"]


def _uni_row(c: dict) -> dict:
    return {"ticker": c["ticker"], "cik": c["cik"], "name": c["name"], "price": c["price"],
            "shares_total": None if c["shares_total"] is None else round(c["shares_total"]),
            "classes": json.dumps(c["classes"], sort_keys=True), "mcap_own": _r(c["mcap_own"]),
            "mcap_yahoo": _r(c["mcap_yahoo"]), "mcap_used": _r(c["mcap_used"]), "mcap_check": c["mcap_check"],
            "price_date": c["price_date"], "cover_date": c["cover_date"], "cover_form": (c["latest"] or {}).get("form"),
            "split_after_cover": c["split"], "sic": c["sic"]}


def _r(x):
    return None if x is None else round(x)


def _fmt(x):
    if x is None:
        return "-"
    return f"{x / 1e9:,.2f}B" if abs(x) >= 1e8 else f"{x / 1e6:,.1f}M" if abs(x) >= 1e5 else f"{x:,.0f}"


def main() -> int:
    if not os.environ.get("SEC_USER_AGENT"):
        print("set SEC_USER_AGENT"); return 1
    t0 = time.time()
    weights, ads = load_weights(CONF / "share_class_weights.csv"), load_ads(CONF / "ads_ratio.csv")
    report: dict = {}
    src = Sources()
    uni = build_universe(src, weights, ads, report)
    print(f"universe: {len(uni)} companies >= ${UNIVERSE_MIN / 1e9:.1f}B ({time.time() - t0:.0f}s)", flush=True)
    changes: list = []
    report["library"] = None
    if LIBRARY:
        report["library"] = run_library(uni, changes, src)
        print(f"library done ({time.time() - t0:.0f}s)", flush=True)
    (OUT / "companies").mkdir(parents=True, exist_ok=True)
    recs, excluded, compare = [], [], []
    for i, c in enumerate(uni, 1):
        try:
            rec = company_record(c, src)
        except Exception as e:                                      # noqa: BLE001
            print(f"  {c['ticker']}: {type(e).__name__}: {e}"); excluded.append((c, f"error {type(e).__name__}"))
            continue
        rec["market"]["ads_ratio"] = ads.get(c["ticker"])
        if "revenue" not in rec["ttm"]:
            excluded.append((c, "no revenue (fund / trust / shell)")); continue
        path = OUT / "companies" / f"{c['cik']}.json"
        prev = json.loads(path.read_text()) if path.exists() else None
        changes += company_changes(prev, rec)
        path.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
        old = OLD / f"{c['cik']}.json"
        if old.exists():
            compare += [dict(d, ticker=c["ticker"]) for d in compare_company(json.loads(old.read_text()), rec)]
        else:
            compare.append({"ticker": c["ticker"], "field": "file", "period": "-", "old": None, "v2": None,
                            "pct": None})
        recs.append((c, rec))
        if i % 50 == 0:
            print(f"  {i}/{len(uni)} companies", flush=True)
    kept = [c for c, _ in recs]
    # universe.csv + universe changes (full runs only: a LIMIT/ONLY run is a sample, not the universe)
    uni_path = OUT / "universe.csv"
    if not LIMIT and not ONLY:
        prev = {r["cik"]: r for r in csv.DictReader(uni_path.open())} if uni_path.exists() else {}
        new = {str(c["cik"]): _uni_row(c) for c in kept}
        if prev:                                                    # the first run is not "600 entered"
            changes += universe_changes(prev, new)
        for p in (OUT / "companies").glob("*.json"):
            if p.stem not in new:
                p.unlink()
    with uni_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=UNI_COLS)
        w.writeheader()
        for c in kept:
            w.writerow(_uni_row(c))
    with (OUT / "changes.jsonl").open("a") as f:
        for ch in changes:
            f.write(json.dumps(ch, sort_keys=True) + "\n")
    write_compare(compare, kept)
    write_report(report, recs, excluded, changes, time.time() - t0)
    print((OUT / "report.md").read_text())
    return 0


def write_compare(rows: list[dict], kept: list[dict]):
    by = defaultdict(list)
    for r in rows:
        by[r["ticker"]].append(r)
    fields = defaultdict(int)
    for r in rows:
        fields[r["field"]] += 1
    L = [f"# v2 vs data/companies ({TODAY})", "",
         "For every universe company, the fields where pipeline v2 and the old build differ by more than 5% (or one "
         "side is missing): revenue and capex of the latest fiscal year both have, total debt at the latest balance "
         "date both have, and shares (old: latest quarterly shares_outstanding; v2: the latest cover's classes added "
         "up, before class weights and ADS ratios). The parallel week is judged on this file: each row is either a "
         "v2 fix (say which in the review) or a v2 bug.", "",
         f"- companies: {len(kept)}; with a difference: {len(by)}",
         "- by field: " + ", ".join(f"{k} {v}" for k, v in sorted(fields.items())), "",
         "| ticker | field | period | old | v2 | diff % |", "|---|---|---|---|---|---|"]
    order = {c["ticker"]: i for i, c in enumerate(kept)}
    for t in sorted(by, key=lambda t: order.get(t, 1e9)):
        for r in by[t]:
            L.append(f"| {t} | {r['field']} | {r['period']} | {_fmt(r['old'])} | {_fmt(r['v2'])} | "
                     f"{'-' if r['pct'] is None else r['pct']} |")
    (OUT / "compare.md").write_text("\n".join(L) + "\n")


def write_report(report: dict, recs: list, excluded: list, changes: list, secs: float):
    n = len(recs)
    cov = {f: sum(1 for _, r in recs if f in r["ttm"]) for f in ("revenue", "net_income", "operating_cash_flow",
                                                                  "capex", "stock_comp", "shares_diluted")}
    debt = sum(1 for _, r in recs if r["balance"].get("total_debt") is not None)
    checks = [(c, c["mcap_check"]) for c, _ in recs if c["mcap_check"] != "ok"]
    ctypes = defaultdict(int)
    for ch in changes:
        ctypes[ch["type"]] += 1
    L = [f"# Pipeline v2 {TODAY}", "", f"- run: {secs / 60:.0f} min" + (f"; ONLY_TICKERS={','.join(ONLY)}" if ONLY else "")
         + (f"; LIMIT={LIMIT}" if LIMIT else ""),
         f"- universe: {n} companies >= ${UNIVERSE_MIN / 1e9:.1f}B, of which {sum(1 for c, _ in recs if (c['mcap_used'] or 0) >= SP_MIN)} "
         f">= ${SP_MIN / 1e9:.1f}B (S&P size)",
         "- dropped before the universe: " + ", ".join(f"{k} {v}" for k, v in sorted(report.get("dropped", {}).items())),
         f"- TTM coverage: " + ", ".join(f"{k} {v}/{n}" for k, v in cov.items()) + f"; total_debt {debt}/{n}",
         "- changes this run: " + (", ".join(f"{k} {v}" for k, v in sorted(ctypes.items())) or "none"),
         ""]
    L += lib.report_lines(report.get("library")) + ["", "## Excluded after the fundamentals", ""]
    L += [f"- {c['ticker']} {c['name']}: {why}" for c, why in excluded] or ["- none"]
    L += ["", "## Market value checks (not ok)", "", "| ticker | own | yahoo | used | check |", "|---|---|---|---|---|"]
    L += [f"| {c['ticker']} | {_fmt(c['mcap_own'])} | {_fmt(c['mcap_yahoo'])} | {_fmt(c['mcap_used'])} | {ck} |"
          for c, ck in checks]
    L += ["", "## Data flags", ""]
    L += [f"- {c['ticker']}: {', '.join(r['flags'])}" for c, r in recs if r["flags"]] or ["- none"]
    L += ["", "## Largest 25", "", "| ticker | market value | revenue TTM | capex TTM | total debt | shares |",
          "|---|---|---|---|---|---|"]
    for c, r in recs[:25]:
        L.append(f"| {c['ticker']} | {_fmt(c['mcap_used'])} | {_fmt((r['ttm'].get('revenue') or {}).get('val'))} | "
                 f"{_fmt((r['ttm'].get('capex') or {}).get('val'))} | {_fmt(r['balance'].get('total_debt'))} | "
                 f"{_fmt(c['shares_total'])} |")
    (OUT / "report.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    sys.exit(main())
