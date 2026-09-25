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
    lines, no OTC), not a partnership (L.P.), not a commodity trust (SIC 6221), revenue on file, and SEC figures
    that say the company COULD be S&P-sized, or is small but may be held by fmp (size_gate: public float >= $0.75B,
    or total assets >= $5B, or annual revenue >= $1B, or no public float reported in the last 18 months, e.g. a recent IPO). NO PRICES here (owner,
    25 Sep 2026: no Yahoo for anything; Robinhood is where we invest): fmp multiplies shares_total by its Robinhood
    price and draws S&P's $22.7B line itself. The rule missed none of the 420 companies in fmp's pool worth
    >= $15B on 25 Sep 2026 (a float-only line would have missed 8: BE, ARES, UI, RKT, SUNB, FOXA, ECHO, PPL).
    shares_total = the latest 10-Q/10-K COVER, every class added up (dei:EntityCommonStockSharesOutstanding by
    class in the filing's XBRL), with class weights (data/v2/share_class_weights.csv: Berkshire A = 1,500 B) and
    ADS ratios (data/v2/ads_ratio.csv). A split after the cover date is not applied here: fmp's Robinhood market
    value alarm catches it. Cover instances are fetched in parallel (6 threads, 8 requests/s in total) and cached
    in work/v2/xbrl across runs (actions/cache), so a normal night fetches only the new 10-Qs and 10-Ks.
 3. Filing library (library.py, 25 Sep 2026): the filings that matter (library.KEEP_FORMS) of the last 3 years and
    every document in them, as release assets on the `library` tag (one <cik>.tar.gz each), for the companies in
    data/v2/pool.txt (fmp's pool, one ticker per line) or, without that file, the universe companies with a public
    float >= $15B. The per-company filing lists come from submissions.zip (step 1): finding new filings is free.
 4. Fundamentals from companyfacts, point in time (each value keeps the form and the date it was first public, and
    the first-filed value when later restated), annual + quarterly + TTM, with the tag used per field. The latest
    10-K and 10-Q XBRL instances (from the library) fill a quarter companyfacts lacks (CNP's Q2) and supply the
    company's own capex tag when no us-gaap one exists (COP, NEE).
 5. data/v2/: companies/<cik>.json, events/<cik>.json and tickers.json (the old feed's shapes, for fmp's switch),
    universe.csv, changes.jsonl (appended), report.md, compare.md (v2 vs the old
    data/companies file: debt, capex, revenue and shares that differ by > 5%; the parallel week is judged on it).

Env: SEC_USER_AGENT (required), ONLY_TICKERS, LIMIT (largest n companies by public float), LIBRARY=true (run step 3; on demand only),
LIBRARY_MINUTES / MAX_NEW_FILINGS / LIBRARY_YEARS / LIBRARY_TAG (library.py), GH_TOKEN (to publish the library;
without it the assets stay in work/library/assets), SEC_MIN_GAP (seconds between SEC requests; 0.5 when sharing
the limit from a workstation), V2_OUT (default data/v2), V2_WORK (default work/v2).
"""
from __future__ import annotations

import copy
import csv
import datetime as dt
import gzip
import json
import os
import re
import sys
import threading
import time
import zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import build_sec_dataset as _old
import build_sec_events as _ev
import fetch_filings as ff
import library as lib

OUT = Path(os.environ.get("V2_OUT", "data/v2"))
WORK = Path(os.environ.get("V2_WORK", "work/v2"))
OLD = Path("data/companies")
CONF = Path("data/v2")                 # the two hand-kept CSVs (copied from fmp/owner/data), whatever V2_OUT is
STORE = Path(os.environ.get("FILINGS_STORE", "filings-store"))
# size_gate: SEC figures that say a company COULD be worth S&P's $22.7B (fmp draws the line with Robinhood prices)
# FLOAT_MIN 0.75B, not 2B (25 Sep 2026): fmp still HOLDS smaller companies bought before the S&P-size rule (LMAT 1.7B,
# USLM 1.07B, WINA 0.89B of float) and watch.py needs their 8-K feed; fmp's coverage.py blocks any name without a file.
FLOAT_MIN, ASSETS_MIN, REVENUE_MIN = 0.75e9, 5e9, 1e9
FLOAT_DAYS = 550                       # a public float filed longer ago than this counts as none
STALE_DAYS = 800                       # assets / revenue for a period ending longer ago than this are ignored
LIBRARY_FLOAT_MIN = 15e9               # library without data/v2/pool.txt: public float >= this
THREADS = 6                            # cover instances in flight at once, under build_sec_events' shared 8/s
ONLY = [t.strip().upper() for t in os.environ.get("ONLY_TICKERS", "").split(",") if t.strip()]
LIMIT = int(os.environ.get("LIMIT", "0") or 0)
LIBRARY = os.environ.get("LIBRARY", "false").strip().lower() in ("1", "true", "yes")   # on demand only
MIN_GAP = float(os.environ.get("SEC_MIN_GAP", "0") or 0)
TODAY = dt.date.today()
# The two bulk files live in DIFFERENT folders (the first v2 run asked for bulkdata/companyfacts.zip: 403).
BULK = {"submissions": "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip",
        "companyfacts": "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"}
FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A", "10-KT", "10-KT/A", "10-QT"}
PERIODIC = ("10-K", "10-Q", "10-KT", "10-QT")
COVER = "dei:EntityCommonStockSharesOutstanding"

if MIN_GAP > 0.12:                     # slower than build_sec_events' 8/s, for runs that share the SEC limit
    _raw_get, _last, _gap_lock = _ev.get, [0.0], threading.Lock()

    def _slow_get(url, *a, **k):
        with _gap_lock:
            time.sleep(max(0.0, MIN_GAP - (time.time() - _last[0])))
            _last[0] = time.time()
        return _raw_get(url, *a, **k)
    _ev.get = _slow_get


# ================================================================ tags
RFCWC = "RevenueFromContractWithCustomerExcludingAssessedTax"
RNFC = "RevenueNotFromContractWithCustomer"
REV_TOTAL = ["Revenues", "RegulatedAndUnregulatedOperatingRevenue"]
REV_OTHER = ["SalesRevenueNet", "SalesRevenueGoodsNet", "RevenuesNetOfInterestExpense", "RealEstateRevenueNet",
             "OperatingLeaseLeaseIncome", "OperatingLeasesIncomeStatementLeaseRevenue", "ElectricUtilityRevenue", "RegulatedOperatingRevenue",
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
              "PaymentsToDevelopRealEstateAssets", "PaymentsToAcquireEquipmentOnLease"],
    "stock_comp": ["ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"],
    "shares_diluted": ["WeightedAverageNumberOfDilutedSharesOutstanding",
                       "WeightedAverageNumberOfShareOutstandingBasicAndDiluted"],
}
AVERAGES = {"shares_diluted"}          # never differenced from year-to-date figures, never summed into a TTM
# the company's own capex concept (only when no us-gaap one covers the period): the largest per period, which is the
# total when a filer tags pieces too (NEE: FPL 8.7B inside 24.6B; DTE: utility 4.3B next to non-utility 0.1B)
EXT_CAPEX = re.compile(r"CapitalExpenditure|PlantAndEquipmentExpenditure|PaymentsToAcquireProductiveAssets|"
                       r"PaymentsToAcquirePropertyPlantAndEquipment|AdditionsToPropertyPlantAndEquipment|"
                       r"PaymentsForPropertyPlantAndEquipment|PropertySubjectToOrAvailableForOperatingLease|"
                       r"EquipmentOnLease|RentalEquipment", re.I)
EXT_CAPEX_NOT = re.compile(r"Planned|Estimat|Commitment|Incurred|NotYetPaid|Accrued|Future|AFUDC|Remainder|Year|"
                           r"Proceeds|Budget|Forecast|Guidance|Percent|Ratio|Business|Increase|Decrease|Payable|"
                           r"Change", re.I)
INSTANTS = {
    "cash": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
             "Cash"],
    "short_term_investments": ["ShortTermInvestments", "MarketableSecuritiesCurrent",
                               "AvailableForSaleSecuritiesDebtSecuritiesCurrent"],
    "cash_and_sti_tagged": ["CashCashEquivalentsAndShortTermInvestments"],
    "equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
}
DEBT_NONCURRENT = ["LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations", "LongTermDebt",
                   "LongTermNotesPayable", "SeniorLongTermNotes", "UnsecuredLongTermDebt", "OtherLongTermDebtNoncurrent",
                   "LongTermNotesAndLoans"]
DEBT_CURRENT_LTD = ["LongTermDebtCurrent", "LongTermDebtAndCapitalLeaseObligationsCurrent", "OtherLongTermDebtCurrent",
                    "NotesPayableCurrent", "SeniorNotesCurrent"]
DEBT_SHORT = ["ShortTermBorrowings", "CommercialPaper", "OtherShortTermBorrowings", "ShortTermBankLoansAndNotesPayable",
              "LoansPayableCurrent"]
LEASES = ["FinanceLeaseLiability", "FinanceLeaseLiabilityNoncurrent", "FinanceLeaseLiabilityCurrent"]
# unclassified balance sheets (REITs, insurers, homebuilders) tag one TOTAL instead of current / non-current
DEBT_COMBINED = ["DebtLongtermAndShorttermCombinedAmount", "DebtAndCapitalLeaseObligations",
                 "LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities"]
DEBT_NOTES = ["NotesPayable", "SeniorNotes", "UnsecuredDebt", "ConvertibleNotesPayable", "JuniorSubordinatedNotes"]
DEBT_EXTRA = ["LoansPayable", "SecuredDebt", "LineOfCredit"]          # term loans, mortgages, revolver: added to notes
DEBT_INSTRUMENTS = "DebtInstrumentCarryingAmount"      # the debt note's instruments added up: a tie-breaker only
DEBT_TAGS = ([DEBT_INSTRUMENTS] + DEBT_NONCURRENT + DEBT_CURRENT_LTD + DEBT_SHORT + ["DebtCurrent"] + LEASES + DEBT_COMBINED + DEBT_NOTES
             + DEBT_EXTRA)


# ================================================================ small helpers
def _d(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def _days(a: str, b: str) -> int:
    return (_d(b) - _d(a)).days


def _num(v):
    v = float(v)
    return int(v) if v.is_integer() else v


def _collapse(fs: list[dict], annual: bool = False) -> dict:
    """Every fact for one period -> one record: the latest-filed value, dated by the FIRST filing that showed that
    value (when it became public), plus the first-filed value and date when a later filing restated it. A full-year
    period (annual=True) is restated only by a 10-K / 10-K/A when one reported it: a later 10-Q's value for a whole
    year is a mis-tagged context, not a restatement (FIX's Q1 2026 10-Q put its quarter, 1.83B, on FY2025's dates,
    replacing the 10-K's 9.10B)."""
    fs = sorted(fs, key=lambda f: (f["filed"], f.get("accn") or ""))
    if annual and any(str(f.get("form", "")).startswith("10-K") for f in fs):
        fs = [f for f in fs if str(f.get("form", "")).startswith("10-K")]
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
    P = {k: dict(_collapse(v, annual=_days(k[0], k[1]) >= 300), start=k[0], end=k[1]) for k, v in per.items()}
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
    for e, r in list(q.items()):          # the same mislabel when the year IS on file (LHX FY2024: the 10-K's 21.3B
        a = ann.get(e)                    # sat on the Sep-Jan quarter context next to the real year): not a quarter
        if r.get("derived") or not a or not (a["val"] > 0 and r["val"] >= 0.9 * a["val"]):
            continue
        nine = [p for (s2, e2), p in P.items() if 250 <= _days(s2, e2) <= 290 and abs(_days(s2, a["start"])) <= 7
                and 0 < _days(e2, r["start"]) <= 7]
        if nine:
            q[e] = dict(r, val=_num(a["val"] - nine[0]["val"]), start=r["start"], derived=True,
                        note="year reported on a quarter context")
        else:
            del q[e]
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
    if RENT_PLUS_606 in c and not total:
        return RENT_PLUS_606
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


STMT_COST = ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold", "CostOfServices",
             "CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization"]
STMT_TOTAL_COST = ["CostsAndExpenses", "OperatingCostsAndExpenses", "BenefitsLossesAndExpenses", "OperatingExpenses"]
STMT_PROFIT = ["OperatingIncomeLoss",
               "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
               "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"]
STMT_TOL = 0.001
LEASE_INCOME = ["OperatingLeaseLeaseIncome", "OperatingLeasesIncomeStatementLeaseRevenue"]
RENT_PLUS_606 = "RevenueFromContractWithCustomerExcludingAssessedTax+OperatingLeaseLeaseIncome"
REVENUE_VERIFIED: dict = {}            # filled in main() from data/v2/revenue_verified.csv


def statement_revenue(picked: tuple, rs: dict, F: dict, verified: str | None = None) -> tuple[tuple, list]:
    """The fiscal year's revenue line checked against the company's own income-statement arithmetic: the line that
    equals gross profit + cost of revenue, or operating (or pre-tax) income + total costs, within 0.1%, is the
    statement's top line (WMB: 'Revenues' 11.95B, not the 14.9B contract line that nets out derivatives later; CNC
    194.8B incl. premium tax, not 174.6B; NTAP the 6.925B contract total, not the 6.237B 'Revenues' subset; FIX).
    With no such tie-out: two total tags that agree win over the contract line (SRE: Revenues = Regulated and
    unregulated = 13.70B, its reported figure, vs 12.42B), else choose_revenue's pick stands and, when the
    candidates differ by > 2%, the year is returned as unverified (flagged revenue_unverified_<end>: ARES, BAM)."""
    ann = dict(picked[0])
    unverified = []
    series = {}

    def year(tag, e):
        if tag not in F:
            return None
        if tag not in series:
            series[tag] = flow_series(F[tag])[0]
        r = series[tag].get(e)
        return r["val"] if r else None
    for e, cur in picked[0].items():
        c = {t: s[0][e] for t, s in rs.items() if e in s[0]}
        vals = {t: r["val"] for t, r in c.items()}
        sums = []
        gp = year("GrossProfit", e)
        sums += [gp + v for v in (year(t, e) for t in STMT_COST) if gp is not None and v is not None]
        for p in (year(t, e) for t in STMT_PROFIT):
            if p is not None:
                sums += [p + v for v in (year(t, e) for t in STMT_TOTAL_COST) if v is not None]
        ok = [t for t, v in vals.items() if any(abs(v - x) <= STMT_TOL * max(abs(v), 1) for x in sums)]
        if ok:
            if cur["tag"] not in ok:
                t = next((t for t in [RFCWC] + REV_TOTAL + REV_OTHER + [RNFC] if t in ok), ok[0])
                ann[e] = dict(c[t], tag=t, note="income-statement tie-out")
            continue
        totals = [t for t in REV_TOTAL if t in vals]
        if cur["tag"] == RFCWC and len(totals) >= 2 and abs(vals[totals[0]] - vals[totals[1]]) <= STMT_TOL * abs(vals[totals[0]]):
            ann[e] = dict(c[totals[0]], tag=totals[0], note="two total lines agree")
            continue
        t0 = ann[e]["tag"]
        if t0 in REV_TOTAL and RFCWC in vals and RNFC in vals and \
                abs(vals[RFCWC] + vals[RNFC] - vals[t0]) <= 0.02 * abs(vals[t0]):
            continue                                   # contract + non-contract = the total (COP, BRK-B): verified
        if verified and verified in vals:              # checked by hand against the reported figure
            if t0 != verified:
                ann[e] = dict(c[verified], tag=verified, note="hand-verified line (revenue_verified.csv)")
            continue
        lo, hi = min(vals.values()), max(vals.values())
        if len(vals) > 1 and hi > 0 and (hi - lo) / hi > 0.02 and cur["tag"] != RNFC and t0 != RENT_PLUS_606:
            unverified.append(e)
    return (ann, picked[1], picked[2]), unverified


SEG_ADDITIONS = "SegmentExpenditureAdditionToLongLivedAssets"


def segment_capex(picked: tuple, ser: dict, F: dict) -> tuple[tuple, list]:
    """The fiscal year's capex checked against the segment note's total additions to long-lived assets (ASC 280,
    tagged since 2024): among the chosen line, every other capex line, and every PAIR of lines, the one within 10% of
    the segment total wins (AEP: 8.45B construction + 3.45B other = 11.906B = the segment total; URI: 4.149B rental
    fleet + 0.379B other = 4.528B vs 4.568B). Segment additions are accrual-basis, hence 10%. With no line or pair
    that close, the pick stands, and one below 60% of the segment total is flagged capex_below_segment_<end>.
    A chosen pair becomes its own series ('a+b') so the quarters follow it."""
    if SEG_ADDITIONS not in F:
        return picked, []
    seg = flow_series(F[SEG_ADDITIONS], additive=False)[0]
    ann, flags = dict(picked[0]), []
    for e, cur in picked[0].items():
        s = seg.get(e)
        if not s or not s["val"] or s["val"] <= 0:
            continue
        target = s["val"]
        c = {t: sr[0][e] for t, sr in ser.items() if e in sr[0] and sr[0][e]["val"] and sr[0][e]["val"] > 0}
        opts = [((t,), r["val"]) for t, r in c.items()]
        ts = sorted(c)
        opts += [((a, b), c[a]["val"] + c[b]["val"]) for i, a in enumerate(ts) for b in ts[i + 1:]]
        near = [(abs(v - target) / target, k, v) for k, v in opts if abs(v - target) <= 0.10 * target]
        if near:
            _, k, v = min(near, key=lambda x: (x[0], len(x[1])))
            if k != (cur["tag"],):
                if len(k) == 1:
                    ann[e] = dict(c[k[0]], tag=k[0], note="segment additions tie-out")
                else:
                    key = "+".join(k)
                    if key not in ser:
                        ser[key] = _sum_series(ser[k[0]], ser[k[1]])
                    if e in ser[key][0]:
                        ann[e] = dict(ser[key][0][e], tag=key, note="segment additions tie-out")
        elif cur["val"] < 0.6 * target:
            flags.append((f"capex_below_segment_{e}", e))
    return (ann, picked[1], picked[2]), flags


def same_line_as_year(picked: tuple, series: dict) -> tuple:
    """Quarters and year-to-date periods take the revenue (or capex) line chosen for their fiscal year when the filer tagged it
    for that period too. choose_revenue() decides each period alone, and a quarter can lack the tag that made the
    year's choice (COP tags RevenueNotFromContractWithCustomer only annually, so its quarters fell back to the ASC 606
    line: 51.8B over four quarters against 58.9B for the year, and the quarters no longer added up). A quarter after
    the latest fiscal year follows that year's line."""
    ann = sorted(picked[0].items())                              # [(end, row)]
    out = (picked[0], dict(picked[1]), dict(picked[2]))
    for k in (1, 2):
        for e, r in picked[k].items():
            yr = next((a for ae, a in ann if a.get("start") and a["start"] <= e <= ae), None)
            if yr is None and ann and ann[-1][0] < e:
                yr = ann[-1][1]
            t = (yr or {}).get("tag")
            if not t or t == r["tag"]:
                continue
            same = [t] + [x for x, sr in series.items() if x != t and yr["end"] in sr[0]      # SRE: 'Revenues' has no
                          and abs(sr[0][yr["end"]]["val"] - yr["val"]) <= STMT_TOL * abs(yr["val"] or 1)]  # quarters,
            for x in same:                                                  # its equal total line does
                cand = series.get(x, ({}, {}, {}))[k].get(e)
                if cand and cand.get("start") == r.get("start"):
                    if x != r["tag"]:
                        out[k][e] = dict(cand, tag=x)
                    break
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
        # LongTermDebt includes its current portion by definition, but some filers tag it without (DRI: 1.638B +
        # 0.694B current = 2.33B, and its instruments add up to 2.19B). The debt note's total decides which.
        ins = v.get(DEBT_INSTRUMENTS)
        if not (ins and abs(nonc + ltc - ins) < abs(nonc - ins)):
            nonc -= ltc
        used.append(lt)
    if v.get("DebtCurrent") is not None:
        cur, cur_tags = v["DebtCurrent"], ["DebtCurrent"]
    else:
        stb = v.get("ShortTermBorrowings")
        paper_tags = [t for t in ("CommercialPaper", "OtherShortTermBorrowings", "ShortTermBankLoansAndNotesPayable",
                                  "LoansPayableCurrent") if v.get(t) is not None]           # distinct lines: added
        paper = sum(v[t] for t in paper_tags) if paper_tags else None
        st_opts = [(x, t) for x, t in ((stb, ["ShortTermBorrowings"]), (paper, paper_tags)) if x is not None]
        st, st_tags = max(st_opts, key=lambda x: x[0]) if st_opts else (None, [])
        only_paper = stb is None or (paper is not None and stb <= paper * 1.05)
        if ltc is not None and st is not None:
            # A short-term line of 100-110% of the current portion already holds it (AMAT: 1.299B vs 1.199B; Cintas
            # 2020: equal): count once. Otherwise they are separate borrowings and add up (the Sep 2026 audit: EXC,
            # CBRE; and MSFT, SHW, WMT against their stated totals). The old 'take the larger' rule dropped the current
            # portion whenever a ShortTermBorrowings line existed.
            if not only_paper and ltc <= st <= 1.10 * ltc:
                cur, cur_tags = st, st_tags
            else:
                cur, cur_tags = ltc + st, [lt] + st_tags
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


def unclassified_debt(v: dict) -> dict | None:
    """Total debt of a company that does not split it into current and non-current (REITs, insurers, homebuilders,
    TEVA): a combined-total tag when there is one (VTR, KVUE, PGR, TRV, AFL), else the largest notes tag (the notes
    tags overlap: TEVA's SeniorNotes 16.65B vs its 12.09B non-current + 4.5B current) plus term loans, mortgages,
    the revolver and commercial paper / short-term borrowings (O: 25.09B notes + 2.76B term loans + 1.40B paper).
    Used only when assemble_debt finds one side or nothing."""
    comb = next((t for t in DEBT_COMBINED if v.get(t)), None)
    if comb:
        return {"total_debt": _num(v[comb]), "debt_noncurrent": None, "debt_current": None, "finance_leases": None,
                "tags": [comb], "both_sides": True}
    notes = [t for t in DEBT_NOTES if v.get(t)]
    if not notes:
        return None
    base = max(notes, key=lambda t: v[t])
    parts = [base] + [t for t in DEBT_EXTRA if v.get(t)]
    st = max(((v[t], t) for t in DEBT_SHORT if v.get(t)), default=None)
    if st:
        parts.append(st[1])
    return {"total_debt": _num(sum(v[t] for t in parts)), "debt_noncurrent": None, "debt_current": None,
            "finance_leases": None, "tags": parts, "both_sides": True}


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


INVARIANT_YEARS = 3
DUE_12M = "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths"
DEBT_STALE_DAYS = 200                  # balance total_debt from an earlier date at most this much older


def invariant_flags(annual: list[dict], quarterly: list[dict]) -> list[str]:
    """Loud checks on the finished rows, so a wrong number is flagged instead of passed on: a quarter bigger than
    its whole fiscal year (a mislabelled context), and four quarters of a fiscal year that do not add up to it
    (within 2%) for revenue, operating cash flow and capex. The last INVARIANT_YEARS fiscal years only (what the
    screen reads; older gaps are mostly restatements, which point-in-time values keep on purpose); the quarter-vs-year
    size check skips operating cash flow, whose quarters can swing past the year (JPM, BA)."""
    out = []
    recent = sorted(a["end"] for a in annual)[-INVARIANT_YEARS:]
    for f in ("revenue", "operating_cash_flow", "capex"):
        for a in annual:
            if a.get(f) is None or not a.get("start") or a["end"] not in recent:
                continue
            qs = [r for r in quarterly if r.get(f) is not None and a["start"] <= r["end"] <= a["end"]
                  and r.get("start", "") >= a["start"]]
            if f != "operating_cash_flow" and any(abs(r[f]) > abs(a[f]) * 1.02 and abs(a[f]) > 0 for r in qs):
                out.append(f"quarter_exceeds_year_{f}_{a['end']}")
            if len(qs) == 4 and abs(sum(r[f] for r in qs) - a[f]) > 0.02 * max(abs(a[f]), 1):
                out.append(f"quarters_off_year_{f}_{a['end']}")
    return out


def load_revenue_verified(path: Path = CONF / "revenue_verified.csv") -> dict:
    """{ticker: tag} checked by hand against the company's reported revenue when no tie-out exists (evidence column)."""
    if not path.exists():
        return {}
    return {r["ticker"]: r["tag"] for r in csv.DictReader(path.open())}


def fundamentals(F: dict, verified_revenue: str | None = None) -> dict:
    """Annual and quarterly rows, TTM and the latest balance sheet from load_facts() (+ merge_instance()) output.
    Each row: {end, start, <field>: value, ..., src: {<field>: {tag, form, filed, accn[, first_val, first_filed,
    derived]}}}. Debt pieces sit in the row next to total_debt, their tags in src.total_debt.tags."""
    flows = {}
    capex_flags: list = []
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
    lease = next((t for t in LEASE_INCOME if t in rs), None)
    if lease and RFCWC in rs and not any(t in rs for t in REV_TOTAL):
        rs[RENT_PLUS_606] = _sum_series(rs[RFCWC], rs[lease])      # a REIT with no total line: rent + other revenue
    picked = _pick_per_period(rs, lambda c: choose_revenue(c, bank))
    unverified = []
    if not bank:
        picked, unverified = statement_revenue(picked, rs, F, verified_revenue)
    flows["revenue"] = same_line_as_year(picked, rs)
    for field, tags in FLOWS.items():
        ser = {t: flow_series(F[t], additive=field not in AVERAGES) for t in tags if t in F}
        if field == "capex":
            ser.update({t: flow_series(fs) for t, fs in F.items() if t.startswith("ext:")})
            picked, cx_flags = segment_capex(_pick_per_period(ser, choose_capex), ser, F)
            capex_flags += cx_flags
            flows[field] = same_line_as_year(picked, ser)
        else:
            flows[field] = _pick_per_period(ser, lambda c, tags=tags: next((t for t in tags if t in c), None))
    inst = {t: instant_series(F[t]) for t in set(DEBT_TAGS) | {t for ts in INSTANTS.values() for t in ts} | {DUE_12M}
            if t in F}

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
        comb = vals.get(DEBT_COMBINED[0])
        if not bank and comb and comb["val"] and debt and debt["both_sides"] and \
                comb["val"] > debt["total_debt"] * 1.02:        # the company's own stated total (SHW 12.07B: the
            debt = dict(debt, total_debt=_num(comb["val"]),     # PepsiCo rule dropped its 1.5B current portion)
                        tags=debt["tags"] + [DEBT_COMBINED[0]])
        if not bank and (not debt or not debt["both_sides"]):         # banks: debt is a different animal
            alt = unclassified_debt({t: r["val"] for t, r in vals.items()})
            if alt and (not debt or alt["total_debt"] > (debt["total_debt"] or 0) * 1.05):
                debt = alt
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
    # debt from the latest date that has it (ORCL's Aug 2026 10-Q tags only the current notes: its May 10-K's
    # $129.5B is the latest total), dated, and only within DEBT_STALE_DAYS of the balance date
    debt_rows = [r for r in annual + quarterly if r.get("total_debt") is not None]
    if latest and latest.get("total_debt") is None and debt_rows:
        d = max(debt_rows, key=lambda r: r["end"])
        if _days(d["end"], latest["end"]) <= DEBT_STALE_DAYS:
            bal.update({k: d[k] for k in ("total_debt", "debt_noncurrent", "debt_current", "finance_leases") if k in d})
            bal["debt_end"] = d["end"]
            latest = dict(latest, src=dict(latest.get("src", {}), total_debt=d.get("src", {}).get("total_debt", {})))
    tags = {f: sorted({r["tag"] for k in (0, 1, 2) for r in ser[k].values()}) for f, ser in flows.items()}
    flags = [f"no_{f}" for f in ("revenue", "operating_cash_flow", "capex") if f not in ttm]
    newest = max([r["end"] for r in annual + quarterly] or [""])
    for f, v in ttm.items():                         # a field its filer stopped tagging (MTB capex after 2023)
        if newest and v.get("end") and _days(v["end"], newest) > 200:
            v["stale"] = True
            flags.append(f"stale_{f}")
    if not bal.get("total_debt") and bal:
        flags.append("no_debt_tagged")
    flags += invariant_flags(annual, quarterly)
    recent_ends = {r["end"] for r in annual[-INVARIANT_YEARS:]}
    flags += [f for f, e in capex_flags if e in recent_ends]
    flags += [f"revenue_unverified_{e}" for e in unverified if e in {r["end"] for r in annual[-INVARIANT_YEARS:]}]
    de = bal.get("debt_end") or bal.get("end")                  # CAT: the current portion of long-term debt is
    due = inst.get(DUE_12M, {}).get(de, {}).get("val")          # tagged only by segment; its maturity table says
    lsrc = (latest.get("src") or {}).get("total_debt") or {}    # $7.1B falls due within 12 months
    if bal.get("total_debt") is not None and due and due > 0 and not set(lsrc.get("tags", [])) & set(DEBT_CURRENT_LTD) \
            and "DebtCurrent" not in lsrc.get("tags", []) and (bal.get("debt_current") or 0) < due:
        flags.append(f"current_ltd_untagged_{due / 1e9:.1f}B")
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
    divided by the ADS ratio when the listing is an ADS (a split after the cover date: fmp's Robinhood alarm)."""
    if not by_class:
        return None
    n = 0.0
    for cls, v in by_class.items():
        w = next((w for m, w in weights.get(ticker, []) if m.lower() in cls.lower()), 1.0)
        n += v * w
    return n * (split or 1.0) / ads.get(ticker, 1.0)


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
            "latest": latest_periodic(sub), "tenks": sum(f in ("10-K", "10-KT") for f in r.get("form", []))}, ""


def cf_shares(cf: dict) -> float | None:
    """companyfacts' latest cover count (ONE class for multi-class filers: only a pre-screen)."""
    fs = [f for f in (cf or {}).get("facts", {}).get("dei", {}).get("EntityCommonStockSharesOutstanding", {})
          .get("units", {}).get("shares", []) if f.get("val")]
    if not fs:
        return None
    last = max(f["end"] for f in fs)
    return float(max(f["val"] for f in fs if f["end"] == last))


def _latest(fs: list[dict], annual: bool = False) -> tuple[float | None, str | None, str | None]:
    """(value, period end, filed) of the latest fact; annual=True keeps full-year durations only."""
    fs = [f for f in fs if f.get("val") is not None and f.get("end")
          and (not annual or f.get("start") and 330 <= _days(f["start"], f["end"]) <= 400)]
    if not fs:
        return None, None, None
    f = max(fs, key=lambda f: (f["end"], f.get("filed", "")))
    return float(f["val"]), f["end"], f.get("filed")


def size_signals(cf: dict) -> dict:
    """The SEC figures size_gate reads: public float (dei, the 10-K cover), total assets, annual revenue."""
    facts = (cf or {}).get("facts", {})
    g = facts.get("us-gaap", {})
    usd = lambda d, t: d.get(t, {}).get("units", {}).get("USD", [])            # noqa: E731
    fl, fl_end, fl_filed = _latest(usd(facts.get("dei", {}), "EntityPublicFloat"))
    recent = lambda x: x[0] if x[1] and _days(x[1], str(TODAY)) <= STALE_DAYS else None   # noqa: E731
    assets = recent(_latest(usd(g, "Assets")))
    revs = [recent(_latest(usd(g, t), annual=True)) for t in [RFCWC, *REV_TOTAL, *REV_OTHER]]
    rev = max((v for v in revs if v), default=None)
    return {"public_float": fl, "float_date": fl_end, "float_filed": fl_filed, "assets": assets, "revenue": rev}


def size_gate(sig: dict, tenks: int = 0, today: dt.date = TODAY) -> str | None:
    """Why the company could be S&P-sized ('float' / 'assets' / 'revenue' / 'no_float'), or None. No prices."""
    fresh = sig.get("public_float") and sig.get("float_filed") and _days(sig["float_filed"], str(today)) <= FLOAT_DAYS
    if fresh and sig["public_float"] >= FLOAT_MIN:
        return "float"
    if (sig.get("assets") or 0) >= ASSETS_MIN:
        return "assets"
    if (sig.get("revenue") or 0) >= REVENUE_MIN:
        return "revenue"
    if not fresh and tenks <= 1:                    # a recent IPO: no float on a 10-K yet
        return "no_float"
    return None


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


BIG_FLOAT = 15e9                       # public float above which leaving the universe is an ALARM (XOM-type drops)
INTEREST_NO_DEBT = 50e6                # annual interest expense above which "no debt found" means debt was missed


def alarms(recs: list, changes: list) -> list[str]:
    """The report's ALARMS section, at the top: things that must not happen silently. A big company leaving the
    universe; a big company (float / assets gate) whose file is flagged no_revenue, short_history or build_error; and
    'interest_but_no_debt' (the company pays interest, v2 found no debt: F, BRK-B, KKR)."""
    out = [f"- BIG COMPANY LEFT THE UNIVERSE: {ch['ticker']} (cik {ch['cik']}, float {ch['public_float'] / 1e9:,.1f}B)"
           for ch in changes if ch.get("type") == "ALARM_big_company_left"]
    for c, r in recs:
        bad = [f for f in r.get("flags", []) if f.startswith(("short_history", "build_error"))]
        if bad and c.get("gate") in ("float", "assets"):
            out.append(f"- {c['ticker']}: {', '.join(bad)} (a big company: fix or add to data/v2/predecessors.csv)")
    # big companies with NO revenue at all: mostly funds, trusts and pre-revenue companies (ARCC, NLY, SPCX), but a
    # company that moved to a new SEC registrant looks exactly like this (XOM before predecessors.csv): one line to scan
    norev = sorted(c["ticker"] for c, r in recs if "no_revenue" in r.get("flags", []) and c.get("gate") in ("float", "assets"))
    if norev:
        out.append(f"- big companies with no revenue ({len(norev)}; funds / pre-revenue are expected, anything you "
                   f"recognise as an operating company is a drop): {', '.join(norev)}")
    cur = sorted(f"{c['ticker']} ({f[11:]})" for c, r in recs for f in r.get("flags", []) if f.startswith("reports_in_")
                 and c.get("gate") in ("float", "assets"))
    if cur:
        out.append(f"- big companies reporting in another currency (not read): {', '.join(cur)}")
    for flag, what in (("debt_too_small_for_interest", "interest is over 25% of the debt v2 found"),):
        hit = [c["ticker"] for c, r in recs if flag in r.get("flags", [])]
        if hit:
            out.append(f"- {flag}: {len(hit)} companies ({what}): {', '.join(hit)}")
    n = sum(1 for _, r in recs if "interest_but_no_debt" in r.get("flags", []))
    if n:
        out.append(f"- interest_but_no_debt: {n} companies pay interest but v2 found no debt: "
                   + ", ".join(c["ticker"] for c, r in recs if "interest_but_no_debt" in r.get("flags", [])))
    return out or ["- none"]


def universe_changes(prev: dict, new: dict) -> list[dict]:
    """prev/new: {cik: universe row}. Entering and leaving (S&P's $22.7B line is fmp's, on Robinhood prices)."""
    out = []
    for cik in sorted(set(prev) | set(new)):
        p, n = prev.get(cik), new.get(cik)
        row = {"date": str(TODAY), "cik": int(cik), "ticker": (n or p)["ticker"]}
        if p is None:
            out.append(dict(row, type="entered_universe", gate=n.get("gate")))
        elif n is None:
            fl = float(p.get("public_float") or 0)
            out.append(dict(row, type="left_universe", public_float=fl or None))
            if fl >= BIG_FLOAT:                 # a company this big does not shrink out of the universe: an alarm
                out.append(dict(row, type="ALARM_big_company_left", public_float=fl))
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
    na = {r["end"]: r for r in new.get("v2_annual", [])}
    both = sorted(set(oa) & set(na))
    if both:
        e = both[-1]
        for f in ("revenue", "capex"):
            add(f, e, oa[e].get(f), na[e].get(f))
    oq = {r.get("period_end"): r for r in old.get("quarterly", []) + old.get("annual", [])
          if r.get("period_end") and r.get("total_debt") is not None}
    nq = {r["end"]: r for r in new.get("v2_quarterly", []) + new.get("v2_annual", []) if r.get("total_debt") is not None}
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
            tp = OUT / "tickers.json" if (OUT / "tickers.json").exists() else CONF / "tickers.json"
            tick = json.loads((tp if tp.exists() else Path("data/tickers.json")).read_text())   # the SEC's current map
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
        """companyfacts, merged with a predecessor filer's (data/v2/predecessors.csv) when the company moved to a
        new SEC registrant: XOM's holding company (2115436, since Jul 2026) has none of Exxon Mobil Corp's (34088)
        history, so on its own it looked like a shell and was dropped."""
        cf = self._facts(cik)
        pred = PREDECESSORS.get(int(cik))
        if pred:
            old = self._facts(pred)
            if old:
                cf = merge_facts_docs(old, cf)
        return cf

    def _facts(self, cik: int) -> dict | None:
        if self.only is not None:
            return self._api(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json", f"cf_{cik}.json")
        try:
            return json.loads(self.cf_zip.read(f"CIK{cik:010d}.json"))
        except KeyError:
            return None


PREDECESSORS: dict = {}                # {cik: predecessor cik}, from data/v2/predecessors.csv in main()


def load_predecessors(path: Path = CONF / "predecessors.csv") -> dict:
    if not path.exists():
        return {}
    return {int(r["cik"]): int(r["predecessor_cik"]) for r in csv.DictReader(path.open())}


def merge_facts_docs(old: dict, new: dict | None) -> dict:
    """Two companyfacts documents as one: every fact of both (the predecessor's first); _collapse sorts out periods
    both reported (the later filing wins, as for any restatement)."""
    out = {"cik": (new or old).get("cik"), "entityName": (new or old).get("entityName"), "facts": {}}
    for doc in (old, new or {}):
        for ns, tags in (doc.get("facts") or {}).items():
            for tag, v in tags.items():
                dst = out["facts"].setdefault(ns, {}).setdefault(tag, {"units": {}})
                for u, fs in v.get("units", {}).items():
                    dst["units"].setdefault(u, []).extend(fs)
    return out


def currency_note(cf: dict | None) -> str | None:
    """'reports_in_CAD' (etc.) when the revenue lines are tagged only in a non-USD currency (ENB, CP): v2 reads USD."""
    g = ((cf or {}).get("facts") or {}).get("us-gaap") or {}
    units = {u for t in [RFCWC] + REV_TOTAL + REV_OTHER if t in g for u in g[t].get("units", {})}
    if units and "USD" not in units:
        return f"reports_in_{sorted(units)[0]}"
    return None


def _cached(cik: int, accn: str) -> Path | None:
    for p in (STORE / str(cik) / f"{accn}_xbrl.json.gz", WORK / "xbrl" / f"{cik}_{accn}.json.gz"):
        if p.exists():
            return p
    return None


def prefetch(pairs: set) -> int:
    """Fetch the (cik, accn) instances not cached yet, THREADS at a time under the shared 8 requests/s."""
    todo = sorted(p for p in pairs if not _cached(*p))
    with ThreadPoolExecutor(THREADS) as ex:
        list(ex.map(lambda p: instance(*p), todo))
    return len(todo)


def prune_cache(keep: set) -> int:
    """Drop cached instances no universe company needs any more (the cache stays the size of the universe)."""
    n = 0
    for p in (WORK / "xbrl").glob("*.json.gz"):
        cik, _, accn = p.name[:-len(".json.gz")].partition("_")
        if (int(cik), accn) not in keep:
            p.unlink(); n += 1
    return n


def instance(cik: int, accn: str) -> dict | None:
    """A filing's XBRL facts: from the library when it has them, else work/v2/xbrl (kept across runs by the
    workflow's cache), else fetched (2 requests)."""
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


# ================================================================ main
def build_universe(src: Sources, weights: dict, ads: dict, report: dict) -> list[dict]:
    cands, dropped, gates = [], defaultdict(int), defaultdict(int)
    for sub in src.submissions():
        c, why = candidate(sub)
        if c:
            c["_two"] = latest_two(sub)                             # not the whole record: thousands are held
            cands.append(c)
        else:
            dropped[why] += 1
    print(f"candidates: {len(cands)} US 10-Q filers with a listed common ticker", flush=True)
    uni = []
    for c in cands:
        cf = src.facts(c["cik"])
        c["size"] = size_signals(cf)
        c["gate"] = size_gate(c["size"], c["tenks"]) if not ONLY else "only"
        if not c["gate"]:
            dropped["too_small_sec_figures"] += 1
            continue
        c["cf_shares"] = cf_shares(cf)
        gates[c["gate"]] += 1
        uni.append(c)
    uni.sort(key=lambda c: -(c["size"]["public_float"] or c["size"]["assets"] or 0))
    if LIMIT:
        uni = uni[:LIMIT]
    need = {(c["cik"], f["accn"]) for c in uni for f in c["_two"] + ([c["latest"]] if c["latest"] else [])}
    t = time.time()
    report["instances_fetched"] = prefetch(need)
    report["instances_needed"] = len(need)
    print(f"cover instances: {report['instances_fetched']} fetched of {len(need)} needed ({time.time() - t:.0f}s)",
          flush=True)
    if not LIMIT and not ONLY:
        report["instances_pruned"] = prune_cache(need)
    for c in uni:
        cov_date, classes, cov = None, {}, c["latest"]
        if cov:
            x = instance(c["cik"], cov["accn"])
            cov_date, classes = cover_classes(x) if x else (None, {})
        c["cover_date"], c["classes"] = cov_date, classes
        c["shares_cover"] = sum(classes.values()) if classes else None
        c["shares_total"] = shares_total(classes, c["ticker"], weights, ads)
        if c["shares_total"] is None and c["cf_shares"]:
            c["shares_total"] = c["cf_shares"] / ads.get(c["ticker"], 1.0)
            c["cover_note"] = "cover unreadable: companyfacts shares"
    report["dropped"] = dict(dropped)
    report["gates"] = dict(gates)
    return uni


# The nightly 8-K feed (data/v2/events) that watch.py checks held names against. Since 25 Sep 2026 it also carries the
# filings that signal trouble or a deal (owner: "yeah add them"): late filings, activist stakes, tender offers, merger
# and proxy-fight proxies, going-private, controlled-company actions, spin-off registrations, going dark, delisting.
# Metadata from submissions.zip only: no extra requests.
EVENT_FORMS = {"8-K", "8-K/A", "10-K", "10-K/A", "10-Q", "10-Q/A", "10-KT", "10-QT",
               "NT 10-K", "NT 10-Q", "NT 10-K/A", "NT 10-Q/A",
               "SC 13D", "SC 13D/A", "SCHEDULE 13D", "SCHEDULE 13D/A",
               "SC TO-T", "SC TO-T/A", "SC TO-I", "SC TO-I/A", "SC 14D9", "SC 14D9/A",
               "S-4", "S-4/A", "425", "DEFM14A", "PREM14A", "PREC14A", "DEFC14A", "DFAN14A",
               "SC 13E3", "SC 13E3/A", "DEF 14C", "PRE 14C", "DEFM14C", "PREM14C",
               "10-12B", "10-12B/A", "10-12G", "10-12G/A", "15-12B", "15-12G", "15-15D", "25-NSE", "25"}
EVENT_DAYS = 400


def events_record(sub: dict, cik: int, today: dt.date = TODAY) -> dict:
    """data/events/<cik>.json in the old feed's shape (what fmp's screen / watch / shares read): the 8-K / 10-K / 10-Q
    filings of the last EVENT_DAYS with their 8-K item codes, straight from the submissions JSON (no requests). The
    old feed's `exhibits` list is not rebuilt (fmp does not read it; the library holds every exhibit)."""
    r = sub.get("filings", {}).get("recent", {})
    since = str(today - dt.timedelta(days=EVENT_DAYS))
    ev = []
    for f, d, a, it, rd, doc in zip(r.get("form", []), r.get("filingDate", []), r.get("accessionNumber", []),
                                    r.get("items", []) or [""] * len(r.get("form", [])),
                                    r.get("reportDate", []) or [""] * len(r.get("form", [])),
                                    r.get("primaryDocument", []) or [""] * len(r.get("form", []))):
        if f in EVENT_FORMS and d >= since:
            ev.append(dict(accession=a, date=d, form=f, items=[x.strip() for x in (it or "").split(",") if x.strip()],
                           period=rd or d, url=f"https://www.sec.gov/Archives/edgar/data/{cik}/{a.replace('-', '')}/{doc}"))
    ev.sort(key=lambda e: e["date"], reverse=True)
    return dict(cik=cik, name=sub.get("name"), sic=sub.get("sicDescription"), sic_code=sub.get("sic"),
                tickers=sub.get("tickers", []), events=ev)


def write_events(uni: list[dict], src) -> int:
    d = OUT / "events"
    d.mkdir(parents=True, exist_ok=True)
    keep, n = set(), 0
    for c in uni:
        sub = src.submission(int(c["cik"]))
        if not sub:
            continue
        (d / f"{c['cik']}.json").write_text(json.dumps(events_record(sub, int(c["cik"])), indent=1) + "\n")
        keep.add(f"{c['cik']}.json"); n += 1
    for p in d.glob("*.json"):                          # companies that left the universe
        if p.name not in keep:
            p.unlink()
    return n


def write_tickers() -> int:
    """data/v2/tickers.json in the old shape {TICKER: {cik, name}} from the SEC's company_tickers.json (1 request)."""
    r = _ev.get("https://www.sec.gov/files/company_tickers.json")
    if r is None:
        return 0
    out = {}
    for v in r.json().values():
        out.setdefault(v["ticker"].upper(), dict(cik=int(v["cik_str"]), name=v["title"]))
    (OUT / "tickers.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return len(out)


def library_companies(uni: list[dict]) -> list[dict]:
    """fmp's pool (data/v2/pool.txt, one ticker per line) when that file exists, else public float >= $15B."""
    p = CONF / "pool.txt"
    if p.exists():
        want = {t.strip().upper().replace(".", "-") for t in p.read_text().split() if t.strip()}
        return [c for c in uni if c["ticker"] in want]
    return [c for c in uni if (c["size"]["public_float"] or 0) >= LIBRARY_FLOAT_MIN]


def run_library(uni: list[dict], changes: list, src: Sources) -> dict:
    """library.run for library_companies; its new-filing entries join data/v2/changes.jsonl with source=library."""
    lib_changes: list = []
    stats = lib.run([dict(cik=c["cik"], ticker=c["ticker"], name=c["name"], mcap=c["size"]["public_float"])
                     for c in library_companies(uni)],
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
    fund = fundamentals(F, REVENUE_VERIFIED.get(c["ticker"]))
    fund = {("v2_" + k if k in ("annual", "quarterly", "tags_used") else k): v for k, v in fund.items()}
    lf = c["latest"] or {}
    return {**legacy(cf, fund), "cik": c["cik"], "ticker": c["ticker"], "tickers": c["tickers"], "name": c["name"], "sic": c["sic"],
            "sic_description": c["sic_description"], "fiscal_year_end": c["fye"],
            "latest_filing": lf, "instances_merged": merged,
            "market": {"shares_total": c["shares_total"], "shares_cover": c["shares_cover"], "classes": c["classes"],
                       "cover_date": c["cover_date"], "cover_accession": lf.get("accn"),
                       "ads_ratio": None, "note": c.get("cover_note"), "size_gate": c["gate"], **c["size"]},
            **fund}


# ================================================================ the old file's fields (fmp's switch)
OVERLAY = {"revenue": "revenue", "capex": "capex", "total_debt": "total_debt", "debt_noncurrent": "lt_debt_noncurrent",
           "debt_current": "debt_current"}
FILL = {"net_income": "net_income", "operating_cash_flow": "operating_cash_flow", "stock_comp": "stock_comp"}


def overlay(old_rows: list[dict], v2_rows: list[dict], annual: bool) -> list[dict]:
    """v2's corrected values written over the old build's rows of the same period end: revenue, capex and debt
    always (the fields v2 exists to fix), net income / operating cash flow / stock comp only where the old row has
    none. <field>_as_filed follows (screen.py's val() prefers it): v2's first-filed value when it was restated. An
    annual period only v2 has (LHX FY2025) is added as a row. Returns [{period, field, old, v2}] for what changed."""
    by_end = {r.get("period_end"): r for r in old_rows if r.get("period_end")}
    shift = next((r["fiscal_year"] - int(r["period_end"][:4]) for r in old_rows
                  if r.get("fiscal_year") and r.get("period_end")), 0)
    fixes = []
    for v in v2_rows:
        e = v["end"]
        row = by_end.get(e)
        if row is None:
            if not annual:
                continue
            row = {"period_end": e, "fiscal_year": int(e[:4]) + shift, "form": "10-K", "added_by": "v2"}
            old_rows.append(row); by_end[e] = row
        for vf, of in list(OVERLAY.items()) + list(FILL.items()):
            val = v.get(vf)
            if val is None or (vf in FILL and row.get(of) is not None):
                continue
            src = (v.get("src") or {}).get(vf) or {}
            if row.get(of) != val:
                fixes.append({"period": e, "field": of, "old": row.get(of), "v2": val})
            row[of] = val
            if src.get("filed"):
                row[of + "_filed"] = src["filed"]
            if (of + "_as_filed") in row or src.get("first_val") is not None:
                row[of + "_as_filed"] = src.get("first_val", val)
                row[of + "_as_filed_filed"] = src.get("first_filed", src.get("filed"))
    old_rows.sort(key=lambda r: r.get("period_end", ""))
    return fixes


def legacy(cf: dict | None, fund: dict) -> dict:
    """The old data/companies file's keys (sec_name, annual, quarterly, checks, splits, annual_coverage, tags_used),
    built by build_sec_dataset from the same companyfacts, with v2's corrections overlaid (v2_fixes lists them).
    fmp's screen.py, mathprice.py and the reads use ~45 fields of that shape (buybacks, dividends, goodwill, interest,
    deposits and insurance lines for financials, net_income_parent ...); v2's own rows stay in v2_annual /
    v2_quarterly. The checks are recomputed after the overlay."""
    if not cf:
        return {"annual": [], "quarterly": [], "checks": {}, "v2_fixes": []}
    norm = _old.normalise_company(cf)
    ann, qtr = norm["annual"], norm["quarterly"]
    chk = lambda: _old.data_checks(ann, qtr, norm["tags_used"], norm.get("_top_line"))   # noqa: E731
    before, q0 = _off(chk()), copy.deepcopy(qtr)
    fixes = [dict(f, rows="annual") for f in overlay(ann, fund.get("v2_annual", []), True)]
    fixes += [dict(f, rows="quarterly") for f in overlay(qtr, fund.get("v2_quarterly", []), False)]
    notes = []
    broke = _off(chk()) - before
    if broke:                       # v2's quarters no longer add up to the year (COP: a different revenue line per
        keep = {r.get("period_end"): r for r in q0}            # quarter): those quarterly fields stay the old build's
        for r in qtr:
            o = keep.get(r.get("period_end"), {})
            for f in broke:
                for k in (f, f + "_as_filed", f + "_filed", f + "_as_filed_filed"):
                    if k in o:
                        r[k] = o[k]
                    else:
                        r.pop(k, None)
        fixes = [x for x in fixes if not (x["rows"] == "quarterly" and x["field"] in broke)]
        notes.append(f"v2 quarterly {', '.join(sorted(broke))} not used: its quarters did not add up to the year")
    return {"sec_name": cf.get("entityName"), "annual": ann, "quarterly": qtr, "tags_used": norm["tags_used"],
            "annual_coverage": norm["annual_coverage"], "splits": norm["splits"], "checks": chk(),
            "v2_fixes": fixes, "v2_notes": notes}


def _off(checks: dict) -> set:
    """The items a data_checks() result says do not reconcile ("off:revenue,capex" -> {"revenue", "capex"})."""
    r = str(checks.get("reconciles") or "")
    return {x.strip() for x in r[4:].split(",") if x.strip()} if r.startswith("off:") else set()


UNI_COLS = ["ticker", "cik", "name", "gate", "shares_total", "classes", "cover_date", "cover_form", "public_float",
            "float_date", "assets", "revenue", "sic"]


def _uni_row(c: dict) -> dict:
    z = c["size"]
    return {"ticker": c["ticker"], "cik": c["cik"], "name": c["name"], "gate": c["gate"],
            "shares_total": None if c["shares_total"] is None else round(c["shares_total"]),
            "classes": json.dumps(c["classes"], sort_keys=True), "cover_date": c["cover_date"],
            "cover_form": (c["latest"] or {}).get("form"), "public_float": _r(z["public_float"]),
            "float_date": z["float_date"], "assets": _r(z["assets"]), "revenue": _r(z["revenue"]), "sic": c["sic"]}


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
    REVENUE_VERIFIED.update(load_revenue_verified())
    PREDECESSORS.update(load_predecessors())
    report: dict = {}
    src = Sources()
    uni = build_universe(src, weights, ads, report)
    print(f"universe: {len(uni)} companies that could be S&P-sized ({time.time() - t0:.0f}s)", flush=True)
    changes: list = []
    report["events"] = write_events(uni, src)
    report["tickers"] = write_tickers() if not ONLY else 0
    print(f"events: {report['events']} companies; tickers: {report['tickers']}", flush=True)
    report["library"] = None
    if LIBRARY:
        report["library"] = run_library(uni, changes, src)
        print(f"library done ({time.time() - t0:.0f}s)", flush=True)
    (OUT / "companies").mkdir(parents=True, exist_ok=True)
    recs, excluded, compare = [], [], []
    for i, c in enumerate(uni, 1):
        # NOTHING IS DROPPED (owner, 25 Sep 2026: "how do we know nothing else is silently dropped"): a company that
        # can't be built or has no revenue still gets its file, flagged, so fmp sees it and says so.
        try:
            rec = company_record(c, src)
        except Exception as e:                                      # noqa: BLE001
            print(f"  {c['ticker']}: {type(e).__name__}: {e}")
            rec = {"cik": c["cik"], "ticker": c["ticker"], "tickers": c["tickers"], "name": c["name"],
                   "sic": c["sic"], "annual": [], "quarterly": [], "v2_annual": [], "v2_quarterly": [], "ttm": {},
                   "balance": {}, "checks": {}, "flags": [f"build_error_{type(e).__name__}"],
                   "market": {"shares_total": c.get("shares_total"), "classes": c.get("classes"),
                              "cover_date": c.get("cover_date"), "size_gate": c.get("gate")}}
            excluded.append((c, f"error {type(e).__name__} (file written, flagged)"))
        rec["market"]["ads_ratio"] = ads.get(c["ticker"])
        if "revenue" not in rec["ttm"] and not any(f.startswith("build_error") for f in rec["flags"]):
            why = currency_note(src.facts(c["cik"])) or "no_revenue"
            rec["flags"] = [f for f in rec["flags"] if f != "no_revenue"] + [why]
            excluded.append((c, f"{why} (file written, flagged)"))
        ie = next((a.get("interest_expense") for a in reversed(rec.get("annual", [])) if a.get("interest_expense")), None)
        if rec.get("bank"):                     # a bank's interest expense is mostly on deposits, not debt
            ie = None
        if rec.get("balance", {}).get("total_debt") is None and ie and ie > INTEREST_NO_DEBT:
            rec["flags"] = rec["flags"] + ["interest_but_no_debt"]      # F, BRK-B, KKR: debt exists, v2 missed it
        td = rec.get("balance", {}).get("total_debt")
        if td and ie and ie > INTEREST_NO_DEBT and ie > 0.25 * td:     # ED: 0.97B found, ~1.2B of interest a year
            rec["flags"] = rec["flags"] + ["debt_too_small_for_interest"]
        years = sum(1 for r in rec.get("v2_annual", []) if r.get("revenue"))
        big = c.get("gate") in ("float", "assets") and 0 < years < 2        # revenue, but under 2 years of it
        if big and int(c["cik"]) not in PREDECESSORS:
            rec["flags"] = rec["flags"] + ["short_history"]            # a big company with < 2 years: a new
                                                                        # registrant (XOM)? add it to predecessors.csv
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
    ctypes = defaultdict(int)
    for ch in changes:
        ctypes[ch["type"]] += 1
    L = [f"# Pipeline v2 {TODAY}", "", "## ALARMS", ""] + alarms(recs, changes) + ["", f"- run: {secs / 60:.0f} min" + (f"; ONLY_TICKERS={','.join(ONLY)}" if ONLY else "")
         + (f"; LIMIT={LIMIT}" if LIMIT else ""),
         f"- universe: {n} companies that could be S&P-sized (no prices: fmp draws the $22.7B line with Robinhood's); "
         "by size gate: " + ", ".join(f"{k} {v}" for k, v in sorted(report.get("gates", {}).items())),
         f"- cover instances: {report.get('instances_fetched')} fetched of {report.get('instances_needed')} needed "
         f"(the rest from the cache); {report.get('instances_pruned', 0)} dropped from the cache",
         "- dropped before the universe: " + ", ".join(f"{k} {v}" for k, v in sorted(report.get("dropped", {}).items())),
         f"- TTM coverage: " + ", ".join(f"{k} {v}/{n}" for k, v in cov.items()) + f"; total_debt {debt}/{n}",
         "- changes this run: " + (", ".join(f"{k} {v}" for k, v in sorted(ctypes.items())) or "none"),
         ""]
    L += lib.report_lines(report.get("library")) + ["", "## Without usable revenue (files written, flagged; nothing is dropped)", ""]
    L += [f"- {c['ticker']} {c['name']}: {why}" for c, why in excluded] or ["- none"]
    L += ["", "## Data flags", ""]
    L += [f"- {c['ticker']}: {', '.join(r['flags'] + r.get('v2_notes', []))}" for c, r in recs
          if r["flags"] or r.get("v2_notes")] or ["- none"]
    L += ["", "## Largest 25 by public float", "", "| ticker | public float | revenue TTM | capex TTM | total debt | shares |",
          "|---|---|---|---|---|---|"]
    for c, r in recs[:25]:
        L.append(f"| {c['ticker']} | {_fmt(c['size']['public_float'])} | {_fmt((r['ttm'].get('revenue') or {}).get('val'))} | "
                 f"{_fmt((r['ttm'].get('capex') or {}).get('val'))} | {_fmt(r['balance'].get('total_debt'))} | "
                 f"{_fmt(c['shares_total'])} |")
    (OUT / "report.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    sys.exit(main())
