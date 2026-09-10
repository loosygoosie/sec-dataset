"""`shares_diluted_as_filed` — what a fiscal year's own 10-K said, before any restatement.

companyfacts keeps the latest reported value for each fiscal year, and `_pick_latest` deliberately
prefers it ("restated comparatives win over the original"). A 10-K restates only the two or three
comparative years it prints, so after a split the recent years of `shares_diluted` sit on the new
basis and the older ones on the old one: the series steps by the split factor part-way through the
window. On 9 Sep 2026 ten of the thirty-six book holdings stepped inside their own six-year window,
Chipotle's by 49x, and `share_scale` read `ok` for eight of them — correctly, because one step is
exactly what an ordinary split looks like (NOTES.md section 9).

The point of the new field is NOT a smooth series. The as-filed series steps at the split too, and
it should: it is denominated in the shares of its own era, and it is paired with the RAW,
unadjusted price of that era. What is invariant is the product. That is the property these tests
assert, because it is the only one a consumer actually depends on.
"""
from __future__ import annotations

from conftest import doc, fact, fy_fact, shares, usd

DILUTED = "WeightedAverageNumberOfDilutedSharesOutstanding"
BASIC = "WeightedAverageNumberOfSharesOutstandingBasic"


def _row(b, d, fy_end):
    """The annual row for the year ending fy_end."""
    return next(r for r in b.normalise_company(d)["annual"] if r["period_end"] == fy_end)


def _reported_twice(pre, post, fy_end="2022-12-31", own="2023-02-01", later="2025-02-01"):
    """One fiscal year that companyfacts carries twice: the year's own 10-K, and a comparative in
    a later 10-K filed after a split. Revenue anchors the row so it is a real fiscal year."""
    return doc(us_gaap={
        "Revenues": usd(fy_fact(8_635_000_000, fy_end, filed=own)),
        DILUTED: shares(fy_fact(pre, fy_end, filed=own),
                        fy_fact(post, fy_end, filed=later)),
    })


# ------------------------------------------------------------------ the property that matters
def test_a_split_does_not_move_a_past_market_cap_computed_as_filed(b):
    """The whole point. A 50:1 split multiplies the share count and divides the price by the same
    50, so raw price x as-filed shares is the SAME market cap before and after — with no split
    factor anywhere, and nothing to detect or guess. Chipotle's June 2024 split is the shape:
    its raw June 2024 bar opens at $3,138.88 and closes at $62.65."""
    SPLIT = 50
    pre, raw_price = 27_962_000, 1_550.00
    row = _row(b, _reported_twice(pre, pre * SPLIT), "2022-12-31")

    as_filed_cap = row["shares_diluted_as_filed"] * raw_price
    post_split_cap = (pre * SPLIT) * (raw_price / SPLIT)
    assert as_filed_cap == post_split_cap == 43_341_100_000.0


def test_the_as_filed_series_still_steps_at_the_split_and_that_is_correct(b):
    """Guard against the wrong fix. A test asserting the as-filed series is SMOOTH would enshrine
    a second bug: each year is denominated in the shares of its own era, so the step belongs there
    and is cancelled by the raw price, not by the share count."""
    d = doc(us_gaap={
        "Revenues": usd(fy_fact(8_000_000_000, "2022-12-31", filed="2023-02-01"),
                        fy_fact(9_000_000_000, "2023-12-31", filed="2024-02-01")),
        DILUTED: shares(fy_fact(27_962_000, "2022-12-31", filed="2023-02-01"),
                        fy_fact(1_398_100_000, "2022-12-31", filed="2025-02-01"),   # restated 50x
                        fy_fact(1_400_000_000, "2023-12-31", filed="2024-02-01")),
    })
    a = {r["period_end"]: r for r in b.normalise_company(d)["annual"]}
    assert a["2022-12-31"]["shares_diluted_as_filed"] == 27_962_000
    assert a["2023-12-31"]["shares_diluted_as_filed"] == 1_400_000_000


# ------------------------------------------------------------------ selection
def test_the_earliest_filing_wins_for_as_filed(b):
    assert _row(b, _reported_twice(27_962_000, 1_398_100_000), "2022-12-31")["shares_diluted_as_filed"] \
        == 27_962_000


