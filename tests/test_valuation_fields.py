"""The valuation fields added 23 Sep 2026, after a verification of ~360 companies against their own
SEC filings kept finding the same gaps: investments missing beside cash, debt missing whole lines,
capitalised software nowhere, share counts on mixed split bases, and diluted counts absent or
mis-scaled. Each test is a shape a real filer produced; the company is named where it was seen.

Same style as test_normaliser.py: synthetic companyfacts documents, no network, and the assertions
are about what a reader ends up with — and about what must NOT move for the readers already here.
"""
from __future__ import annotations

from conftest import doc, fact, fy_fact, q_fact, shares, usd

D = "WeightedAverageNumberOfDilutedSharesOutstanding"
B = "WeightedAverageNumberOfSharesOutstandingBasic"
COVER = "EntityCommonStockSharesOutstanding"
FY = "2026-07-25"


def _annual(b, d, end=FY):
    return next(r for r in b.normalise_company(d)["annual"] if r["period_end"] == end)


def _anchor(end=FY, **gaap):
    """A fiscal year with revenue so the row exists, plus whatever balance-sheet facts are given."""
    return doc(us_gaap={"Revenues": usd(fy_fact(50_000_000_000, end)), **gaap})


# --------------------------------------------------------------------------
# 1. Investments beside cash
# --------------------------------------------------------------------------
def test_short_and_long_term_investments_are_published_beside_cash(b):
    """Adobe, Amazon, Intuitive Surgical: `cash` alone understated net cash by up to ~$45bn."""
    d = _anchor(**{
        "CashAndCashEquivalentsAtCarryingValue": usd(fact(7_218_000_000, FY)),
        "ShortTermInvestments": usd(fact(8_700_000_000, FY)),
        "MarketableSecuritiesNoncurrent": usd(fact(4_100_000_000, FY)),
    })
    row = _annual(b, d)
    assert row["cash"] == 7_218_000_000, "cash keeps its meaning"
    assert row["short_term_investments"] == 8_700_000_000
    assert row["long_term_investments"] == 4_100_000_000


def test_marketable_securities_outrank_a_long_term_investments_line(b):
    """`LongTermInvestments` can hold equity-method stakes that are not liquid; where the filer also
    tags the marketable securities, those are what a net-cash reader wants."""
    d = _anchor(**{
        "LongTermInvestments": usd(fact(9_000_000_000, FY)),
        "MarketableSecuritiesNoncurrent": usd(fact(4_100_000_000, FY)),
    })
    assert _annual(b, d)["long_term_investments"] == 4_100_000_000


def test_a_filer_tagging_only_securities_by_kind_still_gets_a_figure(b):
    d = _anchor(AvailableForSaleSecuritiesDebtSecuritiesCurrent=usd(fact(2_500_000_000, FY)))
    assert _annual(b, d)["short_term_investments"] == 2_500_000_000


def test_no_investment_tag_means_no_field_not_zero(b):
    row = _annual(b, _anchor(CashAndCashEquivalentsAtCarryingValue=usd(fact(1, FY))))
    assert "short_term_investments" not in row and "long_term_investments" not in row


# --------------------------------------------------------------------------
# 2. Debt: every piece, nothing twice
# --------------------------------------------------------------------------
def _cisco(**extra):
    """Cisco's FY2026 10-K balance sheet, as tagged: LongTermDebt excludes the $6.7bn of commercial
    paper that sits inside DebtCurrent."""
    return _anchor(**{
        "LongTermDebt": usd(fact(22_900_000_000, FY)),
        "DebtInstrumentCarryingAmount": usd(fact(23_002_000_000, FY)),
        "DebtCurrent": usd(fact(10_161_000_000, FY)),
        "LongTermDebtCurrent": usd(fact(3_500_000_000, FY)),
        "LongTermDebtNoncurrent": usd(fact(19_372_000_000, FY)),
        **extra,
    })


def test_a_tagged_total_short_of_its_own_pieces_is_replaced_by_them(b):
    row = _annual(b, _cisco())
    assert row["total_debt"] == 10_161_000_000 + 19_372_000_000
    assert row["total_debt_basis"] == "components_exceed_tagged"
    assert row["total_debt_tagged"] == 23_002_000_000, "the tagged figure is kept, not lost"


