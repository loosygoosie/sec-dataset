"""Tests for the stale-name fallback: reading a quarter out of the filing itself.

The SEC's bulk companyfacts file trails some filers by months, so a company can show a
five-month-old quarter while a newer 10-Q sits in the events feed. For those companies only,
the build reads the filing's own XBRL instance and puts it through the same normaliser.

The instance below is synthetic but carries every shape that decides an outcome: a genuine
three-month context, a year-to-date one, an instant, a dimensioned context that must be
ignored, a nil fact, and a filer extension tag.
"""
from __future__ import annotations

import json

import pytest

from conftest import doc, usd, ytd_fact

INSTANCE = """<?xml version="1.0"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
      xmlns:us-gaap="http://fasb.org/us-gaap/2026"
      xmlns:dei="http://xbrl.sec.gov/dei/2026"
      xmlns:xbrldi="http://xbrl.org/2006/xbrldi"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xmlns:acme="http://acme.com/20260630">
  <context id="q2"><entity><identifier scheme="x">1</identifier></entity>
    <period><startDate>2026-04-01</startDate><endDate>2026-06-30</endDate></period></context>
  <context id="ytd"><entity><identifier scheme="x">1</identifier></entity>
    <period><startDate>2026-01-01</startDate><endDate>2026-06-30</endDate></period></context>
  <context id="inst"><entity><identifier scheme="x">1</identifier></entity>
    <period><instant>2026-06-30</instant></period></context>
  <context id="seg"><entity><identifier scheme="x">1</identifier>
      <segment><xbrldi:explicitMember dimension="us-gaap:StatementBusinessSegmentsAxis">acme:Utility</xbrldi:explicitMember></segment>
    </entity><period><startDate>2026-04-01</startDate><endDate>2026-06-30</endDate></period></context>
  <unit id="usd"><measure>iso4217:USD</measure></unit>
  <unit id="shares"><measure>xbrli:shares</measure></unit>
  <unit id="perShare"><unitNumerator><measure>iso4217:USD</measure></unitNumerator>
    <unitDenominator><measure>xbrli:shares</measure></unitDenominator></unit>
  <us-gaap:Revenues contextRef="q2" unitRef="usd" decimals="-6">5445000000</us-gaap:Revenues>
  <us-gaap:Revenues contextRef="q2" unitRef="usd" decimals="-6">5445000000</us-gaap:Revenues>
  <us-gaap:Revenues contextRef="seg" unitRef="usd" decimals="-6">999000000</us-gaap:Revenues>
  <us-gaap:NetCashProvidedByUsedInOperatingActivities contextRef="ytd" unitRef="usd">3421000000</us-gaap:NetCashProvidedByUsedInOperatingActivities>
  <us-gaap:Assets contextRef="inst" unitRef="usd">121570000000</us-gaap:Assets>
  <us-gaap:EarningsPerShareDiluted contextRef="q2" unitRef="perShare">1.39</us-gaap:EarningsPerShareDiluted>
  <us-gaap:NetIncomeLoss contextRef="q2" unitRef="usd" xsi:nil="true"/>
  <dei:EntityCommonStockSharesOutstanding contextRef="inst" unitRef="shares">534000000</dei:EntityCommonStockSharesOutstanding>
  <acme:RegulatoryThing contextRef="q2" unitRef="usd">42</acme:RegulatoryThing>
</xbrl>"""


@pytest.fixture
def parsed(b):
    return b.parse_xbrl_instance(INSTANCE, "10-Q", "2026-07-30")


def _facts(parsed, tag, ns="us-gaap", unit="USD"):
    return parsed["facts"][ns].get(tag, {}).get("units", {}).get(unit, [])


# --------------------------------------------------------------------------
# Parsing one filing's instance
# --------------------------------------------------------------------------
def test_a_three_month_fact_keeps_its_period_and_filing_metadata(parsed):
    (f,) = _facts(parsed, "Revenues")

    assert f["val"] == 5445000000
    assert f["start"] == "2026-04-01" and f["end"] == "2026-06-30"
    assert f["form"] == "10-Q" and f["filed"] == "2026-07-30"


def test_a_segment_breakdown_is_not_mistaken_for_the_company_total(parsed):
    """companyfacts drops dimensioned facts; taking them here would put a segment's revenue
    where the company's total belongs."""
    assert [f["val"] for f in _facts(parsed, "Revenues")] == [5445000000]


def test_the_same_fact_tagged_twice_in_one_document_is_stored_once(parsed):
    assert len(_facts(parsed, "Revenues")) == 1


def test_an_instant_has_no_start_date(parsed):
    (f,) = _facts(parsed, "Assets")

    assert f["end"] == "2026-06-30" and "start" not in f


