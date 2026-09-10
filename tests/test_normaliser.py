"""Tests for build_sec_dataset.py's normaliser, on synthetic companyfacts documents.

Every case here is a shape the SEC bulk file actually contains and the pipeline has
a deliberate rule for — a filer that renames its revenue tag mid-decade, a utility
that tags a token PP&E line beside its real construction spend, a 10-Q that reports
cash flow year-to-date only. The tests pin the rule, not the implementation: they
asks what value a reader ends up with, and what the file says about how far to
trust it.

No network, no fixtures on disk: each test builds the few facts it needs.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from conftest import doc, fact, fy_fact, shares, usd, ytd_fact


# --------------------------------------------------------------------------
# Tag resolution: the same line item under different names
# --------------------------------------------------------------------------
def test_revenue_tag_switch_mid_decade_keeps_every_year(b):
    """Companies renamed revenue when ASC 606 landed. Taking 'the first tag with any
    data' would silently drop either the early years or the recent ones."""
    old_years = {"2019-12-31": 10_000_000_000, "2020-12-31": 11_000_000_000, "2021-12-31": 12_000_000_000}
    new_years = {"2022-12-31": 13_000_000_000, "2023-12-31": 14_000_000_000, "2024-12-31": 15_000_000_000}
    d = doc(us_gaap={
        "Revenues": usd(*[fy_fact(v, e) for e, v in old_years.items()]),
        "RevenueFromContractWithCustomerExcludingAssessedTax": usd(*[fy_fact(v, e) for e, v in new_years.items()]),
    })

    norm = b.normalise_company(d)
    got = {r["fiscal_year"]: r.get("revenue") for r in norm["annual"]}

    assert got == {2019: 10_000_000_000, 2020: 11_000_000_000, 2021: 12_000_000_000,
                   2022: 13_000_000_000, 2023: 14_000_000_000, 2024: 15_000_000_000}
    assert norm["tags_used"]["revenue"] == "Revenues,RevenueFromContractWithCustomerExcludingAssessedTax"


def test_dominant_pick_takes_a_lower_ranked_tag_that_is_much_larger(b):
    """A financial tags contract revenue (a component) beside its real total. The
    preferred tag loses when another is at least 3x bigger."""
    d = doc(us_gaap={
        "Revenues": usd(fy_fact(1_000_000_000, "2024-12-31")),                    # rank 1, a component
        "TotalRevenuesAndOtherIncome": usd(fy_fact(5_000_000_000, "2024-12-31")),  # rank 5, the real total
    })

    assert b.normalise_company(d)["annual"][-1]["revenue"] == 5_000_000_000


def test_dominant_pick_keeps_the_preferred_tag_below_the_3x_threshold(b):
    """Merely larger is not enough — otherwise any bigger neighbouring line would win."""
    d = doc(us_gaap={
        "Revenues": usd(fy_fact(1_000_000_000, "2024-12-31")),
        "TotalRevenuesAndOtherIncome": usd(fy_fact(2_000_000_000, "2024-12-31")),
    })

    assert b.normalise_company(d)["annual"][-1]["revenue"] == 1_000_000_000


def test_max_pick_for_capex_takes_the_real_construction_spend(b):
    """A regulated utility tags a token PP&E line and its actual construction budget."""
    d = doc(us_gaap={
        "NetIncomeLoss": usd(fy_fact(500_000_000, "2024-12-31")),
        "PaymentsToAcquirePropertyPlantAndEquipment": usd(fy_fact(50_000_000, "2024-12-31")),
        "PaymentsForConstructionInProcess": usd(fy_fact(3_000_000_000, "2024-12-31")),
    })

    assert b.normalise_company(d)["annual"][-1]["capex"] == 3_000_000_000


