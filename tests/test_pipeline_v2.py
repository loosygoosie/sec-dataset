"""pipeline_v2.py without the network, on synthetic facts shaped like the cases that sent it: debt pieces added once
(AAPL's paper added, NXPI's not), capex from fallback and company-own tags (COP, NEE), revenue choice (RSG gross,
NTAP segment, COP non-606, banks), a year on a quarter context (LHX), cover shares over every class (HEICO, Berkshire,
co-registrant subsidiaries), ADS ratios, the universe filters, the change log and the v2-vs-old comparison. Also the
fetch_filings EVERYTHING mode the pipeline turns on, and that the default library plan is unchanged."""
import datetime as dt

import pytest

import fetch_filings as ff
import pipeline_v2 as V
from conftest import fact, fy_fact, q_fact, ytd_fact


def usd_facts(*fs):
    return list(fs)


def q1(val, end, start):
    """A first-quarter fact starting on the fiscal year's first day, as 10-Qs tag them."""
    return fact(val, end, start=start, form="10-Q", fp="Q1")


def inst(val, end, form="10-Q", filed=None, accn="a1"):
    return {"val": val, "end": end, "form": form, "filed": filed or end, "accn": accn}


# ---------------------------------------------------------------- debt
def test_debt_adds_paper_to_current_portion_and_noncurrent():
    d = V.assemble_debt({"LongTermDebtNoncurrent": 71_340, "LongTermDebtCurrent": 11_007, "CommercialPaper": 1_997})
    assert d["total_debt"] == 84_344 and d["debt_current"] == 13_004 and d["both_sides"]
    assert d["tags"] == ["LongTermDebtNoncurrent", "LongTermDebtCurrent", "CommercialPaper"]


def test_debt_current_total_is_not_topped_up_with_paper():
    """NXPI: DebtCurrent 0.75B is the whole current side; 2B of paper tagged elsewhere is not added again."""
    d = V.assemble_debt({"LongTermDebtAndCapitalLeaseObligations": 10_974, "DebtCurrent": 750,
                         "CommercialPaper": 2_000, "LongTermDebtCurrent": 750})
    assert d["total_debt"] == 11_724


def test_long_term_debt_including_current_portion_is_not_double_counted():
    d = V.assemble_debt({"LongTermDebt": 10_000, "LongTermDebtCurrent": 1_000})
    assert d["total_debt"] == 10_000 and d["debt_noncurrent"] == 9_000


def test_noncurrent_tag_is_preferred_over_inclusive_long_term_debt():
    d = V.assemble_debt({"LongTermDebtNoncurrent": 9_000, "LongTermDebt": 10_000, "LongTermDebtCurrent": 1_000})
    assert d["total_debt"] == 10_000


def test_short_term_borrowings_holding_current_maturities_take_the_larger():
    """PepsiCo-style: a ShortTermBorrowings line that already holds the current maturities is not added to them."""
    d = V.assemble_debt({"LongTermDebtNoncurrent": 20_000, "LongTermDebtCurrent": 1_600, "ShortTermBorrowings": 10_600})
    assert d["total_debt"] == 30_600


def test_paper_and_other_short_term_borrowings_add_to_current_portion():
    """NEE: commercial paper and other short-term debt are separate lines next to current maturities."""
    d = V.assemble_debt({"LongTermDebtNoncurrent": 98_790, "LongTermDebtCurrent": 5_413, "CommercialPaper": 1_736,
                         "OtherShortTermBorrowings": 4_258})
    assert d["total_debt"] == 110_197


def test_current_side_found_without_noncurrent_and_leases_kept_apart():
    d = V.assemble_debt({"ShortTermBorrowings": 500, "FinanceLeaseLiabilityNoncurrent": 70,
                         "FinanceLeaseLiabilityCurrent": 30})
    assert d["total_debt"] == 500 and d["finance_leases"] == 100 and not d["both_sides"]
    assert V.assemble_debt({"FinanceLeaseLiability": 5}) is None