def test_a_nil_fact_is_skipped(parsed):
    assert _facts(parsed, "NetIncomeLoss") == []


def test_a_filers_own_extension_tag_is_ignored(parsed):
    """CONCEPTS only knows us-gaap and dei; an extension tag means nothing to it."""
    assert all("Regulatory" not in t for t in parsed["facts"]["us-gaap"])


def test_units_are_resolved_including_the_per_share_ratio(parsed):
    assert _facts(parsed, "EarningsPerShareDiluted", unit="USD/shares")[0]["val"] == 1.39
    assert _facts(parsed, "EntityCommonStockSharesOutstanding", ns="dei", unit="shares")[0]["val"] == 534000000


def test_a_ten_k_is_marked_as_a_full_year_period(b):
    p = b.parse_xbrl_instance(INSTANCE, "10-K", "2026-08-11")

    assert p["facts"]["us-gaap"]["Revenues"]["units"]["USD"][0]["fp"] == "FY"


# --------------------------------------------------------------------------
# Merging it in and re-deriving the quarter
# --------------------------------------------------------------------------
def test_the_missing_quarter_is_derived_with_the_same_ytd_rules(b):
    """Q1 is on file from companyfacts; the filing carries only a six-month year-to-date cash
    flow. Q2 must come out as the difference, exactly as it would from the bulk file."""
    base = doc(us_gaap={
        "Revenues": usd(ytd_fact(6020000000, "2026-01-01", "2026-03-31")),
        "NetCashProvidedByUsedInOperatingActivities": usd(ytd_fact(1519000000, "2026-01-01", "2026-03-31")),
    })
    before = {r["period_end"] for r in b.normalise_company(base)["quarterly"]}

    b.merge_facts(base, b.parse_xbrl_instance(INSTANCE, "10-Q", "2026-07-30"))
    rows = {r["period_end"]: r for r in b.normalise_company(base)["quarterly"]}

    assert "2026-06-30" not in before
    assert rows["2026-06-30"]["revenue"] == 5445000000
    assert rows["2026-06-30"]["operating_cash_flow"] == 3421000000 - 1519000000
    assert rows["2026-03-31"]["operating_cash_flow"] == 1519000000      # untouched


def test_merging_leaves_the_existing_facts_in_place(b):
    base = doc(us_gaap={"Revenues": usd(ytd_fact(6020000000, "2026-01-01", "2026-03-31"))})

    b.merge_facts(base, b.parse_xbrl_instance(INSTANCE, "10-Q", "2026-07-30"))

    vals = {f["val"] for f in base["facts"]["us-gaap"]["Revenues"]["units"]["USD"]}
    assert vals == {6020000000, 5445000000}


# --------------------------------------------------------------------------
# Choosing which companies to patch
# --------------------------------------------------------------------------
def _manifest(listed=(), **rows):
    return {cik: {"quarter_age_days": age, "latest_quarter_end": lq,
                  "tickers": ["T" + cik] if cik in listed else []} for cik, (age, lq) in rows.items()}


def _events(tmp_path, monkeypatch, b, **per_cik):
    monkeypatch.setattr(b, "EVENTS_DIR", tmp_path)
    for cik, evs in per_cik.items():
        (tmp_path / f"{cik}.json").write_text(json.dumps({"events": evs}))


FILING = {"form": "10-Q", "period": "2026-06-30", "accession": "0000004904-26-000059", "date": "2026-07-30"}


def test_a_stale_company_with_a_newer_filing_is_a_target(b, tmp_path, monkeypatch):
    man = _manifest(**{"4904": (161, "2026-03-31")})
    _events(tmp_path, monkeypatch, b, **{"4904": [FILING]})

    assert b.patch_targets(man) == [(4904, [FILING])]


def test_a_company_whose_bulk_data_is_current_is_left_alone(b, tmp_path, monkeypatch):
    """The whole point is to touch only what is behind; a fresh company must not be refetched."""
    man = _manifest(**{"320193": (70, "2026-06-27")})
    _events(tmp_path, monkeypatch, b, **{"320193": [FILING]})

    assert b.patch_targets(man) == []


def test_a_stale_company_with_no_newer_filing_is_left_alone(b, tmp_path, monkeypatch):
    man = _manifest(**{"4904": (161, "2026-06-30")})       # the filing is not newer than what we hold
    _events(tmp_path, monkeypatch, b, **{"4904": [FILING]})

    assert b.patch_targets(man) == []


def test_a_company_with_no_events_record_is_skipped(b, tmp_path, monkeypatch):
    man = _manifest(**{"4904": (161, "2026-03-31")})
    _events(tmp_path, monkeypatch, b)

    assert b.patch_targets(man) == []