def test_max_pick_for_total_debt_ignores_a_token_long_term_debt_line(b):
    """total_debt is an instant, so it reaches the annual row via the balance sheet at
    year end rather than through annual_rows."""
    d = doc(us_gaap={
        "NetIncomeLoss": usd(fy_fact(500_000_000, "2024-12-31")),
        "LongTermDebt": usd(fact(23_000_000, "2024-12-31")),
        "DebtAndCapitalLeaseObligations": usd(fact(14_000_000_000, "2024-12-31")),
    })

    assert b.normalise_company(d)["annual"][-1]["total_debt"] == 14_000_000_000


def test_the_latest_filing_wins_so_restatements_replace_originals(b):
    d = doc(us_gaap={"NetIncomeLoss": usd(
        fy_fact(900_000_000, "2024-12-31", filed="2025-02-01"),
        fy_fact(850_000_000, "2024-12-31", filed="2026-02-01"),   # restated a year later
    )})

    assert b.normalise_company(d)["annual"][-1]["net_income"] == 850_000_000


# --------------------------------------------------------------------------
# Quarters: genuine 3-month facts, and the ones that have to be derived
# --------------------------------------------------------------------------
FY24 = "2024-01-01"


def _ocf_ytd(**overrides):
    """A calendar-2024 cash-flow series as a 10-Q files it: cumulative, not per quarter."""
    ytd = {"2024-03-31": 100_000_000, "2024-06-30": 250_000_000, "2024-09-30": 400_000_000}
    ytd.update(overrides.pop("ytd", {}))
    for k in overrides.pop("drop", []):
        ytd.pop(k)
    facts = [ytd_fact(v, FY24, e) for e, v in ytd.items()]
    facts.append(ytd_fact(600_000_000, FY24, "2024-12-31", form="10-K", fp="FY"))
    return doc(us_gaap={"NetCashProvidedByUsedInOperatingActivities": usd(*facts)})


def test_ytd_cash_flow_is_differenced_into_single_quarters(b):
    norm = b.normalise_company(_ocf_ytd())
    got = {r["period_end"]: r["operating_cash_flow"] for r in norm["quarterly"]}

    assert got == {"2024-03-31": 100_000_000,   # 3M as filed
                   "2024-06-30": 150_000_000,   # 6M - 3M
                   "2024-09-30": 150_000_000,   # 9M - 6M
                   "2024-12-31": 200_000_000}   # FY - 9M
    assert norm["annual"][-1]["operating_cash_flow"] == 600_000_000


def test_a_derived_quarter_says_so_in_its_form_field(b):
    rows = {r["period_end"]: r["form"] for r in b.normalise_company(_ocf_ytd())["quarterly"]}

    assert "derived from YTD" in rows["2024-06-30"]
    assert "derived from YTD" not in rows["2024-03-31"]   # a genuine 3-month fact


def test_a_missing_prior_quarter_is_refused_not_absorbed(b):
    """Without the 6M fact, Q3 cannot be derived: 9M minus 3M would silently book two
    quarters of cash flow as one. The pipeline declines instead."""
    norm = b.normalise_company(_ocf_ytd(drop=["2024-06-30"]))
    got = {r["period_end"]: r["operating_cash_flow"] for r in norm["quarterly"]}

    assert got == {"2024-03-31": 100_000_000}
    assert 300_000_000 not in got.values()      # 9M - 3M, the number we must not produce


def test_a_genuine_three_month_fact_beats_the_derivation(b):
    """When the company tags the quarter itself, that value is used verbatim."""
    facts = [ytd_fact(100_000_000, FY24, "2024-03-31"),
             ytd_fact(250_000_000, FY24, "2024-06-30"),
             fact(155_000_000, "2024-06-30", start="2024-04-01", form="10-Q", fp="Q2")]
    d = doc(us_gaap={"NetCashProvidedByUsedInOperatingActivities": usd(*facts)})

    rows = {r["period_end"]: r["operating_cash_flow"] for r in b.normalise_company(d)["quarterly"]}

    assert rows["2024-06-30"] == 155_000_000    # not the 150m the subtraction would give