def test_debt_current_keeps_its_meaning(b):
    """`debt_current` still resolves `LongTermDebtCurrent` first. The full line is its own field."""
    row = _annual(b, _cisco())
    assert row["debt_current"] == 3_500_000_000
    assert row["lt_debt_current"] == 3_500_000_000
    assert row["debt_current_total"] == 10_161_000_000


def test_commercial_paper_inside_debt_current_is_not_added_twice(b):
    """DebtCurrent already includes short-term borrowings. Tagging the paper as well must not add it
    on top: the current side is the LARGER of the full line and its pieces, never their sum."""
    row = _annual(b, _cisco(CommercialPaper=usd(fact(6_661_000_000, FY))))
    assert row["total_debt"] == 10_161_000_000 + 19_372_000_000
    assert row["commercial_paper"] == 6_661_000_000


def test_commercial_paper_inside_short_term_borrowings_is_not_added_twice(b):
    """No DebtCurrent line: current = current portion of LTD + short-term borrowings, and commercial
    paper is a part of those borrowings, so it is the larger of the two that counts."""
    d = _anchor(**{
        "LongTermDebtCurrent": usd(fact(1_000_000_000, FY)),
        "ShortTermBorrowings": usd(fact(5_000_000_000, FY)),
        "CommercialPaper": usd(fact(4_000_000_000, FY)),
        "LongTermDebtNoncurrent": usd(fact(10_000_000_000, FY)),
    })
    row = _annual(b, d)
    assert row["total_debt"] == 16_000_000_000
    assert row["total_debt_basis"] == "components"


def test_short_term_borrowings_are_added_to_long_term_debt(b):
    """PepsiCo's shape: long-term debt tagged, the short-term obligations beside it."""
    d = _anchor(**{
        "LongTermDebt": usd(fact(38_000_000_000, FY)),
        "LongTermDebtNoncurrent": usd(fact(36_400_000_000, FY)),
        "LongTermDebtCurrent": usd(fact(1_600_000_000, FY)),
        "ShortTermBorrowings": usd(fact(9_000_000_000, FY)),
    })
    row = _annual(b, d)
    assert row["total_debt"] == 36_400_000_000 + 1_600_000_000 + 9_000_000_000
    assert row["total_debt_basis"] == "components_exceed_tagged"


def test_a_tagged_zero_beside_real_borrowings_is_not_no_debt(b):
    """SLB: `DebtInstrumentCarryingAmount` 0 beside $11.1bn of long-term debt read as debt-free."""
    d = _anchor(**{
        "DebtInstrumentCarryingAmount": usd(fact(0, FY)),
        "LongTermDebtNoncurrent": usd(fact(11_140_000_000, FY)),
    })
    row = _annual(b, d)
    assert row["total_debt"] == 11_140_000_000
    assert row["total_debt_basis"] == "components_exceed_tagged"
    assert row["total_debt_tagged"] == 0


def test_rounding_between_a_total_and_its_pieces_does_not_flip_the_basis(b):
    """Cisco tags LongTermDebt at -8 decimals (22.9bn) beside 22.872bn of pieces. Inside the
    tolerance the tagged total stands."""
    d = _anchor(**{
        "LongTermDebt": usd(fact(22_900_000_000, FY)),
        "LongTermDebtCurrent": usd(fact(3_500_000_000, FY)),
        "LongTermDebtNoncurrent": usd(fact(19_372_000_000, FY)),
    })
    row = _annual(b, d)
    assert row["total_debt"] == 22_900_000_000
    assert row["total_debt_basis"] == "tagged"
    assert "total_debt_tagged" not in row


def test_the_latest_quarter_gets_the_same_debt_treatment(b):
    """A valuation reads the newest balance sheet, which is a quarterly row. Until now only annual
    rows were ever summed from pieces, so a quarter with no aggregate tag carried no debt."""
    q = "2026-06-30"
    d = doc(us_gaap={
        "Revenues": usd(q_fact(5_000_000_000, q)),
        "DebtCurrent": usd(fact(2_000_000_000, q, form="10-Q", fp="Q3")),
        "LongTermDebtNoncurrent": usd(fact(8_000_000_000, q, form="10-Q", fp="Q3")),
    })
    row = next(r for r in b.normalise_company(d)["quarterly"] if r["period_end"] == q)
    assert row["total_debt"] == 10_000_000_000
    assert row["total_debt_basis"] == "components"