# ---------------------------------------------------------------- periods
def test_quarters_derived_from_year_to_date_and_fiscal_year():
    fs = [fy_fact(400, "2025-12-31"), q1(90, "2025-03-31", "2025-01-01"), ytd_fact(190, "2025-01-01", "2025-06-30"),
          ytd_fact(290, "2025-01-01", "2025-09-30", fp="Q3")]
    ann, q, _ = V.flow_series(fs)
    assert ann["2025-12-31"]["val"] == 400
    assert [q[e]["val"] for e in sorted(q)] == [90, 100, 100, 110]
    assert q["2025-06-30"]["derived"] and q["2025-06-30"]["start"] == "2025-04-01"


def test_year_on_a_quarter_context_is_read_as_the_year():
    """LHX FY2025: the 10-K's full-year revenue (21.9B) sits on an Oct-Jan context; no 365-day fact exists."""
    fs = [ytd_fact(16_217, "2025-01-04", "2025-10-03", fp="Q3"),
          fact(21_865, "2026-01-02", start="2025-10-04", form="10-K")]
    ann, q, _ = V.flow_series(fs)
    assert ann["2026-01-02"]["val"] == 21_865 and ann["2026-01-02"]["start"] == "2025-01-04"
    assert q["2026-01-02"]["val"] == 21_865 - 16_217


def test_genuine_fourth_quarter_in_a_10k_is_left_alone():
    fs = [fy_fact(400, "2025-12-31"), ytd_fact(300, "2025-01-01", "2025-09-30", fp="Q3"),
          q_fact(100, "2025-12-31", form="10-K", fp="FY")]
    ann, q, _ = V.flow_series(fs)
    assert ann["2025-12-31"]["val"] == 400 and q["2025-12-31"]["val"] == 100


def test_ttm_from_year_to_date_when_single_quarters_are_missing():
    fs = [fy_fact(1_200, "2025-12-31", filed="2026-02-10"), ytd_fact(700, "2026-01-01", "2026-06-30", filed="2026-08-01"),
          ytd_fact(600, "2025-01-01", "2025-06-30", filed="2026-08-01")]
    ann, q, ytd = V.flow_series(fs)
    assert ytd["2026-06-30"]["val"] == 1_300
    for k in (ann, q, ytd):
        for r in k.values():
            r["tag"] = "T"
    t = V._ttm(q, ann, ytd)
    assert t["val"] == 1_300 and t["method"] == "year_to_date" and t["end"] == "2026-06-30"


def test_restated_value_keeps_the_first_filed_one():
    fs = [fy_fact(100, "2024-12-31", filed="2025-02-01"), fy_fact(90, "2024-12-31", filed="2026-02-01")]
    r = V.flow_series(fs)[0]["2024-12-31"]
    assert r["val"] == 90 and r["filed"] == "2026-02-01" and r["first_val"] == 100 and r["first_filed"] == "2025-02-01"


def test_value_repeated_later_is_dated_by_its_first_filing():
    fs = [fy_fact(100, "2024-12-31", filed="2025-02-01"), fy_fact(100, "2024-12-31", filed="2026-02-01")]
    r = V.flow_series(fs)[0]["2024-12-31"]
    assert r["filed"] == "2025-02-01" and "first_val" not in r


# ---------------------------------------------------------------- revenue
@pytest.mark.parametrize("c, want", [
    ({V.RFCWC: 16_591, "Revenues": 19_027}, V.RFCWC),                           # RSG: gross before eliminations
    ({V.RFCWC: 6_925, "Revenues": 6_237}, V.RFCWC),                             # NTAP: 'Revenues' is a segment
    ({V.RFCWC: 51_824, "Revenues": 58_944, V.RNFC: 7_201}, "Revenues"),         # COP: 606 + non-606 = total
    ({V.RFCWC: 100, "Revenues": 900}, "Revenues"),                              # a REIT: lease income outside 606
    ({"RegulatedAndUnregulatedOperatingRevenue": 5_141}, "RegulatedAndUnregulatedOperatingRevenue"),   # DTE
    ({"OperatingLeasesIncomeStatementLeaseRevenue": 61}, "OperatingLeasesIncomeStatementLeaseRevenue"),
    ({}, None),
])
def test_revenue_choice(c, want):
    assert V.choose_revenue(c, bank=False) == want