# --------------------------------------------------------------------------
# The dei: prefix, and cover-page facts that are not quarters
# --------------------------------------------------------------------------
def test_dei_prefixed_tags_are_read_from_the_dei_namespace(b):
    d = doc(dei={"EntityCommonStockSharesOutstanding": shares(fact(1_000_000, "2025-02-14"))})

    series, tag = b.extract_series(d, b.CONCEPTS["shares_outstanding"]["tags"], "shares")

    assert tag == "dei:EntityCommonStockSharesOutstanding"
    assert [f["val"] for f in series] == [1_000_000]


def test_a_cover_page_share_count_does_not_invent_a_quarter(b):
    """EntityCommonStockSharesOutstanding is dated the filing date, not a period end.
    A row carrying only instants is not a quarter and must be dropped."""
    d = doc(us_gaap={"NetCashProvidedByUsedInOperatingActivities": usd(
                ytd_fact(100_000_000, FY24, "2024-03-31"))},
            dei={"EntityCommonStockSharesOutstanding": shares(fact(1_000_000, "2025-02-14"))})

    ends = [r["period_end"] for r in b.normalise_company(d)["quarterly"]]

    assert ends == ["2024-03-31"]
    assert "2025-02-14" not in ends


# --------------------------------------------------------------------------
# Fiscal-year labelling
# --------------------------------------------------------------------------
@pytest.mark.parametrize("end, expected", [
    ("2025-12-31", 2025),
    ("2026-03-31", 2026),   # Deckers: year ending in March is that calendar year
    ("2025-08-31", 2025),   # Costco
    ("2026-01-03", 2025),   # Snap-on: a 52/53-week year ending days into January
    ("2026-01-07", 2025),
    ("2026-01-08", 2026),   # past the cutoff, a genuine January year end
])
def test_fiscal_year_is_labelled_by_the_year_the_period_ends_in(b, end, expected):
    assert b._fy_of_period({"end": end}, None) == expected


@pytest.mark.parametrize("today, expected", [
    ("2026-09-08", "2023-09-08"),
    ("2028-02-29", "2025-02-28"),   # the year three back is never a leap year
    ("2024-02-29", "2021-02-28"),
    ("2028-03-01", "2025-03-01"),
])
def test_the_silent_filer_cutoff_survives_a_leap_day(b, today, expected):
    assert b._years_ago(date.fromisoformat(today), 3).isoformat() == expected


# --------------------------------------------------------------------------
# data_checks: what the file says about how far to trust itself
# --------------------------------------------------------------------------
BILLION = 1_000_000_000


def _year_and_quarters(annual=BILLION, quarters=(250_000_000,) * 4, fy_end="2024-12-31"):
    ends = ["2024-03-31", "2024-06-30", "2024-09-30", "2024-12-31"]
    ann = [{"fiscal_year": 2024, "period_end": fy_end,
            "revenue": annual, "net_income": annual, "operating_cash_flow": annual, "capex": annual}]
    qtr = [{"period_end": e, "revenue": v, "net_income": v, "operating_cash_flow": v, "capex": v}
           for e, v in zip(ends, quarters)]
    return ann, qtr


def test_four_quarters_that_sum_to_the_year_reconcile(b):
    checks = b.data_checks(*_year_and_quarters(), tags_used={})

    assert checks["reconciles"] == "ok"
    assert checks["reconciled_fy"] == 2024


def test_quarters_that_miss_the_year_are_flagged_off_with_the_items(b):
    ann, qtr = _year_and_quarters(quarters=(300_000_000,) * 4)   # sums to 1.2bn against 1.0bn

    checks = b.data_checks(ann, qtr, tags_used={})

    assert checks["reconciles"].startswith("off:")
    for item in ("revenue", "net_income", "operating_cash_flow", "capex"):
        assert item in checks["reconciles"]


def test_a_rounding_sized_gap_is_not_flagged(b):
    ann, qtr = _year_and_quarters(quarters=(250_000_000, 250_000_000, 250_000_000, 251_000_000))

    assert b.data_checks(ann, qtr, tags_used={})["reconciles"] == "ok"


