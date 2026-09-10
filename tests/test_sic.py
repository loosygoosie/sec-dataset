"""`sic` on the manifest — the SEC's own industry code, carried so a screen can read one file.

Why this exists: the book's re-screen needs a SECTOR for every S&P 500 constituent, and its labels
used to come from a data vendor that was removed on 9 Sep 2026. 249 of the 503 constituents had no
replacement source. The broker's taxonomy cannot substitute — it calls both Deckers and Monster
"Consumer Non-Durables", while the screen needs one on a 5% revenue-growth floor with a 4x leverage
bound and the other on 2% and 5x. The SEC's own `sicDescription` does separate them, and the events
build already stores it.

What this repo does and does not do with it: it carries the raw code. Mapping a SIC to a sector is
a screening decision and lives with the screen (`NOTES.md`, ground rules: no scoring or screening
logic in this repo).
"""
from __future__ import annotations

import json
import pathlib

import pytest


def test_load_sics_reads_the_description_from_the_events_record(b, tmp_path, monkeypatch):
    (tmp_path / "320193.json").write_text(json.dumps(
        {"cik": 320193, "name": "APPLE INC", "sic": "Electronic Computers", "events": []}))
    (tmp_path / "789019.json").write_text(json.dumps(
        {"cik": 789019, "name": "MICROSOFT CORP", "sic": "Services-Prepackaged Software", "events": []}))
    monkeypatch.setattr(b, "EVENTS_DIR", tmp_path)
    assert b.load_sics() == {"320193": "Electronic Computers",
                             "789019": "Services-Prepackaged Software"}


def test_a_filer_with_no_sic_is_omitted_not_defaulted(b, tmp_path, monkeypatch):
    """A missing code must read as absent. Defaulting one would hand the screen a sector, and with
    it a leverage bound and a growth floor, on no evidence at all."""
    (tmp_path / "1.json").write_text(json.dumps({"cik": 1, "events": []}))
    (tmp_path / "2.json").write_text(json.dumps({"cik": 2, "sic": "", "events": []}))
    monkeypatch.setattr(b, "EVENTS_DIR", tmp_path)
    assert b.load_sics() == {}


def test_an_unreadable_events_file_does_not_take_the_build_down(b, tmp_path, monkeypatch):
    (tmp_path / "3.json").write_text("{ truncated")
    (tmp_path / "4.json").write_text(json.dumps({"cik": 4, "sic": "Retail-Variety Stores", "events": []}))
    monkeypatch.setattr(b, "EVENTS_DIR", tmp_path)
    assert b.load_sics() == {"4": "Retail-Variety Stores"}


# --------------------------------------------------------------------------- against the real data
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"


@pytest.mark.skipif(not (DATA / "sp500.json").exists(), reason="no built dataset on disk")
def test_the_sp500_is_almost_entirely_covered():
    """The screen runs on the index, so coverage there is what matters — not the 7,411 total."""
    sp = json.loads((DATA / "sp500.json").read_text())
    have = sum(1 for c in sp["companies"]
               if (DATA / "events" / f"{c['cik']}.json").exists()
               and json.loads((DATA / "events" / f"{c['cik']}.json").read_text()).get("sic"))
    assert have >= len(sp["companies"]) - 5, f"only {have} of {len(sp['companies'])} carry a sic"


@pytest.mark.skipif(not (DATA / "sp500.json").exists(), reason="no built dataset on disk")
def test_sic_separates_the_two_the_brokers_taxonomy_cannot():
    """Deckers and Monster are one category to the broker and two to the screen. If a future change
    ever collapsed them, the growth floor and leverage bound would silently swap for one of them."""
    t = json.loads((DATA / "tickers.json").read_text())
    sic = {}
    for k in ("DECK", "MNST"):
        p = DATA / "events" / f"{t[k]['cik']}.json"
        sic[k] = json.loads(p.read_text()).get("sic")
    assert sic["DECK"] and sic["MNST"] and sic["DECK"] != sic["MNST"], sic
