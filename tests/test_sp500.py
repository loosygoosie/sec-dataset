"""Tests for the S&P 500 constituents snapshot.

The snapshot is the one input that does not come from the SEC, so the rules around it
matter more than usual: a ticker is resolved through the SEC's own map or not at all, a
failed fetch must leave the previous file standing rather than publish an empty index,
and the request must not carry SEC_USER_AGENT off sec.gov.
"""
from __future__ import annotations

import pytest

HEADER = "Symbol,Security,GICS Sector,GICS Sub-Industry,Headquarters Location,Date added,CIK,Founded\n"

MAP = {
    "MMM": {"cik": 66740, "name": "3M CO"},
    "AAPL": {"cik": 320193, "name": "Apple Inc."},
    "BRK-B": {"cik": 1067983, "name": "BERKSHIRE HATHAWAY INC"},
}

GENERATED = "2026-09-08T19:00:00Z"


def csv_rows(*symbols):
    return HEADER + "".join(f'{s},{s} Corp,Industrials,Widgets,"Town, State",1957-03-04,1,1900\n' for s in symbols)


@pytest.fixture
def fetch(b, monkeypatch):
    """Swap the network call for a canned CSV (or None, for a failed fetch)."""
    def _set(text):
        monkeypatch.setattr(b, "_sp500_csv", lambda: text)
    return _set


def test_constituents_are_resolved_to_ciks_from_the_sec_map(b, fetch, monkeypatch):
    monkeypatch.setattr(b, "SP500_MIN", 2)
    fetch(csv_rows("MMM", "AAPL"))

    rec, note = b.sp500_snapshot(MAP, GENERATED)

    assert note == "ok"
    assert rec["companies"] == [{"ticker": "AAPL", "cik": 320193, "name": "AAPL Corp"},
                                {"ticker": "MMM", "cik": 66740, "name": "MMM Corp"}]
    assert rec["unmatched"] == []
    assert rec["constituents"] == 2 and rec["matched"] == 2


def test_a_dotted_ticker_matches_the_sec_maps_dashed_spelling(b, fetch, monkeypatch):
    """The CSV writes BRK.B; the SEC ticker map writes BRK-B. Without the rewrite,
    Berkshire would land in `unmatched` every single build."""
    monkeypatch.setattr(b, "SP500_MIN", 1)
    fetch(csv_rows("BRK.B"))

    rec, _ = b.sp500_snapshot(MAP, GENERATED)

    assert [c["ticker"] for c in rec["companies"]] == ["BRK-B"]
    assert rec["companies"][0]["cik"] == 1067983
    assert rec["unmatched"] == []


def test_a_ticker_the_sec_map_does_not_carry_is_listed_not_guessed(b, fetch, monkeypatch):
    """A fresh index addition can precede the SEC map. It is named, not given a made-up CIK."""
    monkeypatch.setattr(b, "SP500_MIN", 2)
    fetch(csv_rows("AAPL", "NEWCO"))

    rec, _ = b.sp500_snapshot(MAP, GENERATED)

    assert rec["unmatched"] == ["NEWCO"]
    assert [c["ticker"] for c in rec["companies"]] == ["AAPL"]
    assert rec["constituents"] == 2 and rec["matched"] == 1


def test_a_repeated_ticker_is_counted_once(b, fetch, monkeypatch):
    monkeypatch.setattr(b, "SP500_MIN", 1)
    fetch(csv_rows("AAPL", "AAPL"))

    rec, _ = b.sp500_snapshot(MAP, GENERATED)

    assert rec["constituents"] == 1


def test_the_snapshot_carries_the_build_date_and_its_source(b, fetch, monkeypatch):
    monkeypatch.setattr(b, "SP500_MIN", 1)
    fetch(csv_rows("AAPL"))

    rec, _ = b.sp500_snapshot(MAP, GENERATED)

    assert rec["date"] == "2026-09-08"
    assert rec["generated_utc"] == GENERATED
    assert rec["source"] == b.SP500_CSV_URL


def test_a_failed_fetch_returns_no_record_so_the_previous_file_stands(b, fetch):
    fetch(None)

    rec, note = b.sp500_snapshot(MAP, GENERATED)

    assert rec is None                       # main writes nothing, data/sp500.json survives
    assert "fetch failed" in note


def test_a_truncated_list_is_treated_as_a_failed_fetch(b, fetch):
    """A two-line CSV is a broken download, not an index that shrank to one member.
    Publishing it would silently empty the universe every reader screens on."""
    fetch(csv_rows("AAPL"))                  # real SP500_MIN of 400 applies here

    rec, note = b.sp500_snapshot(MAP, GENERATED)

    assert rec is None
    assert "only 1 tickers" in note


def test_a_full_length_list_passes_the_floor(b, fetch):
    fetch(csv_rows(*[f"T{i}" for i in range(b.SP500_MIN)]))

    rec, note = b.sp500_snapshot(MAP, GENERATED)

    assert note == "ok"
    assert rec["constituents"] == b.SP500_MIN


def test_the_constituents_request_does_not_carry_the_sec_user_agent(b):
    """SEC_USER_AGENT is a real name and email the SEC requires. It goes to sec.gov and
    nowhere else, so this one non-SEC request must use its own header."""
    assert b.SP500_HEADERS["User-Agent"] != b.HEADERS["User-Agent"]
    assert "sec.gov" not in b.SP500_CSV_URL
    assert b.USER_AGENT not in b.SP500_HEADERS["User-Agent"]


# --------------------------------------------------------------------------
# no_fundamentals: resolved to a CIK, but nothing behind it
# --------------------------------------------------------------------------
def test_a_constituent_with_no_company_file_is_named(b, fetch, monkeypatch):
    """A spinoff that has not filed yet, or a ticker moved to a new registrant, resolves
    cleanly and then joins to nothing. Silence there looks identical to a company with no
    revenue, so it is stated instead."""
    monkeypatch.setattr(b, "SP500_MIN", 2)
    fetch(csv_rows("AAPL", "MMM"))

    rec, _ = b.sp500_snapshot(MAP, GENERATED, published={320193})   # MMM's CIK absent

    assert rec["no_fundamentals"] == ["MMM"]
    assert rec["matched"] == 2                  # still matched: it has a CIK, just no file


def test_nothing_is_flagged_when_every_constituent_has_a_file(b, fetch, monkeypatch):
    monkeypatch.setattr(b, "SP500_MIN", 2)
    fetch(csv_rows("AAPL", "MMM"))

    rec, _ = b.sp500_snapshot(MAP, GENERATED, published={320193, 66740})

    assert rec["no_fundamentals"] == []


def test_an_unmatched_ticker_is_not_also_reported_as_lacking_fundamentals(b, fetch, monkeypatch):
    """The two lists answer different questions; a ticker with no CIK belongs only in unmatched."""
    monkeypatch.setattr(b, "SP500_MIN", 2)
    fetch(csv_rows("AAPL", "NEWCO"))

    rec, _ = b.sp500_snapshot(MAP, GENERATED, published={320193})

    assert rec["unmatched"] == ["NEWCO"]
    assert rec["no_fundamentals"] == []


def test_without_a_published_set_the_check_is_skipped_not_guessed(b, fetch, monkeypatch):
    monkeypatch.setattr(b, "SP500_MIN", 1)
    fetch(csv_rows("AAPL"))

    rec, _ = b.sp500_snapshot(MAP, GENERATED)

    assert rec["no_fundamentals"] == []