def test_a_year_without_four_quarters_is_not_available_rather_than_wrong(b):
    ann, qtr = _year_and_quarters()

    checks = b.data_checks(ann, qtr[:3], tags_used={})

    assert checks["reconciles"] == "n/a"
    assert checks["reconciled_fy"] is None


def test_quarter_age_days_is_measured_from_the_latest_quarter_end(b):
    latest = date.today() - timedelta(days=40)
    qtr = [{"period_end": latest.isoformat(), "revenue": 1}]

    checks = b.data_checks([], qtr, tags_used={})

    assert checks["latest_quarter_end"] == latest.isoformat()
    assert checks["quarter_age_days"] == 40


def test_no_quarters_at_all_leaves_the_age_unknown(b):
    checks = b.data_checks([], [], tags_used={})

    assert checks["latest_quarter_end"] is None
    assert checks["quarter_age_days"] is None


DIL = "WeightedAverageNumberOfDilutedSharesOutstanding"
BOTH = "WeightedAverageNumberOfShareOutstandingBasicAndDiluted"
BASIC = "WeightedAverageNumberOfSharesOutstandingBasic"
OUT = "dei:EntityCommonStockSharesOutstanding"


@pytest.mark.parametrize("tags_used, row, expected", [
    ({"shares_diluted": DIL},   {"shares_diluted": 1_000_000}, "ok"),
    ({"shares_diluted": BOTH},  {"shares_diluted": 1_000_000}, "ok"),
    ({"shares_diluted": BASIC}, {"shares_diluted": 1_000_000}, "basic-only"),
    ({"shares_diluted": None, "shares_outstanding": OUT}, {"shares_outstanding": 1_000_000}, "outstanding-only"),
    ({"shares_diluted": None, "shares_outstanding": None}, {}, "none"),
    ({}, {}, "none"),
    # the tag resolved and nothing landed behind it: for a year this read "ok"
    ({"shares_diluted": DIL}, {}, "none"),
    ({"shares_diluted": DIL}, {"shares_outstanding": 1_000_000}, "outstanding-only"),
])
def test_the_shares_flag_says_which_per_share_tests_a_reader_can_run(b, tags_used, row, expected):
    """Multi-class filers tag share counts by class, and companyfacts drops dimensioned
    facts, so the count is simply absent. A reader must flag that, not score it as zero.

    The flag is read off the VALUES. Until 9 Sep 2026 it was read off the tag map, and this
    test passed no rows at all — so both the code and the test agreed that a resolved tag
    meant usable data, and neither of them ever looked. That is how 76 companies came to
    promise a per-share figure they could not supply."""
    qtr = [{"period_end": "2026-06-30", **row}]
    assert b.data_checks([], qtr, tags_used=tags_used)["shares"] == expected


def test_the_shares_flag_reads_the_window_a_consumer_uses(b):
    """The flag's third form and its third bug, found 10 Sep 2026 by a consumer.

    §2 moved it from "which tag resolved" to "does a value exist". It then read `any` over every
    annual and quarterly row the file holds — and "exists anywhere" is not "exists where a reader
    will look". Regency Centers last tagged a diluted count for FY2020 and J.M. Smucker for
    FY2022; every row since is empty in both, and both reported `ok`. 162 companies were in that
    state, 2 of them in the S&P 500.

    This is the Regency shape: a count five years back, nothing since. It must NOT read `ok`, and
    where a cover-page count survives it should say `outstanding-only` — which is exactly what a
    consumer needs to know, since that is the only basis left to it."""
    ann = ([{"period_end": f"{y}-12-31", "shares_diluted": 170_000_000, "shares_outstanding": 170_000_000}
            for y in (2018, 2019, 2020)]
           + [{"period_end": f"{y}-12-31", "shares_outstanding": 180_000_000}
              for y in (2021, 2022, 2023, 2024, 2025)])
    qtr = [{"period_end": "2026-06-30", "shares_outstanding": 180_000_000}]
    assert b.data_checks(ann, qtr, tags_used={"shares_diluted": DIL})["shares"] == "outstanding-only"