def test_missing_quarters_are_ordered_oldest_first(b, tmp_path, monkeypatch):
    """Deriving a quarter from a year-to-date figure needs the earlier quarters of that year to
    exist, so a two-quarter gap has to be filled in order."""
    q3 = {**FILING, "period": "2026-03-31", "accession": "a1"}
    q4 = {**FILING, "period": "2026-06-30", "accession": "a2"}
    man = _manifest(**{"721371": (251, "2025-12-31")})
    _events(tmp_path, monkeypatch, b, **{"721371": [q4, q3]})

    assert [f["period"] for f in b.patch_targets(man)[0][1]] == ["2026-03-31", "2026-06-30"]


def test_listed_companies_are_served_before_other_stale_filers(b, tmp_path, monkeypatch):
    """The budget is capped, so it should be spent where the data is actually read: `fmp` can only
    buy a company with a ticker. (S&P 500 constituents were this tier until 24 Sep 2026.)"""
    man = _manifest(listed=("4904",), **{"4904": (161, "2026-03-31"), "999": (400, "2025-01-31")})
    _events(tmp_path, monkeypatch, b, **{"4904": [FILING], "999": [FILING]})

    assert [cik for cik, _ in b.patch_targets(man)] == [4904, 999]


def test_within_a_tier_the_most_stale_goes_first(b, tmp_path, monkeypatch):
    man = _manifest(**{"4904": (161, "2026-03-31"), "999": (400, "2025-01-31")})
    _events(tmp_path, monkeypatch, b, **{"4904": [FILING], "999": [FILING]})

    assert [cik for cik, _ in b.patch_targets(man)] == [999, 4904]


# --------------------------------------------------------------------------
# Whose figures a filing holds (24 Sep 2026)
# --------------------------------------------------------------------------
# A subsidiary that co-files a combined 10-Q with its parent finds the PARENT's CIK on the
# undimensioned contexts: Transco and Northwest Pipeline were given Williams' revenue and 1.225B
# diluted shares this way, Piedmont was given Duke's.
SUB, PARENT = 99250, 107263


def _instance(period_end, revenue, entity_cik=None, identifier=SUB):
    from datetime import date, timedelta

    start = (date.fromisoformat(period_end) - timedelta(days=91)).isoformat()
    ecik = (f'<dei:EntityCentralIndexKey contextRef="d">{entity_cik:010d}</dei:EntityCentralIndexKey>'
            if entity_cik is not None else "")
    return f"""<?xml version="1.0"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
      xmlns:us-gaap="http://fasb.org/us-gaap/2026"
      xmlns:dei="http://xbrl.sec.gov/dei/2026"
      xmlns:xbrldi="http://xbrl.org/2006/xbrldi">
  <context id="d"><entity><identifier scheme="http://www.sec.gov/CIK">{identifier:010d}</identifier></entity>
    <period><startDate>{start}</startDate><endDate>{period_end}</endDate></period></context>
  <context id="sub"><entity><identifier scheme="http://www.sec.gov/CIK">{identifier:010d}</identifier>
      <segment><xbrldi:explicitMember dimension="dei:LegalEntityAxis">x:SubMember</xbrldi:explicitMember></segment>
    </entity><period><startDate>{start}</startDate><endDate>{period_end}</endDate></period></context>
  <unit id="usd"><measure>iso4217:USD</measure></unit>
  {ecik}
  <dei:EntityCentralIndexKey contextRef="sub">{SUB:010d}</dei:EntityCentralIndexKey>
  <us-gaap:Revenues contextRef="d" unitRef="usd">{revenue}</us-gaap:Revenues>
  <us-gaap:NetIncomeLoss contextRef="d" unitRef="usd">{revenue // 10}</us-gaap:NetIncomeLoss>
  <us-gaap:Revenues contextRef="sub" unitRef="usd">1</us-gaap:Revenues>
</xbrl>"""


def _stored_record(b, cik):
    """What is on disk for a company whose companyfacts stops at 2025-06-30."""
    from datetime import date

    from conftest import fy_fact, q_fact

    facts = doc(us_gaap={
        "Revenues": usd(fy_fact(4_000_000_000, "2024-12-31", filed="2025-02-20", fy=2024),
                        q_fact(900_000_000, "2025-03-31", filed="2025-04-30", fy=2025),
                        q_fact(950_000_000, "2025-06-30", filed="2025-07-30", fy=2025)),
        "NetIncomeLoss": usd(fy_fact(400_000_000, "2024-12-31", filed="2025-02-20", fy=2024),
                             q_fact(90_000_000, "2025-03-31", filed="2025-04-30", fy=2025),
                             q_fact(95_000_000, "2025-06-30", filed="2025-07-30", fy=2025)),
    }, cik=cik)
    rec, _ = b.company_record(facts, b.normalise_company(facts), cik, {}, date(2026, 9, 24), {}, {})
    return json.loads(b.record_body(rec)), facts