def test_the_restated_value_still_wins_for_shares_diluted(b):
    """The existing key does not change meaning. Pinned beside
    test_normaliser.py::test_the_latest_filing_wins_so_restatements_replace_originals."""
    assert _row(b, _reported_twice(27_962_000, 1_398_100_000), "2022-12-31")["shares_diluted"] \
        == 1_398_100_000


def test_a_year_reported_once_has_as_filed_equal_to_restated(b):
    """Most years, most companies. The field is present and agrees — not None."""
    d = doc(us_gaap={"Revenues": usd(fy_fact(8_000_000_000, "2022-12-31")),
                     DILUTED: shares(fy_fact(27_962_000, "2022-12-31"))})
    row = _row(b, d, "2022-12-31")
    assert row["shares_diluted_as_filed"] == row["shares_diluted"] == 27_962_000


def test_a_january_retailer_labelling_its_year_backwards_still_picks_its_own_filing(b):
    """The reason selection is on `filed` and not on `fy`. Filers disagree about what to call a
    fiscal year spanning two calendar years: Ross and Target name it for the year it began, TJX and
    Autodesk for the year it ended, with period ends days apart in late January. For a
    beginning-year filer the own-year fact carries fy=2025 while the period ends in 2026, and the
    NEXT year's 10-K prints that same period as a comparative carrying fy=2026 — the one an
    `fy == period's year` test would wrongly accept. No rule on `fy` can be right for both groups."""
    d = doc(us_gaap={
        "Revenues": usd(fy_fact(56_000_000_000, "2026-01-31", filed="2026-04-01", fy=2025)),
        DILUTED: shares(fy_fact(1_130_000_000, "2026-01-31", filed="2026-04-01", fy=2025),
                        fy_fact(2_260_000_000, "2026-01-31", filed="2027-04-01", fy=2026)),
    })
    assert _row(b, d, "2026-01-31")["shares_diluted_as_filed"] == 1_130_000_000


def test_a_fact_with_no_fiscal_year_focus_at_all_is_handled(b):
    """Every fixture in this suite omits `fy` by default, and real 20-F filers can too. The picker
    must never depend on it."""
    d = doc(us_gaap={"Revenues": usd(fy_fact(8_000_000_000, "2022-12-31", filed="2023-02-01")),
                     DILUTED: shares(fy_fact(27_962_000, "2022-12-31", filed="2023-02-01"),
                                     fy_fact(1_398_100_000, "2022-12-31", filed="2025-02-01"))})
    assert all("fy" not in f for f in d["facts"]["us-gaap"][DILUTED]["units"]["shares"])
    assert _row(b, d, "2022-12-31")["shares_diluted_as_filed"] == 27_962_000


def test_a_fact_with_no_filing_date_does_not_win_by_sorting_first(b):
    """`_filed_key` returns 0 for a missing date, which would sort FIRST under earliest-wins and
    hand the field a value from nowhere. The patch path can supply an empty `filed`."""
    undated = fact(999_999_999, "2022-12-31", start="2021-12-31", form="10-K", fp="FY")
    undated["filed"] = ""
    d = doc(us_gaap={"Revenues": usd(fy_fact(8_000_000_000, "2022-12-31", filed="2023-02-01")),
                     DILUTED: shares(undated,
                                     fy_fact(27_962_000, "2022-12-31", filed="2023-02-01"),
                                     fy_fact(1_398_100_000, "2022-12-31", filed="2025-02-01"))})
    assert _row(b, d, "2022-12-31")["shares_diluted_as_filed"] == 27_962_000


def test_an_amendment_filed_later_does_not_displace_the_original(b):
    """A 10-K/A filed after a split carries post-split comparatives like any later filing."""
    d = doc(us_gaap={
        "Revenues": usd(fy_fact(8_000_000_000, "2022-12-31", filed="2023-02-01")),
        DILUTED: shares(fy_fact(27_962_000, "2022-12-31", filed="2023-02-01"),
                        fy_fact(1_398_100_000, "2022-12-31", form="10-K/A", filed="2025-06-01")),
    })
    assert _row(b, d, "2022-12-31")["shares_diluted_as_filed"] == 27_962_000