def test_a_current_diluted_count_still_reads_ok(b):
    """The other half: narrowing the window must not start failing companies that are fine. A
    count in the recent rows is usable however long the history behind it runs."""
    ann = [{"period_end": f"{y}-12-31", "shares_diluted": 1_000_000} for y in range(2018, 2026)]
    qtr = [{"period_end": "2026-06-30", "shares_diluted": 1_000_000}]
    assert b.data_checks(ann, qtr, tags_used={"shares_diluted": DIL})["shares"] == "ok"


def test_a_non_positive_count_is_caught_wherever_it_landed(b):
    """The zero/negative scan deliberately still reads the WHOLE history while the window above
    narrowed. A count of zero or less is a defect whenever it happened, and narrowing that scan
    with the other would have quietly stopped reporting old ones."""
    ann = [{"period_end": "2018-12-31", "shares_diluted": -5}] + \
          [{"period_end": f"{y}-12-31", "shares_diluted": 1_000_000} for y in range(2019, 2026)]
    qtr = [{"period_end": "2026-06-30", "shares_diluted": 1_000_000}]
    assert b.data_checks(ann, qtr, tags_used={"shares_diluted": DIL})["shares"] == "invalid:shares_diluted"


def test_the_shares_flag_survives_the_whole_pipeline(b):
    d = doc(us_gaap={
        "NetIncomeLoss": usd(fy_fact(500_000_000, "2024-12-31")),
        "WeightedAverageNumberOfSharesOutstandingBasic": shares(fy_fact(1_000_000, "2024-12-31")),
    })
    norm = b.normalise_company(d)

    assert b.data_checks(norm["annual"], norm["quarterly"], norm["tags_used"])["shares"] == "basic-only"


# --------------------------------------------------------------------------
# Non-additive items: a weighted-average share count is not a sum of quarters
# --------------------------------------------------------------------------
def _apple_fy2025_shares():
    """Apple's FY2025 diluted count as filed: three quarterly averages, a nine-month average,
    and the fiscal year's own average in the 10-K. Nothing here is a running total."""
    return [
        fact(15_050_000_000, "2024-12-28", start="2024-09-29", form="10-Q", fp="Q1"),
        fact(15_000_000_000, "2025-03-29", start="2024-12-29", form="10-Q", fp="Q2"),
        fact(14_948_179_000, "2025-06-28", start="2025-03-30", form="10-Q", fp="Q3"),
        fact(15_050_000_000, "2025-06-28", start="2024-09-29", form="10-Q", fp="Q3"),
        fact(15_004_697_000, "2025-09-27", start="2024-09-29", form="10-K", fp="FY"),
    ]


def test_a_weighted_average_share_count_is_taken_as_filed_not_differenced(b):
    """Subtracting nine months of a weighted average from the year gives roughly minus twice the
    real count: Apple's fiscal-year quarter read -30,150,480,000 against a true ~15bn."""
    q = b.quarterly_rows(_apple_fy2025_shares(), "flow", additive=False)

    assert q["2025-09-27"]["val"] == 15_004_697_000


def test_differencing_a_weighted_average_is_what_produced_the_negative(b):
    """The old behaviour, kept as a test so the defect cannot come back unnoticed."""
    q = b.quarterly_rows(_apple_fy2025_shares(), "flow", additive=True)

    assert q["2025-09-27"]["val"] < 0


def test_the_share_count_stays_in_band_with_its_neighbouring_quarters(b):
    q = b.quarterly_rows(_apple_fy2025_shares(), "flow", additive=False)
    vals = [q[e]["val"] for e in sorted(q)]

    assert min(vals) > 0
    assert max(vals) / min(vals) < 1.1


def test_a_value_taken_as_filed_is_not_labelled_a_derivation(b):
    q = b.quarterly_rows(_apple_fy2025_shares(), "flow", additive=False)

    assert q["2025-09-27"].get("_derived") is None