def test_a_debt_total_built_from_pieces_carries_an_as_filed_value_on_the_same_basis(b):
    """Point-in-time: where the pieces decide the value, what the year's own 10-K said is rebuilt
    from the pieces too — the aggregate's original would describe a different number."""
    end = "2024-12-31"
    d = doc(us_gaap={
        "Revenues": usd(fy_fact(9_000_000_000, end, filed="2025-02-01")),
        "LongTermDebt": usd(fact(5_000_000_000, end, filed="2025-02-01")),
        "DebtCurrent": usd(fact(3_000_000_000, end, filed="2025-02-01"),
                           fact(3_200_000_000, end, filed="2026-02-01")),     # restated a year on
        "LongTermDebtNoncurrent": usd(fact(9_000_000_000, end, filed="2025-02-01")),
    })
    row = _annual(b, d, end)
    assert row["total_debt"] == 12_200_000_000
    assert row["total_debt_as_filed"] == 12_000_000_000
    assert row["total_debt_as_filed_filed"] == "2025-02-01"
    assert "total_debt" in row["restated"], "the same tag reporting a new value is a restatement"


def test_an_untouched_tagged_row_keeps_its_as_filed_value(b):
    """Strictly additive where the aggregate stands: nothing about its as-filed pair moves."""
    end = "2024-12-31"
    d = doc(us_gaap={
        "Revenues": usd(fy_fact(9_000_000_000, end, filed="2025-02-01")),
        "LongTermDebt": usd(fact(14_000_000_000, end, filed="2025-02-01")),
        "LongTermDebtNoncurrent": usd(fact(13_000_000_000, end, filed="2025-02-01")),
    })
    row = _annual(b, d, end)
    assert (row["total_debt"], row["total_debt_basis"]) == (14_000_000_000, "tagged")
    assert row["total_debt_as_filed"] == 14_000_000_000


def test_finance_leases_are_their_own_field_and_not_folded_into_total_debt(b):
    d = _anchor(**{
        "LongTermDebtNoncurrent": usd(fact(10_000_000_000, FY)),
        "FinanceLeaseLiabilityCurrent": usd(fact(100_000_000, FY)),
        "FinanceLeaseLiabilityNoncurrent": usd(fact(400_000_000, FY)),
    })
    row = _annual(b, d)
    assert row["finance_lease_liabilities"] == 500_000_000, "two halves, no total: summed"
    assert row["total_debt"] == 10_000_000_000


def test_a_tagged_finance_lease_total_is_not_added_to_its_halves(b):
    d = _anchor(**{
        "FinanceLeaseLiability": usd(fact(500_000_000, FY)),
        "FinanceLeaseLiabilityCurrent": usd(fact(100_000_000, FY)),
        "FinanceLeaseLiabilityNoncurrent": usd(fact(400_000_000, FY)),
    })
    assert _annual(b, d)["finance_lease_liabilities"] == 500_000_000


# --------------------------------------------------------------------------
# 3. Capitalised software
# --------------------------------------------------------------------------
def test_capitalised_software_is_its_own_field_and_capex_is_unchanged(b):
    """ADP capitalises ~$468m of software a year that `capex` never saw. Folding it in would change
    what `capex` means for every reader already subtracting it."""
    d = _anchor(**{
        "PaymentsToAcquirePropertyPlantAndEquipment": usd(fy_fact(150_000_000, FY)),
        "PaymentsToDevelopSoftware": usd(fy_fact(468_000_000, FY)),
    })
    row = _annual(b, d)
    assert row["capex"] == 150_000_000
    assert row["capitalized_software"] == 468_000_000


def test_developed_and_acquired_software_are_summed_when_no_total_is_tagged(b):
    d = _anchor(**{
        "PaymentsToDevelopSoftware": usd(fy_fact(400_000_000, FY)),
        "PaymentsToAcquireSoftware": usd(fy_fact(68_000_000, FY)),
    })
    assert _annual(b, d)["capitalized_software"] == 468_000_000


def test_a_tagged_software_total_is_not_added_to_its_parts(b):
    d = _anchor(**{
        "PaymentsForSoftware": usd(fy_fact(468_000_000, FY)),
        "PaymentsToDevelopSoftware": usd(fy_fact(400_000_000, FY)),
    })
    assert _annual(b, d)["capitalized_software"] == 468_000_000


# --------------------------------------------------------------------------
# 4. Stock splits, and a count on one basis
# --------------------------------------------------------------------------
def _q(v, end, filed):
    return q_fact(v, end, filed=filed)


def _cover(v, end, filed, form="10-Q"):
    return fact(v, end, form=form, filed=filed)