def test_a_same_day_tie_is_broken_by_tag_preference(b):
    """Two tags reported in one filing: diluted outranks basic, exactly as `_pick_latest` orders."""
    d = doc(us_gaap={"Revenues": usd(fy_fact(8_000_000_000, "2022-12-31", filed="2023-02-01")),
                     DILUTED: shares(fy_fact(27_962_000, "2022-12-31", filed="2023-02-01")),
                     BASIC: shares(fy_fact(27_500_000, "2022-12-31", filed="2023-02-01"))})
    assert _row(b, d, "2022-12-31")["shares_diluted_as_filed"] == 27_962_000


def test_the_original_filing_beats_a_better_tag_in_a_later_one(b):
    """Ordering differs from `_pick_latest` on purpose. This year's own 10-K tagged only a basic
    count; a later 10-K restated it with a diluted one. Sorting tag-rank-first would hand the
    field that later diluted value — the restated number it exists to avoid. Preferring the
    original can mean preferring basic over diluted, which is what "as filed" means."""
    d = doc(us_gaap={"Revenues": usd(fy_fact(8_000_000_000, "2022-12-31", filed="2023-02-01")),
                     BASIC: shares(fy_fact(27_500_000, "2022-12-31", filed="2023-02-01")),
                     DILUTED: shares(fy_fact(1_398_100_000, "2022-12-31", filed="2025-02-01"))})
    row = _row(b, d, "2022-12-31")
    assert row["shares_diluted_as_filed"] == 27_500_000        # the original filing's own number
    assert row["shares_diluted"] == 1_398_100_000              # unchanged: best tag, latest filing


# ------------------------------------------------------------------ the basis date
def test_the_filing_date_of_each_count_is_emitted(b):
    """The load-bearing part. A share count is denominated in whatever split basis prevailed when
    it was FILED, so without that date no past market cap can be computed from it."""
    row = _row(b, _reported_twice(27_962_000, 1_398_100_000), "2022-12-31")
    assert row["shares_diluted_filed"] == "2025-02-01"            # the restated fact's own filing
    assert row["shares_diluted_as_filed_filed"] == "2023-02-01"   # the original's


def test_a_split_between_year_end_and_the_10k_makes_as_filed_already_post_split(b):
    """"As filed" does NOT mean "pre-split". ASC 260 makes a company restate share counts
    retroactively in any filing issued after a split, so a fiscal year whose own 10-K went out
    after one carries a post-split count. Walmart's FY2024 is the live instance: year end
    2024-01-31, 3:1 split 2024-02-26, 10-K filed 2024-03-15. Multiplying that by a RAW price from
    the fiscal year — when the stock was still pre-split — is wrong by exactly 3x. Only the
    emitted filing date reveals it, which is why it is emitted."""
    post = 8_415_000_000
    d = doc(us_gaap={
        "Revenues": usd(fy_fact(648_125_000_000, "2024-01-31", filed="2024-03-15")),
        DILUTED: shares(fy_fact(post, "2024-01-31", filed="2024-03-15")),
    })
    row = _row(b, d, "2024-01-31")
    assert row["shares_diluted_as_filed"] == post                 # already restated by the split
    assert row["shares_diluted_as_filed_filed"] == "2024-03-15"   # ...and dated after it

    raw_at_year_end, split = 165.0, 3
    naive = row["shares_diluted_as_filed"] * raw_at_year_end
    correct = row["shares_diluted_as_filed"] * (raw_at_year_end / split) * 1.0   # k = 1 after the split
    assert naive / correct == split                               # the trap, quantified