def test_flows_on_the_same_filing_are_still_differenced(b):
    """The fix must not stop revenue or cash flow being derived — only averages."""
    q = b.quarterly_rows([
        ytd_fact(100_000_000, FY24, "2024-03-31"),
        ytd_fact(250_000_000, FY24, "2024-06-30"),
    ], "flow", additive=True)

    assert q["2024-06-30"]["val"] == 150_000_000
    assert q["2024-06-30"]["_derived"]


def test_the_shares_concept_is_declared_non_additive(b):
    """The wiring, not just the mechanism: a weighted average must never be summed."""
    assert b.CONCEPTS["shares_diluted"].get("additive") is False
    assert all(spec.get("additive", True) for name, spec in b.CONCEPTS.items() if name != "shares_diluted")


def test_apple_shaped_company_ends_with_a_sane_fiscal_year_quarter(b):
    """End to end through normalise_company, the shape that shipped the defect."""
    d = doc(us_gaap={
        "Revenues": usd(*[ytd_fact(v, "2024-09-29", e, form=fm, fp=fp) for v, e, fm, fp in [
            (100_000_000_000, "2024-12-28", "10-Q", "Q1"), (200_000_000_000, "2025-03-29", "10-Q", "Q2"),
            (300_000_000_000, "2025-06-28", "10-Q", "Q3"), (400_000_000_000, "2025-09-27", "10-K", "FY")]]),
        "WeightedAverageNumberOfDilutedSharesOutstanding": shares(*_apple_fy2025_shares()),
    })

    rows = {r["period_end"]: r for r in b.normalise_company(d)["quarterly"]}

    assert rows["2025-09-27"]["shares_diluted"] == 15_004_697_000
    assert rows["2025-09-27"]["revenue"] == 100_000_000_000      # the flow is still differenced


# --------------------------------------------------------------------------
# The check that should have caught it
# --------------------------------------------------------------------------
def test_a_negative_share_count_fails_the_check_instead_of_reading_ok(b):
    """478 of 479 affected companies reported "shares": "ok" while carrying a negative count."""
    qtr = [{"period_end": "2025-09-27", "shares_diluted": -30_150_480_000}]

    checks = b.data_checks([], qtr, tags_used={"shares_diluted": "WeightedAverageNumberOfDilutedSharesOutstanding"})

    assert checks["shares"].startswith("invalid")
    assert "shares_diluted" in checks["shares"]


def test_a_zero_share_count_also_fails(b):
    """No per-share figure can be computed from zero either."""
    checks = b.data_checks([], [{"period_end": "2020-06-30", "shares_outstanding": 0}], tags_used={})

    assert checks["shares"] == "invalid:shares_outstanding"


def test_a_bad_count_in_an_annual_row_fails_too(b):
    checks = b.data_checks([{"fiscal_year": 2025, "shares_diluted": -1}], [], tags_used={})

    assert checks["shares"].startswith("invalid")


def test_the_check_names_every_affected_item(b):
    checks = b.data_checks([], [{"period_end": "2025-09-27", "shares_diluted": -1, "shares_outstanding": 0}],
                           tags_used={})

    assert checks["shares"] == "invalid:shares_diluted,shares_outstanding"


def test_healthy_share_counts_still_report_their_normal_flag(b):
    qtr = [{"period_end": "2025-09-27", "shares_diluted": 15_004_697_000, "shares_outstanding": 14_773_260_000}]

    checks = b.data_checks([], qtr, tags_used={"shares_diluted": "WeightedAverageNumberOfDilutedSharesOutstanding"})

    assert checks["shares"] == "ok"