def _booking(covers=True):
    """Booking's 25:1 split, April 2026: the Q1 2026 10-Q reprints Q1 2025 on the new basis."""
    dei = {COVER: shares(_cover(32_400_000, "2025-10-20", "2025-10-28"),
                         _cover(32_300_000, "2026-02-10", "2026-02-18", form="10-K"),
                         _cover(805_000_000, "2026-04-20", "2026-04-28"))} if covers else None
    return doc(us_gaap={
        "Revenues": usd(q_fact(5e9, "2025-03-31", filed="2025-04-29"), q_fact(5e9, "2025-06-30", filed="2025-07-29"),
                        q_fact(5e9, "2025-09-30", filed="2025-10-28"), q_fact(6e9, "2026-03-31", filed="2026-04-28")),
        D: shares(_q(33_000_000, "2025-03-31", "2025-04-29"), _q(32_800_000, "2025-06-30", "2025-07-29"),
                  _q(32_558_000, "2025-09-30", "2025-10-28"),
                  _q(825_000_000, "2025-03-31", "2026-04-28"), _q(794_000_000, "2026-03-31", "2026-04-28")),
        B: shares(_q(32_700_000, "2025-03-31", "2025-04-29"), _q(817_500_000, "2025-03-31", "2026-04-28")),
    }, dei=dei)


def test_a_split_is_found_from_the_same_period_restated_at_a_clean_ratio(b):
    [s] = b.normalise_company(_booking())["splits"]
    assert s["ratio"] == 25 and s["applied"] is True
    assert s["evidence"] == 2, "diluted and basic both reprinted"
    assert (s["after"], s["date"]) == ("2026-02-18", "2026-04-28"), "the cover-page jump narrows it"
    assert s["cover"] is True


def test_every_count_is_put_on_the_newest_basis_without_touching_the_reported_one(b):
    q = {r["period_end"]: r for r in b.normalise_company(_booking())["quarterly"]}
    assert q["2025-09-30"]["shares_diluted"] == 32_558_000, "as reported, unchanged"
    assert q["2025-09-30"]["shares_diluted_adj"] == 32_558_000 * 25
    assert q["2026-03-31"]["shares_diluted_adj"] == 794_000_000, "already post-split"
    assert q["2025-03-31"]["shares_diluted_adj"] == 825_000_000, "the restated value is post-split"


def test_the_as_filed_count_is_never_rewritten(b):
    """The point-in-time record is the whole reason `_as_filed` exists; a basis adjustment is a
    separate, derived key."""
    end = "2022-12-31"
    d = doc(us_gaap={
        "Revenues": usd(fy_fact(8e9, end, filed="2023-02-01")),
        D: shares(fy_fact(100_000_000, end, filed="2023-02-01"), fy_fact(1_000_000_000, end, filed="2025-02-01")),
        B: shares(fy_fact(99_000_000, end, filed="2023-02-01"), fy_fact(990_000_000, end, filed="2025-02-01")),
    })
    n = b.normalise_company(d)
    row = n["annual"][-1]
    assert row["shares_diluted_as_filed"] == 100_000_000
    assert row["shares_diluted"] == 1_000_000_000
    assert [s["ratio"] for s in n["splits"]] == [10]


def test_one_restated_count_alone_does_not_invent_a_split(b):
    """A mis-scaled restatement looks like a clean ratio once. A real split reprints several counts
    at once, or moves the cover page, or is tagged; one pair with none of that is not enough."""
    end = "2022-12-31"
    d = doc(us_gaap={
        "Revenues": usd(fy_fact(8e9, end, filed="2023-02-01")),
        D: shares(fy_fact(100_000_000, end, filed="2023-02-01"), fy_fact(1_000_000_000, end, filed="2025-02-01")),
    })
    assert b.normalise_company(d)["splits"] == []