def _fake_sec(b, monkeypatch, instances: dict):
    monkeypatch.setattr(b, "filing_instance_url", lambda cik, acc: f"inst://{acc}")

    class R:
        def __init__(self, text):
            self.text = text

    monkeypatch.setattr(b, "get", lambda url, *a, **kw: R(instances[url.split("//", 1)[1]]))


Q3 = {"form": "10-Q", "period": "2025-09-30", "accession": "q3", "date": "2025-10-30"}


def test_the_instance_reports_whose_figures_it_holds(b):
    assert b.parse_xbrl_instance(_instance("2025-09-30", 1, entity_cik=PARENT), "10-Q", "x")["entity_cik"] == PARENT
    assert b.parse_xbrl_instance(_instance("2025-09-30", 1, entity_cik=SUB), "10-Q", "x")["entity_cik"] == SUB


def test_without_a_tagged_cik_the_undimensioned_identifier_decides(b):
    assert b.parse_xbrl_instance(_instance("2025-09-30", 1, identifier=PARENT), "10-Q", "x")["entity_cik"] == PARENT


def test_a_co_registrants_combined_filing_patches_nothing(b, monkeypatch):
    """The subsidiary is listed on its parent's combined 10-Q, whose undimensioned figures are the
    PARENT's. Storing them is the Transco / Williams bug; nothing may be patched."""
    rec, facts = _stored_record(b, SUB)
    before = json.loads(json.dumps(rec))
    _fake_sec(b, monkeypatch, {"q3": _instance("2025-09-30", 3_048_000_000, entity_cik=PARENT, identifier=PARENT)})

    ok, budget = b.patch_company(SUB, rec, facts, [Q3], 5)

    assert ok is False and budget == 4
    assert rec == before
    assert "2025-09-30" not in {r["period_end"] for r in rec["quarterly"]}


def test_the_companys_own_filing_still_patches(b, monkeypatch):
    rec, facts = _stored_record(b, SUB)
    _fake_sec(b, monkeypatch, {"q3": _instance("2025-09-30", 1_000_000_000, entity_cik=SUB)})

    ok, _ = b.patch_company(SUB, rec, facts, [Q3], 5)

    q = {r["period_end"]: r for r in rec["quarterly"]}["2025-09-30"]
    assert ok is True
    assert (q["revenue"], q["source"]) == (1_000_000_000, "filing")


# --------------------------------------------------------------------------
# A company several filings behind reaches its newest quarter (24 Sep 2026)
# --------------------------------------------------------------------------
def test_four_newer_filings_and_a_cap_of_three_patch_in_the_newest_quarter(b, tmp_path, monkeypatch):
    """Both builds rebuild from companyfacts before patching, so taking the OLDEST three read the
    same three filings every time and a company four behind (AUMN, EIDP) never reached its newest
    quarter. The window is now the newest three, still read oldest first."""
    monkeypatch.setattr(b, "PATCH_PER_COMPANY", 3)
    ends = ["2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30"]
    filings = [{"form": "10-K" if e.endswith("12-31") else "10-Q", "period": e, "accession": f"a{i}",
                "date": e} for i, e in enumerate(ends)]
    man = _manifest(**{str(SUB): (86, "2025-06-30")})
    _events(tmp_path, monkeypatch, b, **{str(SUB): list(reversed(filings))})

    (cik, window), = b.patch_targets(man)
    assert [f["period"] for f in window] == ends[1:]                  # newest three, oldest first

    rec, facts = _stored_record(b, SUB)
    _fake_sec(b, monkeypatch, {f["accession"]: _instance(f["period"], 1_000_000_000 + i, entity_cik=SUB)
                               for i, f in enumerate(filings)})
    ok, _ = b.patch_company(cik, rec, facts, window, 10)

    periods = {r["period_end"] for r in rec["quarterly"]}
    assert ok is True
    assert rec["checks"]["latest_quarter_end"] == "2026-06-30"
    assert "2026-06-30" in periods and "2025-09-30" not in periods     # the oldest is the one left out


def test_the_daily_run_uses_the_same_window(b):
    """`patch_companies.rebuild` must pick filings exactly as the weekly build does, or the daily
    run stops writing what the weekly build writes."""
    import inspect

    import patch_companies

    assert "patch_window(" in inspect.getsource(patch_companies.rebuild)
    assert b.patch_window([{"period": p} for p in "abcd"]) == [{"period": p} for p in "bcd"]