def test_bank_revenue_is_net_interest_plus_noninterest_income():
    F = {"InterestIncomeExpenseNet": [fy_fact(7_000, "2025-12-31")], "NoninterestIncome": [fy_fact(2_700, "2025-12-31")],
         "InterestAndDividendIncomeOperating": [fy_fact(10_000, "2025-12-31")],
         V.RFCWC: [fy_fact(860, "2025-12-31")], "Revenues": [fy_fact(1_660, "2025-12-31")]}
    out = V.fundamentals(F)
    assert out["bank"] and out["annual"][-1]["revenue"] == 9_700
    assert out["annual"][-1]["src"]["revenue"]["tag"] == V.BANK_NET
    F["RevenuesNetOfInterestExpense"] = [fy_fact(9_800, "2025-12-31")]
    assert V.fundamentals(F)["annual"][-1]["revenue"] == 9_800


def test_bank_without_net_interest_income_falls_back_to_gross():
    assert V.choose_revenue({V.BANK_GROSS: 12_700}, bank=True) == V.BANK_GROSS


# ---------------------------------------------------------------- capex
def test_capex_fallback_tags_in_priority_order():
    F = {"PaymentsToAcquireProductiveAssets": [fy_fact(500, "2025-12-31")],
         "NetCashProvidedByUsedInOperatingActivities": [fy_fact(2_000, "2025-12-31")]}
    row = V.fundamentals(F)["annual"][-1]
    assert row["capex"] == 500 and row["fcf"] == 1_500
    F["PaymentsToAcquirePropertyPlantAndEquipment"] = [fy_fact(450, "2025-12-31")]
    assert V.fundamentals(F)["annual"][-1]["capex"] == 450


def test_company_own_capex_tag_from_the_instance_fills_a_gap():
    """COP 2023-25 and NEE: no us-gaap capex; their own concept is in the 10-K's XBRL. Of several, the largest (the
    total) wins; planned / accrued ones never count."""
    F = {"NetCashProvidedByUsedInOperatingActivities": [dict(fy_fact(20_000, "2025-12-31"), accn="k1")]}
    x = {"cop:SegmentReportingInformationCapitalExpendituresAndInvestments": [
            [12_553.0, "USD", "2025-01-01", "2025-12-31", {}],
            [3_607.0, "USD", "2025-01-01", "2025-12-31", {"us-gaap:StatementBusinessSegmentsAxis": "cop:Alaska"}]],
         "nee:CapitalExpendituresOfFPL": [[8_719.0, "USD", "2025-01-01", "2025-12-31", {}]],
         "cop:PlannedCapitalExpendituresFirstYear": [[99_999.0, "USD", "2025-01-01", "2025-12-31", {}]],
         "us-gaap:Revenues": [[1.0, "USD", "2025-01-01", "2025-12-31", {}]]}
    assert V.merge_instance(F, x, "10-K", "2026-02-17", "k1") == 2        # us-gaap skipped: companyfacts has k1
    row = V.fundamentals(F)["annual"][-1]
    assert row["capex"] == 12_553
    assert row["src"]["capex"]["tag"] == "ext:SegmentReportingInformationCapitalExpendituresAndInvestments"


def test_instance_fills_a_quarter_companyfacts_lacks():
    """CNP's Q2 10-Q was not in companyfacts: the undimensioned us-gaap facts of the instance fill it."""
    F = {"LongTermDebtNoncurrent": [inst(22_476, "2026-03-31", accn="q1")]}
    x = {"us-gaap:LongTermDebtNoncurrent": [[22_906.0, "USD", None, "2026-06-30", {}],
                                            [10_837.0, "USD", None, "2026-06-30", {"dei:LegalEntityAxis": "cnp:HE"}]],
         "us-gaap:OtherLongTermDebtCurrent": [[1_616.0, "USD", None, "2026-06-30", {}]]}
    assert V.merge_instance(F, x, "10-Q", "2026-07-28", "q2") == 2
    s = V.instant_series(F["LongTermDebtNoncurrent"])
    assert s["2026-06-30"]["val"] == 22_906 and s["2026-06-30"]["filed"] == "2026-07-28"
    assert V.assemble_debt({"LongTermDebtNoncurrent": 22_906, "OtherLongTermDebtCurrent": 1_616})["total_debt"] == 24_522


