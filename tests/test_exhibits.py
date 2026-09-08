"""Tests for the exhibit links added to each 8-K in the events feed.

An event's `url` is the filing's primary document, which for an 8-K is the cover page: it
says a 2.02 happened, not what was announced. The announcement is EX-99.1. These tests run
against a synthetic EDGAR index page shaped like the real one — including the two forms it
takes in practice, a filer-prepared filing and an agent-prepared one linked through the
inline-XBRL viewer.
"""
from __future__ import annotations

import pytest

INDEX = """<html><body>
<table class="tableFile" summary="Document Format Files">
<tr><th>Seq</th><th>Description</th><th>Document</th><th>Type</th><th>Size</th></tr>
<tr><td>1</td><td>8-K</td><td><a href="/ix?doc=/Archives/edgar/data/769397/000076939726000059/adsk-20260827.htm">adsk-20260827.htm</a>&nbsp;&nbsp;iXBRL</td><td>8-K</td><td>29187</td></tr>
<tr><td>2</td><td>EX-99.1</td><td><a href="/Archives/edgar/data/769397/000076939726000059/q227pressrelease.htm">q227pressrelease.htm</a></td><td>EX-99.1</td><td>272605</td></tr>
<tr><td>3</td><td>MATERIAL CONTRACT</td><td><a href="/Archives/edgar/data/769397/000076939726000059/credit.htm">credit.htm</a></td><td>EX-10.1</td><td>1000</td></tr>
<tr><td>&nbsp;</td><td>Complete submission text file</td><td><a href="/Archives/edgar/data/769397/000076939726000059/0000769397-26-000059.txt">0000769397-26-000059.txt</a></td><td>&nbsp;</td><td>441751</td></tr>
</table>
<table class="tableFile" summary="Data Files">
<tr><th>Seq</th><th>Description</th><th>Document</th><th>Type</th><th>Size</th></tr>
<tr><td>4</td><td>XBRL TAXONOMY EXTENSION SCHEMA DOCUMENT</td><td><a href="/Archives/edgar/data/769397/000076939726000059/adsk-20260827.xsd">adsk-20260827.xsd</a></td><td>EX-101.SCH</td><td>1810</td></tr>
<tr><td>5</td><td>XBRL TAXONOMY EXTENSION LABEL LINKBASE</td><td><a href="/Archives/edgar/data/769397/000076939726000059/adsk-20260827_lab.xml">adsk-20260827_lab.xml</a></td><td>EX-101.LAB</td><td>21885</td></tr>
<tr><td>15</td><td>EXTRACTED XBRL INSTANCE DOCUMENT</td><td><a href="/Archives/edgar/data/769397/000076939726000059/adsk-20260827_htm.xml">adsk-20260827_htm.xml</a></td><td>XML</td><td>2720</td></tr>
</table></body></html>"""

NO_EXHIBITS = """<html><body><table>
<tr><th>Seq</th><th>Description</th><th>Document</th><th>Type</th><th>Size</th></tr>
<tr><td>1</td><td>CURRENT REPORT</td><td><a href="/ix?doc=/Archives/edgar/data/769397/000121390026084276/ea0300009-8k.htm">ea0300009-8k.htm</a>&nbsp;&nbsp;iXBRL</td><td>8-K</td><td>23747</td></tr>
<tr><td>2</td><td>XBRL SCHEMA FILE</td><td><a href="/Archives/edgar/data/769397/000121390026084276/adsk-20260803.xsd">adsk-20260803.xsd</a></td><td>EX-101.SCH</td><td>3014</td></tr>
</table></body></html>"""

ACC = "0000769397-26-000059"
CIK = 769397


class Resp:
    def __init__(self, text):
        self.text = text


@pytest.fixture
def index(ev, monkeypatch):
    def _set(text):
        calls = []
        def fake_get(url, *a, **kw):
            calls.append(url)
            return None if text is None else Resp(text)
        monkeypatch.setattr(ev, "get", fake_get)
        return calls
    return _set


def test_the_earnings_release_is_linked_not_just_the_cover_page(ev, index):
    index(INDEX)

    ex = ev.exhibits_for(CIK, ACC)

    assert {"type": "EX-99.1",
            "url": "https://www.sec.gov/Archives/edgar/data/769397/000076939726000059/q227pressrelease.htm"} in ex


def test_a_material_contract_is_kept_but_the_xbrl_taxonomy_is_not(ev, index):
    """EX-10.1 is a contract worth reading; EX-101.SCH is a schema file. The prefixes are one
    character apart, so this is the boundary most worth pinning."""
    index(INDEX)

    types = [e["type"] for e in ev.exhibits_for(CIK, ACC)]

    assert types == ["EX-99.1", "EX-10.1"]
    assert not any(t.startswith(("EX-100", "EX-101")) for t in types)


def test_the_inline_xbrl_viewer_prefix_is_stripped_from_urls(ev, index):
    """Primary documents are linked as /ix?doc=/Archives/... — that prefix would 404 as an
    exhibit link. No exhibit here uses it, so assert no url keeps it."""
    index(INDEX)

    assert all("/ix?doc=" not in e["url"] for e in ev.exhibits_for(CIK, ACC))
    assert all(e["url"].startswith("https://www.sec.gov/Archives/") for e in ev.exhibits_for(CIK, ACC))


def test_a_filing_with_nothing_attached_returns_an_empty_list(ev, index):
    index(NO_EXHIBITS)

    assert ev.exhibits_for(CIK, ACC) == []


def test_an_unreadable_index_returns_none_so_it_is_retried_not_cached(ev, index):
    """[] means 'nothing attached' and is stored; None means 'could not look' and is not, so a
    transient failure does not permanently record an 8-K as exhibit-free."""
    index(None)

    assert ev.exhibits_for(CIK, ACC) is None


def test_the_index_url_is_built_from_the_accession(ev, index):
    calls = index(INDEX)

    ev.exhibits_for(CIK, ACC)

    assert calls == ["https://www.sec.gov/Archives/edgar/data/769397/"
                     "000076939726000059/0000769397-26-000059-index.html"]


def test_header_rows_and_short_rows_are_ignored(ev, index):
    index("<table><tr><th>Seq</th><th>Description</th><th>Document</th><th>Type</th></tr>"
          "<tr><td>only</td><td>two</td></tr></table>")

    assert ev.exhibits_for(CIK, ACC) == []