def test_two_splits_seen_across_one_gap_are_not_a_third(b):
    """Texas Pacific Land split 3:1 twice. A year reported before the first split and next after the
    second reads 9x — which is both splits, not a 9:1 one."""
    def pair(end, v0, f0, v1, f1):
        return [fy_fact(v0, end, filed=f0), fy_fact(v1, end, filed=f1)]
    dil = (pair("2021-12-31", 7_700_000, "2022-02-20", 23_100_000, "2024-05-01")      # split 1
           + pair("2020-12-31", 7_750_000, "2022-02-20", 23_250_000, "2024-05-01")
           + pair("2023-12-31", 23_000_000, "2025-02-19", 69_000_000, "2026-02-18")   # split 2
           + pair("2022-12-31", 7_720_000, "2023-02-15", 69_480_000, "2026-02-18"))   # both at once
    bas = (pair("2021-12-31", 7_690_000, "2022-02-20", 23_070_000, "2024-05-01")
           + pair("2023-12-31", 22_990_000, "2025-02-19", 68_970_000, "2026-02-18"))
    d = doc(us_gaap={"Revenues": usd(fy_fact(7e8, "2023-12-31", filed="2025-02-19")),
                     D: shares(*dil), B: shares(*bas)})
    assert [s["ratio"] for s in b.normalise_company(d)["splits"]] == [3, 3]


def test_a_composite_ratio_is_explained_by_the_splits_it_spans(b):
    """The same rule where the product IS a listed ratio: two 2:1 splits and a year that jumped 4x
    across both. A 4:1 split must not be added."""
    def pair(end, v0, f0, v1, f1):
        return [fy_fact(v0, end, filed=f0), fy_fact(v1, end, filed=f1)]
    dil = (pair("2021-12-31", 10_000_000, "2022-02-20", 20_000_000, "2024-05-01")
           + pair("2023-12-31", 20_000_000, "2025-02-19", 40_000_000, "2026-02-18")
           + pair("2022-12-31", 10_100_000, "2023-02-15", 40_400_000, "2026-02-18"))
    bas = (pair("2021-12-31", 9_900_000, "2022-02-20", 19_800_000, "2024-05-01")
           + pair("2023-12-31", 19_800_000, "2025-02-19", 39_600_000, "2026-02-18"))
    d = doc(us_gaap={"Revenues": usd(fy_fact(7e8, "2023-12-31", filed="2025-02-19")),
                     D: shares(*dil), B: shares(*bas)})
    assert [s["ratio"] for s in b.normalise_company(d)["splits"]] == [2, 2]


def test_a_count_filed_inside_a_splits_window_gets_no_adjusted_value(b):
    """Without the cover-page counts the split is only known to fall between two filings; a count
    filed in between could be on either basis, so it carries no adjusted value rather than a guess."""
    splits = [{"date": "2026-04-28", "after": "2025-04-29", "ratio": 25, "applied": True}]
    assert b.split_factor("2025-04-29", splits) == 25
    assert b.split_factor("2025-10-28", splits) is None
    assert b.split_factor("2026-04-28", splits) == 1


def test_a_split_tagged_but_not_yet_in_any_count_is_listed_and_not_applied(b):
    """A split after the newest filing (Monster, Amphenol in 2026) is in no count this file holds.
    If the filer tagged the ratio it is listed, but nothing is re-denominated by it."""
    d = doc(us_gaap={
        "Revenues": usd(q_fact(2e9, "2026-06-30", filed="2026-08-07")),
        D: shares(_q(984_000_000, "2026-06-30", "2026-08-07")),
        "StockholdersEquityNoteStockSplitConversionRatio1": {"pure": [fact(2, "2026-06-30", form="10-Q", filed="2026-08-07")]},
    })
    n = b.normalise_company(d)
    assert n["splits"] == [{"date": "2026-08-07", "after": None, "ratio": 2, "evidence": 0,
                            "cover": False, "xbrl": True, "applied": False}]
    assert n["quarterly"][-1]["shares_diluted_adj"] == 984_000_000


def test_a_reverse_split_comes_back_below_one(b):
    assert b._clean_ratio(0.1) == 0.1
    assert b._clean_ratio(1.0) is None and b._clean_ratio(1.3) is None and b._clean_ratio(1000) is None


def test_the_patch_path_can_redo_the_adjustment_from_the_rows_alone(b):
    rows = [{"shares_diluted_filled": 10, "shares_diluted_filled_filed": "2025-01-01", "shares_diluted_adj": 10}]
    b.apply_split_adjustment(rows, [{"date": "2025-06-01", "after": "2025-03-01", "ratio": 2, "applied": True}])
    assert rows[0]["shares_diluted_adj"] == 20