def test_fundamentals_rows_ttm_and_balance():
    F = {V.RFCWC: [fy_fact(400, "2025-12-31"), q1(90, "2025-03-31", "2025-01-01"),
                   ytd_fact(190, "2025-01-01", "2025-06-30"), ytd_fact(290, "2025-01-01", "2025-09-30"),
                   q1(120, "2026-03-31", "2026-01-01")],
         "LongTermDebtNoncurrent": [inst(1_000, "2026-03-31")], "DebtCurrent": [inst(100, "2026-03-31")],
         "CashAndCashEquivalentsAtCarryingValue": [inst(50, "2026-03-31")], "ShortTermInvestments": [inst(25, "2026-03-31")],
         "StockholdersEquity": [inst(700, "2026-03-31")]}
    out = V.fundamentals(F)
    assert out["ttm"]["revenue"]["val"] == 100 + 100 + 110 + 120 and out["ttm"]["revenue"]["method"] == "four_quarters"
    assert out["balance"] == {"end": "2026-03-31", "cash_and_sti": 75, "total_debt": 1_100, "debt_noncurrent": 1_000,
                              "debt_current": 100, "equity": 700}
    assert out["quarterly"][-1]["src"]["total_debt"]["tags"] == ["LongTermDebtNoncurrent", "DebtCurrent"]
    assert "no_capex" in out["flags"]


# ---------------------------------------------------------------- shares and market value
def cover(*rows):
    return {V.COVER: [[float(v), "shares", None, "2026-08-25", dims] for v, dims in rows]}


def test_cover_adds_every_class():
    """HEICO: common + Class A, both dimensioned; companyfacts keeps neither total."""
    date, got = V.cover_classes(cover((55_241_647, {"us-gaap:StatementClassOfStockAxis": "hei:HeicoCommonStockMember"}),
                                      (84_515_758, {"us-gaap:StatementClassOfStockAxis": "us-gaap:CommonClassAMember"})))
    assert date == "2026-08-25" and sum(got.values()) == 139_757_405 and set(got) == {"HeicoCommonStockMember",
                                                                                        "CommonClassAMember"}


def test_cover_drops_co_registrants_and_a_repeated_total():
    _, got = V.cover_classes(cover((658_720_288, {}), (1_000, {"dei:LegalEntityAxis": "cnp:HoustonElectricMember"})))
    assert got == {"common": 658_720_288}
    _, got = V.cover_classes(cover((300, {}), (100, {"x:ClassAxis": "a:A"}), (200, {"x:ClassAxis": "a:B"})))
    assert sum(got.values()) == 300


def test_class_weights_ads_and_splits():
    w = {"BRK-B": [("ClassA", 1500.0)]}
    classes = {"CommonClassAMember": 488_450.0, "CommonClassBMember": 1_408_035_161.0}
    assert V.shares_total(classes, "BRK-B", w, {}) == pytest.approx(1_408_035_161 + 488_450 * 1500)
    assert V.shares_total({"common": 1_300.0}, "ONC", {}, {"ONC": 13.0}) == pytest.approx(100)
    assert V.shares_total({}, "X", {}, {}) is None


def test_size_signals_and_gate():
    today = dt.date(2026, 9, 25)
    cf = {"facts": {"dei": {"EntityPublicFloat": {"units": {"USD": [
            {"val": 1e9, "end": "2024-06-30", "filed": "2025-02-01"}, {"val": 3e9, "end": "2025-06-30", "filed": "2026-02-01"}]}}},
        "us-gaap": {"Assets": {"units": {"USD": [{"val": 4e9, "end": "2026-06-30", "filed": "2026-08-01"}]}},
                    "Revenues": {"units": {"USD": [
                        {"val": 9e8, "start": "2025-01-01", "end": "2025-12-31", "filed": "2026-02-01"},
                        {"val": 5e8, "start": "2026-01-01", "end": "2026-06-30", "filed": "2026-08-01"}]}},
                    "SalesRevenueNet": {"units": {"USD": [
                        {"val": 9e9, "start": "2016-01-01", "end": "2016-12-31", "filed": "2017-02-01"}]}}}}}
    sig = V.size_signals(cf)
    assert sig["public_float"] == 3e9 and sig["assets"] == 4e9
    assert sig["revenue"] == 9e8                              # the 2016 tag is stale, the half year is not annual
    assert V.size_gate(sig, 5, today) == "float"
    assert V.size_gate(dict(sig, public_float=1e9), 5, today) is None
    assert V.size_gate(dict(sig, public_float=1e9, assets=6e9), 5, today) == "assets"
    assert V.size_gate(dict(sig, public_float=1e9, revenue=2e9), 5, today) == "revenue"
    ipo = {"public_float": None, "float_filed": None, "assets": 1e9, "revenue": 2e8}
    assert V.size_gate(ipo, 1, today) == "no_float" and V.size_gate(ipo, 4, today) is None
    old = dict(sig, float_filed="2024-01-01")                 # a float filed > 18 months ago counts as none
    assert V.size_gate(old, 1, today) == "no_float" and V.size_gate(old, 3, today) is None


