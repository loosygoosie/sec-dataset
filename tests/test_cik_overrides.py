"""Tests for data/cik_overrides.json — the hand-maintained ticker -> CIK corrections.

The SEC's ticker map is regenerated daily from filing cover pages, so a reorganisation can
move a ticker to a newly registered holding company that has filed nothing, leaving the
operating company — with every year of history — carrying no ticker at all. The override
puts the ticker back where the fundamentals are. Because the file is hand-edited, the
tests care as much about what a bad entry does as about what a good one does.
"""
from __future__ import annotations

import json

import pytest


def write_overrides(b_or_ev, monkeypatch, tmp_path, overrides):
    p = tmp_path / "cik_overrides.json"
    p.write_text(json.dumps({"overrides": overrides}))
    monkeypatch.setattr(b_or_ev, "CIK_OVERRIDES_PATH", p)
    return p


class FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


SEC_MAP = {"0": {"cik_str": 2115436, "ticker": "XOM", "title": "ExxonMobil Holdings Corp"},
           "1": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}


# --------------------------------------------------------------------------
# Parsing the file
# --------------------------------------------------------------------------
def test_an_entry_is_read_with_its_cik_and_optional_name(b, monkeypatch, tmp_path):
    write_overrides(b, monkeypatch, tmp_path, {"XOM": {"cik": 34088, "name": "Exxon Mobil Corporation"}})

    assert b.load_cik_overrides() == {"XOM": {"cik": 34088, "name": "Exxon Mobil Corporation"}}


def test_a_bare_number_is_accepted_as_the_cik(b, monkeypatch, tmp_path):
    write_overrides(b, monkeypatch, tmp_path, {"XOM": 34088})

    assert b.load_cik_overrides()["XOM"]["cik"] == 34088


def test_an_absent_file_is_simply_no_overrides(b, monkeypatch, tmp_path):
    monkeypatch.setattr(b, "CIK_OVERRIDES_PATH", tmp_path / "nope.json")

    assert b.load_cik_overrides() == {}


def test_unparseable_json_is_ignored_rather_than_fatal(b, monkeypatch, tmp_path):
    p = tmp_path / "cik_overrides.json"
    p.write_text("{ this is not json")
    monkeypatch.setattr(b, "CIK_OVERRIDES_PATH", p)

    assert b.load_cik_overrides() == {}          # a typo must not take the weekly build down


def test_one_bad_entry_does_not_discard_the_good_ones(b, monkeypatch, tmp_path):
    write_overrides(b, monkeypatch, tmp_path, {"XOM": {"cik": 34088}, "BAD": {"cik": "not-a-number"}})

    got = b.load_cik_overrides()

    assert got["XOM"]["cik"] == 34088
    assert "BAD" not in got


# --------------------------------------------------------------------------
# Applying it where tickers.json is built
# --------------------------------------------------------------------------
@pytest.fixture
def sec_map(b, monkeypatch):
    def fake_get(url, *a, **kw):
        if "company_tickers_exchange" in url:
            raise RuntimeError("exchange map not used in this test")
        return FakeResp(SEC_MAP)
    monkeypatch.setattr(b, "get", fake_get)


def test_the_override_moves_the_ticker_to_the_operating_company(b, sec_map, monkeypatch, tmp_path):
    write_overrides(b, monkeypatch, tmp_path, {"XOM": {"cik": 34088, "name": "Exxon Mobil Corporation"}})

    by_ticker, by_cik = b.load_ticker_maps()

    assert by_ticker["XOM"] == {"cik": 34088, "name": "Exxon Mobil Corporation"}
    assert by_cik[34088] == ["XOM"]              # the company file and manifest pick this up
    assert 2115436 not in by_cik                 # the shell keeps no ticker
    assert by_ticker["AAPL"]["cik"] == 320193    # every other ticker untouched


def test_an_override_the_sec_map_has_caught_up_with_is_a_no_op(b, sec_map, monkeypatch, tmp_path):
    """Once the SEC map agrees, the entry changes nothing — so a stale entry is harmless
    and can be removed at leisure."""
    write_overrides(b, monkeypatch, tmp_path, {"AAPL": {"cik": 320193}})

    by_ticker, _ = b.load_ticker_maps()

    assert by_ticker["AAPL"] == {"cik": 320193, "name": "Apple Inc."}


def test_an_override_for_a_ticker_the_map_lacks_is_still_applied(b, sec_map, monkeypatch, tmp_path):
    write_overrides(b, monkeypatch, tmp_path, {"NEWCO": {"cik": 999, "name": "New Co"}})

    by_ticker, by_cik = b.load_ticker_maps()

    assert by_ticker["NEWCO"] == {"cik": 999, "name": "New Co"}
    assert by_cik[999] == ["NEWCO"]


# --------------------------------------------------------------------------
# The events feed reads the same file
# --------------------------------------------------------------------------
def test_the_events_feed_inverts_the_map_to_cik_to_tickers(ev, monkeypatch, tmp_path):
    write_overrides(ev, monkeypatch, tmp_path, {"XOM": {"cik": 34088}})

    assert ev.load_ticker_overrides() == {34088: ["XOM"]}


def test_an_untagged_operating_company_gets_its_ticker_back(ev):
    """The SEC's submissions record for CIK 34088 carries no ticker, so without the override
    Exxon's 8-Ks reach the feed untagged and a monitor watching XOM never sees them."""
    overrides = {34088: ["XOM"]}

    assert ev.tickers_for(34088, [], overrides, {}) == ["XOM"]
    assert ev.tickers_for(34088, None, overrides, {}) == ["XOM"]


def test_the_override_does_not_strip_the_ticker_from_the_new_registrant(ev):
    """During a reorganisation both entities file. CIK 2115436 already carries XOM in its own
    submissions record, and it keeps it — both streams matter."""
    assert ev.tickers_for(2115436, ["XOM"], {34088: ["XOM"]}, {}) == ["XOM"]


def test_a_cik_with_no_override_falls_back_to_the_record_then_the_manifest(ev):
    assert ev.tickers_for(320193, ["AAPL"], {}, {}) == ["AAPL"]
    assert ev.tickers_for(4904, [], {}, {4904: ["AEP"]}) == ["AEP"]
    assert ev.tickers_for(999, [], {}, {}) == []


# --------------------------------------------------------------------------
# The file that ships in the repo
# --------------------------------------------------------------------------
def test_the_checked_in_overrides_file_is_valid_and_documented(b):
    """Whatever else it holds later, the shipped file must parse and explain itself."""
    j = json.loads(b.CIK_OVERRIDES_PATH.read_text())

    assert j["_readme"], "the file is hand-edited; it must say what it is for"
    for ticker, entry in j["overrides"].items():
        assert isinstance(entry["cik"], int) and entry["cik"] > 0, ticker
        assert entry.get("why"), f"{ticker} must record why it needs an override"
    assert j["overrides"]["XOM"]["cik"] == 34088
    assert "HONA" not in j["overrides"], "HONA is a real spinoff with nothing filed; nothing to point at"