# --------------------------------------------------------------------------
# 5. A usable diluted count, flagged where it is a fallback
# --------------------------------------------------------------------------
def test_a_mis_scaled_diluted_count_falls_back_to_the_cover_page_and_says_so(b):
    """McDonald's tags 716.4 for 716 million — and its basic count the same way."""
    end = "2025-12-31"
    d = doc(us_gaap={"Revenues": usd(fy_fact(26e9, end, filed="2026-02-24")),
                     D: shares(fy_fact(716.4, end, filed="2026-02-24")),
                     B: shares(fy_fact(712.0, end, filed="2026-02-24"))},
            dei={COVER: shares(_cover(713_000_000, "2026-02-10", "2026-02-24", form="10-K"))})
    row = _annual(b, d, end)
    assert row["shares_diluted"] == 716.4, "the reported figure is left exactly as filed"
    assert row["shares_diluted_filled"] == 713_000_000
    assert row["shares_diluted_filled_source"] == "cover"
    assert row["shares_diluted_filled_filed"] == "2026-02-24"


def test_a_missing_diluted_count_falls_back_to_basic(b):
    end = "2025-12-31"
    d = doc(us_gaap={"Revenues": usd(fy_fact(1e9, end)),
                     "IncomeTaxExpenseBenefit": usd(fy_fact(1e8, end)),
                     B: shares(fy_fact(50_000_000, end))})
    row = _annual(b, d, end)
    # `shares_diluted` already takes basic as a floor, so the row's own count is the basic one
    assert row["shares_diluted_filled"] == 50_000_000


def test_a_sound_diluted_count_is_used_as_is(b):
    end = "2025-12-31"
    d = doc(us_gaap={"Revenues": usd(fy_fact(1e9, end, filed="2026-02-01")),
                     D: shares(fy_fact(50_500_000, end, filed="2026-02-01"))},
            dei={COVER: shares(_cover(50_000_000, "2026-01-20", "2026-02-01", form="10-K"))})
    row = _annual(b, d, end)
    assert (row["shares_diluted_filled"], row["shares_diluted_filled_source"]) == (50_500_000, "shares_diluted")


def test_no_count_anywhere_leaves_the_fields_absent_not_zero(b):
    """Erie tags every share count by class; companyfacts drops them, and nothing is invented."""
    row = _annual(b, _anchor())
    assert not any(k.startswith("shares_diluted") for k in row)


# --------------------------------------------------------------------------
# The contract with readers already here
# --------------------------------------------------------------------------
def test_no_new_field_joins_the_as_filed_contract(b):
    """ASFILED_ITEMS is exactly what the consumer's measures read (test_as_filed_shares.py). The
    new fields are not measure inputs, so they carry no as-filed twin of their own."""
    new = {"short_term_investments", "long_term_investments", "cash_and_short_term_investments",
           "lt_debt_current", "debt_current_total", "short_term_borrowings", "commercial_paper",
           "finance_lease_liabilities", "capitalized_software"}
    assert new <= set(b.CONCEPTS)
    assert not new & set(b.ASFILED_ITEMS)


def test_derived_share_keys_are_not_concepts_so_none_can_invent_a_quarter(b):
    for k in ("shares_diluted_filled", "shares_diluted_adj", "total_debt_tagged"):
        assert k not in b.CONCEPTS


def test_capitalised_software_was_not_added_to_capex(b):
    assert not set(b.CONCEPTS["capex"]["tags"]) & set(b.CONCEPTS["capitalized_software"]["tags"])


# --------------------------------------------------------------------------
# 6. Freshness: a filing from the last few days is reachable
# --------------------------------------------------------------------------
def test_a_company_behind_its_own_filing_is_a_target_however_recent_its_last_quarter(b, tmp_path, monkeypatch):
    """Adobe's August-quarter 10-Q landed 22 Sep; its last quarter held was 114 days old, under the
    old 150-day gate, so it could never be patched however long companyfacts lagged."""
    import json
    monkeypatch.setattr(b, "EVENTS_DIR", tmp_path)
    ev = {"form": "10-Q", "period": "2026-08-28", "accession": "0000796343-26-000100", "date": "2026-09-22"}
    (tmp_path / "796343.json").write_text(json.dumps({"events": [ev]}))
    man = {"796343": {"quarter_age_days": 114, "latest_quarter_end": "2026-05-29"}}
    assert b.patch_targets(man, set()) == [(796343, [ev])]


def test_the_patch_budget_covers_what_the_last_build_left_behind(b):
    """The 20 Sep build found 205 companies behind and a cap of 100 filings reached 72 of them."""
    assert b.PATCH_CAP >= 2 * 205, "room for the backlog the old cap left, at two filings each"
    assert b.PATCH_SECONDS <= 60 * 60, "a hard stop far inside sec.yml's 120-minute budget"