def test_retained_earnings_is_carried_for_altmans_second_term(b):
    """Added 10 Sep 2026. The book's screen scored Altman Z from a vendor's arithmetic until FMP
    was removed; its X2 term is retained earnings over total assets, and no other field here
    stands in for it — `total_equity` nets in paid-in capital and buybacks, so a company that has
    bought back stock can show negative equity on decades of retained profit."""
    d = doc(us_gaap={
        "Revenues": usd(fy_fact(8_000_000_000, "2025-12-31")),
        "RetainedEarningsAccumulatedDeficit": usd(fact(21_000_000_000, "2025-12-31")),
        "Assets": usd(fact(60_000_000_000, "2025-12-31")),
    })
    row = b.normalise_company(d)["annual"][-1]
    assert row["retained_earnings"] == 21_000_000_000
    assert row["total_assets"] == 60_000_000_000


def test_an_accumulated_deficit_keeps_the_sign_the_filer_gave_it(b):
    """A deficit is the same concept with a negative value. Taking its absolute value would turn a
    loss-making balance sheet into a strong Altman score."""
    d = doc(us_gaap={
        "Revenues": usd(fy_fact(1_000_000_000, "2025-12-31")),
        "RetainedEarningsAccumulatedDeficit": usd(fact(-4_500_000_000, "2025-12-31")),
    })
    assert b.normalise_company(d)["annual"][-1]["retained_earnings"] == -4_500_000_000


# --------------------------------------------------------------- the top line

def test_a_sub_item_wearing_the_preferred_tag_is_repaired(b):
    """DTE Energy: $61m of revenue against $2.374bn of operating income.

    `_pick_latest` takes the highest-PREFERENCE tag holding any value for the period, so a filer
    who tags a sub-item as `Revenues` beats one who tags the consolidated total under a
    less-preferred name. Where a larger candidate exists for the same period, re-making the pick is
    a strict improvement.
    """
    row = {"revenue": 61_000_000, "operating_income": 2_374_000_000,
           "pretax_income": 1_550_000_000, "net_income": 1_462_000_000}
    assert b.top_line_repair(row, [{"val": 61_000_000}, {"val": 13_200_000_000}]) is None
    assert row["revenue"] == 13_200_000_000


def test_an_unrepairable_top_line_is_flagged_not_silently_kept(b):
    """Synchrony: only `NoninterestIncome` is tagged, so there is nothing larger to swap in.

    Every margin, growth rate and conversion ratio for that year divides by this number, so the
    reader has to be told. The value is left alone — this module does not invent one — and the
    caller turns the return into `checks.revenue`.
    """
    row = {"revenue": 520_000_000, "operating_income": None,
           "pretax_income": 4_621_000_000, "net_income": 3_552_000_000}
    assert b.top_line_repair(row, [{"val": 520_000_000}]) == "below-income"
    assert row["revenue"] == 520_000_000


def test_a_sound_top_line_is_never_touched(b):
    """The check must fire on roughly 1% of filers, not reshape the other 99%."""
    row = {"revenue": 100_000_000_000, "operating_income": 20_000_000_000,
           "net_income": 15_000_000_000}
    assert b.top_line_repair(row, [{"val": 100_000_000_000}, {"val": 5_000_000}]) is None
    assert row["revenue"] == 100_000_000_000


def test_a_one_off_gain_does_not_trigger_a_repair(b):
    """Net income can legitimately approach revenue after a divestiture. The floor is the MAX of
    the income lines, so this only fires when one genuinely EXCEEDS the top line."""
    row = {"revenue": 1_000_000_000, "operating_income": 100_000_000,
           "net_income": 950_000_000}
    assert b.top_line_repair(row, [{"val": 1_000_000_000}]) is None


def test_checks_carries_revenue_ok_by_default(b):
    """Every existing consumer reads `checks` by field name. A new key is fine; a changed meaning
    is not, so the ~99% of sound filers must read a plain "ok"."""
    ann = [{"fiscal_year": 2025, "period_end": "2025-12-31", "revenue": 1e9, "net_income": 1e8}]
    assert b.data_checks(ann, [], {}, None)["revenue"] == "ok"
    assert b.data_checks(ann, [], {}, [2024, 2025])["revenue"] == "below-income:2024,2025"