def test_instance_cache_prefetch_and_prune(tmp_path, monkeypatch):
    import gzip
    monkeypatch.setattr(V, "WORK", tmp_path); monkeypatch.setattr(V, "STORE", tmp_path / "store")
    (tmp_path / "xbrl").mkdir()
    for name in ("1_a", "2_b"):
        with gzip.open(tmp_path / "xbrl" / f"{name}.json.gz", "wt") as fh:
            fh.write("{}")
    fetched = []
    monkeypatch.setattr(V, "instance", lambda cik, accn: fetched.append((cik, accn)))
    assert V.prefetch({(1, "a"), (3, "c"), (4, "d")}) == 2 and sorted(fetched) == [(3, "c"), (4, "d")]
    assert V.prune_cache({(1, "a")}) == 1 and not (tmp_path / "xbrl" / "2_b.json.gz").exists()


# ---------------------------------------------------------------- universe filters
@pytest.mark.parametrize("tickers, exch, want", [
    (["HEI", "HEI-A"], ["NYSE", "NYSE"], "HEI"),
    (["BAC-PL", "BAC"], ["NYSE", "NYSE"], "BAC"),
    (["ABCDW", "ABCD"], ["Nasdaq", "Nasdaq"], "ABCD"),
    (["XYZ"], ["OTC"], None),
    (["XYZ"], [None], None),
    (["BRK.B"], ["NYSE"], "BRK-B"),
])
def test_primary_ticker(tickers, exch, want):
    assert V.primary_ticker(tickers, exch) == want


@pytest.mark.parametrize("name, want", [("ENTERPRISE PRODUCTS PARTNERS L.P.", True), ("Energy Transfer LP", True),
                                        ("MPLX LP", True), ("KKR & Co. Inc.", False), ("Alpine Corp", False)])
def test_partnerships(name, want):
    assert V.is_partnership(name) is want


def sub(forms, dates, tickers=("ABC",), exch=("NYSE",), name="Abc Inc", sic="3571"):
    n = len(forms)
    return {"cik": "0000000001", "name": name, "sic": sic, "tickers": list(tickers), "exchanges": list(exch),
            "filings": {"recent": {"form": forms, "filingDate": dates, "accessionNumber": [f"a{i}" for i in range(n)],
                                   "reportDate": dates, "primaryDocument": ["d.htm"] * n}}}


def test_candidate_filters():
    today = dt.date(2026, 9, 24)
    c, why = V.candidate(sub(["10-Q", "10-K", "8-K"], ["2026-08-01", "2026-02-01", "2026-09-01"]), today)
    assert c and c["ticker"] == "ABC" and c["latest"]["form"] == "10-Q" and c["latest"]["accn"] == "a0"
    assert V.candidate(sub(["10-K"], ["2026-02-01"]), today) == (None, "no_recent_10q")
    assert V.candidate(sub(["10-Q"], ["2024-02-01"]), today) == (None, "no_recent_10q")
    assert V.candidate(sub(["10-Q"], ["2026-08-01"], name="MPLX LP"), today) == (None, "partnership")
    assert V.candidate(sub(["10-Q"], ["2026-08-01"], sic="6221"), today) == (None, "commodity_trust")
    assert V.candidate(sub(["10-Q"], ["2026-08-01"], exch=("OTC",)), today) == (None, "no_listed_common_ticker")


