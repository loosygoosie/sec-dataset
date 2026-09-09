"""Regression tests over the published data itself, not synthetic input.

The share-count defect was invisible to unit tests because nothing looked at what the build
actually wrote: a whole index of negative counts sat in data/companies/ while every file's own
checks block said "ok". These tests read the committed dataset and assert the guarantees that
failure broke, so a rebuild that reintroduces it fails CI instead of shipping.

They assert what the pipeline is responsible for. A handful of filers tag share counts that are
wrong at source — off by a factor of a thousand, or a count ten times the real one carried in the
annual row — and those are not something the normaliser can invent its way out of. The aggregate
band below is set to catch a systemic regression while tolerating that known tail; see the
session notes for the specific filers.
"""
from __future__ import annotations

import json
import pathlib
import statistics

import pytest

COMPANIES = pathlib.Path(__file__).resolve().parents[1] / "data" / "companies"
SHARE_ITEMS = ("shares_diluted", "shares_outstanding")

pytestmark = pytest.mark.skipif(not COMPANIES.is_dir(), reason="no published dataset in this checkout")


@pytest.fixture(scope="module")
def dataset():
    return [json.loads(p.read_text()) for p in COMPANIES.glob("*.json")]


def _derived(rec):
    return [r for r in rec["quarterly"] if "derived from YTD" in (r.get("form") or "")]


def test_no_year_to_date_derived_row_carries_a_negative_share_count(dataset):
    """The defect itself: the fiscal-year quarter was FY minus nine months of a weighted
    average, which came out at roughly minus twice the real count on 479 of 500 constituents."""
    offenders = [(rec["cik"], r["period_end"], item, r[item])
                 for rec in dataset for r in _derived(rec) for item in SHARE_ITEMS
                 if (r.get(item) or 0) < 0]

    assert offenders == [], f"{len(offenders)} derived rows carry a negative share count: {offenders[:5]}"


def test_no_company_reports_shares_ok_while_carrying_a_bad_count(dataset):
    """The reason it went unnoticed: 5,751 affected companies said "shares": "ok"."""
    offenders = [rec["cik"] for rec in dataset
                 if rec["checks"]["shares"] == "ok"
                 and any((r.get(item) is not None and r[item] <= 0)
                         for rows in (rec["annual"], rec["quarterly"]) for r in rows for item in SHARE_ITEMS)]

    assert offenders == [], f"{len(offenders)} companies report ok over a non-positive count: {offenders[:5]}"


def test_a_bad_share_count_is_always_flagged_invalid(dataset):
    """The converse: wherever a non-positive count survives from the source, the file says so."""
    unflagged = [rec["cik"] for rec in dataset
                 if any((r.get(item) is not None and r[item] <= 0)
                        for rows in (rec["annual"], rec["quarterly"]) for r in rows for item in SHARE_ITEMS)
                 and not rec["checks"]["shares"].startswith("invalid")]

    assert unflagged == []


def test_derived_share_counts_sit_beside_their_neighbouring_quarters(dataset):
    """A derived count should look like the company's other quarters. Stated in aggregate: the
    old behaviour put essentially every one of these far out of band and negative, so a
    regression is unmissable here, while the few hundred filers with a source-side scale error
    do not turn the suite red."""
    devs = []
    for rec in dataset:
        pos = [r["shares_diluted"] for r in rec["quarterly"] if (r.get("shares_diluted") or 0) > 0]
        if len(pos) < 4:
            continue
        median = statistics.median(pos)
        devs += [max(v / median, median / v) for r in _derived(rec)
                 if (v := r.get("shares_diluted")) and v > 0]

    assert len(devs) > 1000, "expected the dataset to contain derived share counts to check"
    assert statistics.median(devs) < 1.1
    assert sum(1 for d in devs if d < 2) / len(devs) > 0.85


def test_apple_fiscal_year_quarter_matches_its_annual_count(dataset):
    """The reported case, pinned by name: -30,150,480,000 against a true ~15bn."""
    apple = next(rec for rec in dataset if rec["cik"] == 320193)
    fy = next(r for r in apple["quarterly"] if r["period_end"] == "2025-09-27")
    annual = next(a for a in apple["annual"] if a["fiscal_year"] == 2025)

    assert fy["shares_diluted"] > 0
    assert fy["shares_diluted"] == annual["shares_diluted"]
    assert 14e9 < fy["shares_diluted"] < 16e9


def test_flows_on_a_derived_row_are_still_derived(dataset):
    """The fix must not have stopped revenue being differenced out of year-to-date."""
    apple = next(rec for rec in dataset if rec["cik"] == 320193)
    fy = next(r for r in apple["quarterly"] if r["period_end"] == "2025-09-27")

    assert 90e9 < fy["revenue"] < 115e9        # Apple's Q4 FY2025, not the 416bn full year