def test_a_fiscal_year_end_change_does_not_take_as_filed_from_the_other_period(b):
    """`_fy_of_period` buckets by the calendar year a period ENDS in, so a company that moves its
    year end can put two full-length periods in one bucket. `_pick_as_filed` sorts opposite to
    `_pick_latest`, so without a period guard it would describe the year the row does not name."""
    d = doc(us_gaap={
        "Revenues": usd(fact(5_000_000_000, "2022-03-31", start="2021-03-31", filed="2022-06-01"),
                        fact(7_000_000_000, "2022-12-31", start="2021-12-31", filed="2023-03-01")),
        DILUTED: shares(fact(11_000_000, "2022-03-31", start="2021-03-31", filed="2022-06-01"),
                        fact(99_000_000, "2022-12-31", start="2021-12-31", filed="2023-03-01")),
    })
    row = _row(b, d, "2022-12-31")
    assert row["shares_diluted"] == 99_000_000
    assert row["shares_diluted_as_filed"] == 99_000_000     # the row's OWN period, not 2022-03-31
    assert row["shares_diluted_as_filed_filed"] == "2023-03-01"


def test_a_mistagged_fiscal_year_focus_cannot_steer_the_pick(b):
    """Discriminates against an fy-primary picker, which the other tests do not: their fixtures
    omit `fy` entirely, so a `min(key=(fy, filed))` mutant ties and falls through to `filed`. Here
    the ORIGINAL carries a higher focus year than the restatement — a mis-tag, which the docstring
    claims immunity to — so an fy-primary picker returns the restated value and fails."""
    d = doc(us_gaap={
        "Revenues": usd(fy_fact(8_000_000_000, "2022-12-31", filed="2023-02-01")),
        DILUTED: shares(fy_fact(27_962_000, "2022-12-31", filed="2023-02-01", fy=2025),
                        fy_fact(1_398_100_000, "2022-12-31", filed="2025-02-01", fy=2024)),
    })
    assert _row(b, d, "2022-12-31")["shares_diluted_as_filed"] == 27_962_000


# ------------------------------------------------------------------ absence, not a fallback
def test_a_non_positive_as_filed_count_is_omitted_rather_than_written(b):
    """A reader must be able to tell "no original on file" from "original agrees with the
    restatement". Writing the restated value into the field would rebuild the defect."""
    d = doc(us_gaap={"Revenues": usd(fy_fact(8_000_000_000, "2022-12-31", filed="2023-02-01")),
                     DILUTED: shares(fy_fact(0, "2022-12-31", filed="2023-02-01"),
                                     fy_fact(1_398_100_000, "2022-12-31", filed="2025-02-01"))})
    row = _row(b, d, "2022-12-31")
    assert "shares_diluted_as_filed" not in row
    assert row["shares_diluted"] == 1_398_100_000


def test_a_company_with_no_share_facts_gets_no_as_filed_key(b):
    d = doc(us_gaap={"Revenues": usd(fy_fact(8_000_000_000, "2022-12-31"))})
    assert "shares_diluted_as_filed" not in _row(b, d, "2022-12-31")


# ------------------------------------------------------------------ the contract
def test_the_annual_row_keeps_every_key_a_consumer_already_reads(b):
    """Adding a field must not rename or drop one. These names are read by the book's tasks."""
    d = doc(us_gaap={"Revenues": usd(fy_fact(8_000_000_000, "2022-12-31")),
                     DILUTED: shares(fy_fact(27_962_000, "2022-12-31")),
                     "CommonStockSharesOutstanding": shares(fact(27_000_000, "2022-12-31"))})
    row = _row(b, d, "2022-12-31")
    for key in ("fiscal_year", "period_end", "filed", "revenue", "shares_diluted"):
        assert key in row, key


def test_the_new_field_is_not_in_share_items_so_checks_shares_keeps_its_meaning(b):
    """`checks.shares` drives three book prompts. Widening SHARE_ITEMS would flip real companies
    to `invalid:shares_diluted_as_filed` — a change in the meaning of an existing key."""
    assert b.SHARE_ITEMS == ("shares_diluted", "shares_outstanding")
    assert "shares_diluted_as_filed" not in b.SHARE_ITEMS


def test_the_new_field_is_not_a_concept_so_it_cannot_create_a_phantom_quarter(b):
    """`flow_names` is built from CONCEPTS and decides which quarterly rows survive the cover-page
    filter. Registering the field there could let a quarter carrying only it survive."""
    assert "shares_diluted_as_filed" not in b.CONCEPTS
    assert b.ASFILED_ITEMS == ("shares_diluted",)