def test_prescreen_shares_from_companyfacts():
    cf = {"facts": {"dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [
        {"val": 5, "end": "2025-01-01"}, {"val": 7, "end": "2026-01-01"}]}}}}}
    assert V.cf_shares(cf) == 7 and V.cf_shares({}) is None


# ---------------------------------------------------------------- change log and comparison
def test_universe_changes():
    prev = {"1": {"ticker": "A"}, "2": {"ticker": "B"}}
    new = {"1": {"ticker": "A"}, "3": {"ticker": "C", "gate": "float"}}
    got = {(c["ticker"], c["type"]) for c in V.universe_changes(prev, new)}
    assert got == {("B", "left_universe"), ("C", "entered_universe")}


def test_company_changes():
    prev = {"cik": 1, "ticker": "A", "latest_filing": {"accn": "x"}, "ttm": {"revenue": {"val": 10}},
            "balance": {"total_debt": 5}, "market": {"shares_total": 100}}
    new = dict(prev, latest_filing={"accn": "y", "form": "10-Q", "filed": "2026-09-01"},
               ttm={"revenue": {"val": 12}}, market={"shares_total": 100.01})
    got = V.company_changes(prev, new)
    assert [c["type"] for c in got] == ["new_filing", "fact_change"] and got[1]["field"] == "revenue_ttm"
    assert V.company_changes(None, new) == []


def test_compare_flags_only_differences_over_five_percent():
    old = {"annual": [{"period_end": "2025-12-31", "revenue": 100, "capex": 10}],
           "quarterly": [{"period_end": "2026-06-30", "total_debt": 1000, "shares_outstanding": 55}]}
    new = {"annual": [{"end": "2025-12-31", "revenue": 104, "capex": 20}],
           "quarterly": [{"end": "2026-06-30", "total_debt": 1_100}],
           "market": {"cover_date": "2026-08-25", "shares_cover": 140}}
    got = {r["field"]: r for r in V.compare_company(old, new)}
    assert set(got) == {"capex", "total_debt", "shares"}
    assert got["capex"]["pct"] == 100.0 and got["total_debt"]["pct"] == 10.0
    old["annual"][0]["capex"] = None
    assert V.compare_company(old, new)[0] == {"field": "capex", "period": "2025-12-31", "old": None, "v2": 20,
                                              "pct": None}


# ---------------------------------------------------------------- fetch_filings EVERYTHING mode
def filings_sub(today):
    d = lambda n: str(today - dt.timedelta(days=n))                 # noqa: E731
    rows = [("10-K", d(200)), ("10-K", d(565)), ("10-K", d(930)), ("10-K", d(1300)), ("10-Q", d(40)), ("8-K", d(10)),
            ("4", d(5)), ("4", d(500)), ("144", d(30)), ("SC 13G/A", d(800)), ("SCHEDULE 13D", d(1000)), ("SC 13G", d(1200)),
            ("CORRESP", d(300)), ("UPLOAD", d(900)), ("NT 10-Q", d(100)), ("S-4", d(90)), ("S-4/A", d(60)),
            ("S-8", d(20)), ("DEFA14A", d(50)), ("S-3ASR", d(700))] + [("424B2", d(i)) for i in range(1, 41)]
    return {"filings": {"recent": {"form": [f for f, _ in rows], "filingDate": [x for _, x in rows],
                                   "accessionNumber": [f"acc{i}" for i in range(len(rows))],
                                   "primaryDocument": ["doc.htm"] * len(rows), "reportDate": [""] * len(rows)}}}


def test_default_plan_is_unchanged():
    keep = ff.plan(filings_sub(ff.TODAY))
    assert sorted(x["form"] for x in keep) == ["10-K", "10-Q", "8-K"]
    assert not any("all_exhibits" in x or "insider" in x for x in keep)


