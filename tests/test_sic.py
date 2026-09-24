"""`sic` and `sic_code` on the manifest — the SEC's own industry assignment, carried as raw source.

WHY IT WAS FIRST CARRIED, and the consumer named here is GONE: the book's re-screen needed a SECTOR
for every S&P 500 constituent after its vendor labels were removed on 9 Sep 2026, and the broker's
taxonomy could not substitute — it calls both Deckers and Monster "Consumer Non-Durables" while the
screen needed one on a 5% growth floor with a 4x leverage bound and the other on 2% and 5x. That
screen, its sectors, its floors and its bounds were all deleted on 14 Sep 2026. The field outlived
them, which is the usual way round and worth saying rather than leaving this paragraph reading as
live.

WHY IT IS CARRIED NOW. `robinhood-book` needs to answer whether a fifty-name book is one bet. The
DESCRIPTION cannot answer it: the top fifty spans 42 distinct descriptions, which reads as well
diversified while "Services-Prepackaged Software", "Services-Computer Integrated Systems Design"
and "Services-Business Services, NEC" are one exposure under three labels. The first two digits of
the CODE are the SIC major group, which is the bucket the question needs — and it is the SEC's own
assignment published with the filing, not a taxonomy this repo would have to maintain. `sic_code`
was added 14 Sep 2026 for exactly that.

What this repo does and does not do with it: it carries the raw assignment. Mapping a SIC to a
sector, or deciding what counts as concentrated, is a consumer's decision (`NOTES.md`, ground
rules: no scoring or screening logic in this repo).
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
    desc, code = b.load_sics()
    assert desc == {"320193": "Electronic Computers", "789019": "Services-Prepackaged Software"}
    assert code == {}, "no sic_code in the fixture, so none is invented"


def test_a_filer_with_no_sic_is_omitted_not_defaulted(b, tmp_path, monkeypatch):
    """A missing code must read as absent. Defaulting one would hand the screen a sector, and with
    it a leverage bound and a growth floor, on no evidence at all."""
    (tmp_path / "1.json").write_text(json.dumps({"cik": 1, "events": []}))
    (tmp_path / "2.json").write_text(json.dumps({"cik": 2, "sic": "", "sic_code": "", "events": []}))
    monkeypatch.setattr(b, "EVENTS_DIR", tmp_path)
    assert b.load_sics() == ({}, {})


def test_an_unreadable_events_file_does_not_take_the_build_down(b, tmp_path, monkeypatch):
    (tmp_path / "3.json").write_text("{ truncated")
    (tmp_path / "4.json").write_text(json.dumps({"cik": 4, "sic": "Retail-Variety Stores", "events": []}))
    monkeypatch.setattr(b, "EVENTS_DIR", tmp_path)
    assert b.load_sics() == ({"4": "Retail-Variety Stores"}, {})


def test_the_CODE_is_carried_beside_the_description_and_is_not_the_description(b, tmp_path, monkeypatch):
    """`sic_code` added 14 Sep 2026. The SEC's submissions record calls the four-digit code `sic`
    and the text `sicDescription`; this file has published the TEXT under the key `sic` since it was
    written, so the code gets a new key rather than the right one. Adding a key is safe where
    changing the meaning of one is not, and the naming confusion is the SEC's, inherited."""
    (tmp_path / "789019.json").write_text(json.dumps(
        {"cik": 789019, "sic": "Services-Prepackaged Software", "sic_code": "7372", "events": []}))
    monkeypatch.setattr(b, "EVENTS_DIR", tmp_path)

    desc, code = b.load_sics()
    assert desc == {"789019": "Services-Prepackaged Software"}
    assert code == {"789019": "7372"}
    assert code["789019"].isdigit(), "sic_code must be the CODE; the description has its own key"


def test_THE_MAJOR_GROUP_IS_WHY_THE_CODE_EXISTS(b, tmp_path, monkeypatch):
    """The whole point, as a worked case rather than an assertion in prose.

    Three descriptions, three labels, one exposure. Their first two digits agree, and that is the
    bucket a concentration question needs. Nothing here decides what to DO with the grouping —
    that is a consumer's decision — but if the code ever stopped being the code, a consumer
    grouping on it would silently get 42 industries out of fifty companies and call it diversified.
    """
    rows = {"1": ("Services-Prepackaged Software", "7372"),
            "2": ("Services-Computer Integrated Systems Design", "7373"),
            "3": ("Services-Business Services, NEC", "7389"),
            "4": ("Retail-Eating  Places", "5812")}
    for cik, (d, c) in rows.items():
        (tmp_path / f"{cik}.json").write_text(json.dumps({"cik": int(cik), "sic": d, "sic_code": c,
                                                          "events": []}))
    monkeypatch.setattr(b, "EVENTS_DIR", tmp_path)
    _, code = b.load_sics()

    groups = {cik: c[:2] for cik, c in code.items()}
    assert len({groups[c] for c in ("1", "2", "3")}) == 1, (
        "three software descriptions must collapse to one major group — that is the field's reason")
    assert groups["4"] != groups["1"], "and a genuinely different business must not collapse into it"


# --------------------------------------------------------------------------- against the real data
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"


# An S&P 500 coverage check lived here until 24 Sep 2026; it read data/sp500.json, which was dropped
# with its last reader (the list remains in git history, NOTES.md 24 Sep 2026).


@pytest.mark.skipif(not (DATA / "tickers.json").exists(), reason="no built dataset on disk")
def test_sic_separates_the_two_the_brokers_taxonomy_cannot():
    """Deckers and Monster are one category to the broker and two to the screen. If a future change
    ever collapsed them, the growth floor and leverage bound would silently swap for one of them."""
    t = json.loads((DATA / "tickers.json").read_text())
    sic = {}
    for k in ("DECK", "MNST"):
        p = DATA / "events" / f"{t[k]['cik']}.json"
        sic[k] = json.loads(p.read_text()).get("sic")
    assert sic["DECK"] and sic["MNST"] and sic["DECK"] != sic["MNST"], sic
