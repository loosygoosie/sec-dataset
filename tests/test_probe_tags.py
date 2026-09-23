"""What the tag probe must get right, since a tag list is changed on the strength of its output.

The probe exists because an empty field has two causes that look identical: a tag we do not list,
or a figure the filer tags only with a dimension — and companyfacts carries no dimensioned facts,
so the second is unreachable and no tag addition fixes it. An empty result is therefore EVIDENCE,
which puts a burden on the probe not to report a tag that carries nothing and not to stay quiet
about one it does.
"""
import re

import pytest
from conftest import doc, fact, fy_fact, usd

import probe_tags as P

SBC = re.compile("ShareBased", re.I)


def test_a_matching_tag_with_facts_is_reported_with_its_span():
    d = doc(us_gaap={"ShareBasedCompensation": usd(fy_fact(10, "2024-12-31", fy=2024),
                                                   fy_fact(12, "2025-12-31", fy=2025))})
    [hit] = P.matching_tags(d, SBC)
    assert hit["tag"] == "ShareBasedCompensation"
    assert hit["facts"] == 2
    assert (hit["fy_first"], hit["fy_last"]) == (2024, 2025)
    assert hit["latest_end"] == "2025-12-31" and hit["latest_val"] == 12


def test_a_tag_that_does_not_match_is_left_out():
    d = doc(us_gaap={"Assets": usd(fy_fact(1, "2025-12-31"))})
    assert P.matching_tags(d, SBC) == []


def test_a_tag_present_but_carrying_nothing_is_not_reported():
    """The whole point of the probe is that a hit means 'this tag would resolve'. A tag with an
    empty unit list resolves nothing, and reporting it would send someone to add a tag that
    changes no company's data."""
    d = doc(us_gaap={"ShareBasedCompensation": {"USD": []}})
    assert P.matching_tags(d, SBC) == []


def test_a_company_with_no_us_gaap_facts_at_all_does_not_crash():
    assert P.matching_tags({}, SBC) == []


def test_the_row_survives_a_value_that_is_not_a_number():
    """A format crash in a diagnostic reads as a missing tag, which is the wrong conclusion."""
    h = {"tag": "T", "unit": "pure", "facts": 1, "fy_first": 2025, "fy_last": 2025,
         "latest_end": "2025-12-31", "latest_val": "n/a"}
    assert "n/a" in P.line(h, "listed")


def test_listed_for_reads_the_builders_own_tag_list():
    assert P.listed_for("stock_comp") == P.B.CONCEPTS["stock_comp"]["tags"]
    assert P.listed_for(None) == []


def test_an_unknown_field_is_refused_rather_than_silently_matching_nothing():
    with pytest.raises(SystemExit):
        P.listed_for("not_a_field")


def _fake_source(monkeypatch, us_gaap, resolved):
    monkeypatch.setattr(P, "ticker_map", lambda: {"ZZZ": 1})
    monkeypatch.setattr(P, "resolved_for", lambda cik, field: resolved)
    monkeypatch.setattr(P.B, "get", lambda url, **kw: type("R", (), {"json": lambda s: doc(us_gaap=us_gaap)})())


def test_a_listed_tag_carrying_facts_that_the_build_resolved_to_nothing_is_a_builder_bug(monkeypatch, capsys):
    """CLAUDE.md: a builder bug is stopped on and reported, never worked around. The exit code
    carries it so a CI run cannot go green over one."""
    _fake_source(monkeypatch, {"ShareBasedCompensation": usd(fy_fact(10, "2025-12-31", fy=2025))}, None)
    assert P.probe(["ZZZ"], SBC, "stock_comp") == 1
    assert "BUILDER BUG" in capsys.readouterr().out


def test_the_same_tag_is_not_a_bug_once_the_build_has_resolved_it(monkeypatch, capsys):
    _fake_source(monkeypatch, {"ShareBasedCompensation": usd(fy_fact(10, "2025-12-31", fy=2025))},
                 "ShareBasedCompensation")
    assert P.probe(["ZZZ"], SBC, "stock_comp") == 0
    assert "BUILDER BUG" not in capsys.readouterr().out


def test_an_unlisted_hit_is_marked_as_the_tag_to_consider_adding(monkeypatch, capsys):
    _fake_source(monkeypatch, {"ShareBasedCompensationNoncash": usd(fy_fact(10, "2025-12-31", fy=2025))}, None)
    assert P.probe(["ZZZ"], SBC, "stock_comp") == 0
    out = capsys.readouterr().out
    assert "NOT LISTED" in out and "BUILDER BUG" not in out


def test_no_match_says_so_in_the_words_that_name_the_other_cause(monkeypatch, capsys):
    """An empty result is the finding, so it must not print as a blank."""
    _fake_source(monkeypatch, {"Assets": usd(fy_fact(1, "2025-12-31"))}, None)
    P.probe(["ZZZ"], SBC, "stock_comp")
    assert "tagged only with a dimension" in capsys.readouterr().out


def test_the_probe_never_writes():
    """It reads data/ and sec.gov and produces text. `data/` belongs to the build script."""
    src = (P.__file__ and open(P.__file__).read())
    for forbidden in ("write_text(", "json.dump(", "mkdir(", '"w"', "'w'"):
        assert forbidden not in src, f"probe_tags.py contains {forbidden} — it must only read"


# --- `--show`, 23 Sep 2026: a verification reads the fields the NEXT build would publish ----------

def test_show_prints_what_the_builder_would_publish(monkeypatch, capsys):
    """The spot-check route for new fields. It must go through `normalise_company` itself — a probe
    re-implementing the debt or share rules would check a copy of them, not them."""
    _fake_source(monkeypatch, {
        "Revenues": usd(fy_fact(50_000_000_000, "2026-07-25")),
        "LongTermDebt": usd(fact(22_900_000_000, "2026-07-25")),
        "DebtCurrent": usd(fact(10_161_000_000, "2026-07-25")),
        "LongTermDebtNoncurrent": usd(fact(19_372_000_000, "2026-07-25")),
    }, None)
    P.probe(["ZZZ"], SBC, None, show=True)
    out = capsys.readouterr().out
    assert "total_debt " in out and "29,533,000,000" in out
    assert "components_exceed_tagged" in out
    assert "splits: []" in out


def test_show_is_off_unless_asked(monkeypatch, capsys):
    _fake_source(monkeypatch, {"Revenues": usd(fy_fact(1, "2026-07-25"))}, None)
    P.probe(["ZZZ"], SBC, None)
    assert "splits:" not in capsys.readouterr().out


def test_a_ticker_outside_the_index_is_still_found(tmp_path, monkeypatch):
    """The verification that asked for this was about small caps (Winmark, Red Violet); a probe
    limited to the S&P 500 list skipped every one of them."""
    (tmp_path / "tickers.json").write_text('{"WINA": {"cik": 908315, "name": "Winmark"}}')
    (tmp_path / "sp500.json").write_text('{"companies": [{"ticker": "AAPL", "cik": 320193}]}')
    monkeypatch.setattr(P, "TICKERS_PATH", tmp_path / "tickers.json")
    monkeypatch.setattr(P, "SP500_PATH", tmp_path / "sp500.json")
    assert P.ticker_map() == {"WINA": 908315, "AAPL": 320193}