def test_everything_plan_keeps_every_kind():
    keep = ff.plan(filings_sub(ff.TODAY), everything=True)
    forms = [x["form"] for x in keep]
    assert forms.count("10-K") == 3                                  # the latest and the two before it
    assert forms.count("4") == 1 and "144" in forms                  # 400 days
    assert {"SC 13G/A", "SCHEDULE 13D", "CORRESP", "UPLOAD", "NT 10-Q", "DEFA14A", "S-8"} <= set(forms)
    assert "SC 13G" not in forms                                     # older than 3 years
    assert "S-4/A" in forms and "S-4" not in forms                   # latest amendment only
    assert "S-3ASR" not in forms                                     # older than 400 days
    assert forms.count("424B2") == ff.MAX_424B
    assert all(x.get("insider") for x in keep if x["form"] in ("4", "144"))
    tenks = sorted((x for x in keep if x["form"] == "10-K"), key=lambda x: x["date"], reverse=True)
    assert tenks[0].get("all_exhibits") and not tenks[1].get("all_exhibits")
    assert all(x.get("all_exhibits") for x in keep if x["form"] in ("10-Q", "8-K"))


FORM4 = b"""<?xml version="1.0"?><ownershipDocument><documentType>4</documentType>
<reportingOwner><reportingOwnerId><rptOwnerName>Doe Jane</rptOwnerName></reportingOwnerId>
<reportingOwnerRelationship><isDirector>0</isDirector><isOfficer>1</isOfficer><officerTitle>CFO</officerTitle>
</reportingOwnerRelationship></reportingOwner>
<nonDerivativeTable><nonDerivativeTransaction><securityTitle><value>Common Stock</value></securityTitle>
<transactionDate><value>2026-09-01</value></transactionDate><transactionCoding><transactionCode>S</transactionCode>
</transactionCoding><transactionAmounts><transactionShares><value>1000</value></transactionShares>
<transactionPricePerShare><value>250.5</value></transactionPricePerShare>
<transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode></transactionAmounts>
<postTransactionAmounts><sharesOwnedFollowingTransaction><value>5000</value></sharesOwnedFollowingTransaction>
</postTransactionAmounts><ownershipNature><directOrIndirectOwnership><value>D</value></directOrIndirectOwnership>
</ownershipNature></nonDerivativeTransaction></nonDerivativeTable></ownershipDocument>"""


def test_form4_is_one_line_per_transaction():
    lines = ff.ownership_lines(FORM4, "0001-26-1", "4", "2026-09-03")
    assert lines == ["0001-26-1 4 filed 2026-09-03 | Doe Jane (Officer, CFO) | S 2026-09-01 D 1000 @ 250.5 -> 5000 D "
                     "| Common Stock"]
    other = ff.ownership_lines(b"<edgarSubmission><seller>X</seller><shares>10</shares></edgarSubmission>",
                               "a", "144", "2026-09-01")
    assert other == ["a 144 filed 2026-09-01 | seller=X; shares=10"]
    assert ff.raw_doc_name("xslF345X05/wk-form4_1.xml") == "wk-form4_1.xml"


def test_bulk_files_point_at_their_own_folders():
    """companyfacts.zip is under daily-index/xbrl/, submissions.zip under daily-index/bulkdata/ (the first run 403'd
    asking for bulkdata/companyfacts.zip)."""
    import pipeline_v2 as P
    assert P.BULK["companyfacts"].endswith("/daily-index/xbrl/companyfacts.zip")
    assert P.BULK["submissions"].endswith("/daily-index/bulkdata/submissions.zip")


def test_events_record_keeps_recent_periodic_and_8k_with_items():
    import datetime as dt
    import pipeline_v2 as P
    sub = {"name": "X", "sicDescription": "Y", "sic": "1", "tickers": ["X"],
           "filings": {"recent": {"form": ["8-K", "4", "10-Q", "8-K"],
                                  "filingDate": ["2026-09-01", "2026-09-02", "2026-08-01", "2024-01-01"],
                                  "accessionNumber": ["a1", "a2", "a3", "a4"],
                                  "items": ["2.02,9.01", "", "", "5.02"],
                                  "reportDate": ["2026-09-01", "", "2026-06-30", ""],
                                  "primaryDocument": ["d.htm"] * 4}}}
    rec = P.events_record(sub, 7, dt.date(2026, 9, 25))
    assert [e["accession"] for e in rec["events"]] == ["a1", "a3"]
    assert rec["events"][0]["items"] == ["2.02", "9.01"] and rec["tickers"] == ["X"]
