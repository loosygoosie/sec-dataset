"""The share-scale check, and the `shares` flag it sits beside.

Both exist because of the same discovery: a company can carry share counts that are internally
impossible while every flag in its file says the data is fine. `shares` said "ok" whenever a
diluted TAG resolved, whether or not a single value landed behind it, and nothing at all looked
at whether the values were on one scale. On 9 Sep 2026 that was 76 companies promising a
per-share figure they could not supply, and 28 of the S&P 500 whose share series cannot be used
for one at all.

The rules are deliberately blunt. `scale` compares a row against itself, `levels` compares a
series against itself, and neither needs to know what the right answer is — only that these
numbers cannot all be true at once.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from build_sec_dataset import data_checks, share_scale  # noqa: E402


def q(end, dil=None, out=None):
    r = {"period_end": end}
    if dil is not None:
        r["shares_diluted"] = dil
    if out is not None:
        r["shares_outstanding"] = out
    return r


# --------------------------------------------------------------------------- scale
def test_diluted_far_above_outstanding_is_a_scale_error():
    """Waters: 98,204,000,000 diluted against 98m outstanding. No split is a thousand to one."""
    rows = [q("2026-06-30", 98_204_000_000, 98_225_000)]
    assert share_scale([], rows) == "suspect:scale"


def test_diluted_far_below_outstanding_is_a_scale_error():
    """McDonald's files 716.4 for 716 million shares — the figure tagged in millions."""
    assert share_scale([], [q("2025-12-31", 716.4, 707_641_531)]) == "suspect:scale"


def test_a_real_gap_between_diluted_and_outstanding_is_not_flagged():
    """Diluted exceeds outstanding by the dilution; a tenth of a percent, not fifty times."""
    assert share_scale([], [q("2026-06-30", 391_804_000, 371_057_782)]) == "ok"


# --------------------------------------------------------------------------- levels
def test_one_step_is_a_split_and_is_left_alone():
    """A 10:1 split moves the series once and leaves it there. The README tells readers to
    expect exactly this, so flagging it would make the check noise."""
    rows = [q("2025-03-31", 40_000_000), q("2025-06-30", 40_100_000),
            q("2025-09-30", 401_000_000), q("2025-12-31", 402_000_000)]
    assert share_scale([], rows) == "ok"


def test_a_series_that_comes_back_is_flagged():
    """KLA: fiscal-year rows ten times its own interim quarters, over and over."""
    rows = [q("2025-03-31", 133_303_000), q("2025-06-30", 1_337_502_000),
            q("2025-09-30", 132_381_000), q("2026-06-30", 1_319_633_000)]
    assert share_scale([], rows) == "suspect:levels"


def test_a_plateau_is_flagged_not_just_a_spike():
    """Booking runs two quarters near 33m then two near 800m. A three-point spike test walks
    past this; counting level changes does not."""
    rows = [q("2024-09-30", 33_864_000), q("2024-12-31", 34_064_000),
            q("2025-03-31", 827_000_000), q("2025-06-30", 815_000_000),
            q("2025-09-30", 32_558_000), q("2025-12-31", 32_639_000)]
    assert share_scale([], rows) == "suspect:levels"


def test_a_company_sitting_near_a_power_of_ten_is_not_flagged():
    """Goldman holds ~3.1e8 shares, either side of 10^8.5. Grouping by rounded magnitude made a
    3% move look like a change of level; comparing adjacent ratios does not."""
    rows = [q("2025-09-30", 309_000_000), q("2025-12-31", 318_000_000),
            q("2026-03-31", 311_000_000), q("2026-06-30", 322_000_000)]
    assert share_scale([], rows) == "ok"


def test_both_reasons_are_reported_together():
    """One row impossible against itself, and a series that changes level more than once."""
    rows = [q("2025-09-30", 59_622_000), q("2025-12-31", 82_139_000_000, 98_166_000),
            q("2026-03-31", 59_763_000), q("2026-07-04", 98_204_000_000, 98_225_000)]
    assert share_scale([], rows) == "suspect:scale,levels"


def test_no_share_data_at_all_is_not_an_error():
    assert share_scale([], [q("2026-06-30")]) == "n/a"


# --------------------------------------------------------------------------- the shares flag
def test_shares_is_measured_on_values_not_on_which_tag_resolved():
    """Erie Indemnity resolved a diluted tag and carried no values behind it, and reported "ok"
    — a promise of a per-share figure the file could not supply."""
    tags = {"shares_diluted": "WeightedAverageNumberOfDilutedSharesOutstanding"}
    assert data_checks([], [q("2026-06-30")], tags)["shares"] == "none"


def test_outstanding_only_when_that_is_all_that_landed():
    tags = {"shares_diluted": "WeightedAverageNumberOfDilutedSharesOutstanding"}
    rows = [q("2026-06-30", out=183_117_863)]
    assert data_checks([], rows, tags)["shares"] == "outstanding-only"


def test_a_diluted_tag_with_values_still_reads_ok():
    tags = {"shares_diluted": "WeightedAverageNumberOfDilutedSharesOutstanding"}
    rows = [q("2026-06-30", 391_804_000, 371_057_782)]
    assert data_checks([], rows, tags)["shares"] == "ok"


def test_basic_only_when_no_diluted_tag_resolved_but_values_exist():
    tags = {"shares_diluted": "WeightedAverageNumberOfSharesOutstandingBasic"}
    rows = [q("2026-06-30", 313_170_171)]
    assert data_checks([], rows, tags)["shares"] == "basic-only"


def test_non_positive_still_wins_over_everything():
    tags = {"shares_diluted": "WeightedAverageNumberOfDilutedSharesOutstanding"}
    rows = [q("2026-06-30", -30_150_480_000, 15_004_697_000)]
    assert data_checks([], rows, tags)["shares"].startswith("invalid:")


@pytest.mark.parametrize("key", ["latest_quarter_end", "quarter_age_days", "reconciles",
                                 "reconciled_fy", "shares", "share_scale"])
def test_checks_block_keeps_every_key_readers_depend_on(key):
    """Other tasks read these by name. share_scale was added; nothing was renamed or removed."""
    assert key in data_checks([], [q("2026-06-30", 1_000, 1_000)], {})
