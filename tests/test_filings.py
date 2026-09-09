"""The 10-K narrative extractor.

The parser can only be exercised against real filings on the runner — the SEC refuses requests
that do not carry the declared contact in SEC_USER_AGENT, and that secret belongs to the build,
not to a developer's shell. So everything the extractor decides is pinned here against synthetic
filings shaped like the real ones: a table of contents that names every item, headings split
across inline-XBRL spans, cross-references to items in the middle of sentences, and the run of
one-line items — 1B, 1C, 2, 3, 4 — that looks exactly like a table of contents and is not.

The rule the tests are protecting: a section is the company's own words between its heading and
the next item's heading. Anything that cannot be established that way is reported missing rather
than guessed at, because a brief written from a mis-sliced filing reads exactly like a correct
one.
"""
from __future__ import annotations

import gzip
import io
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from build_sec_filings import gz_bytes, sections, to_text  # noqa: E402

LONG = "This is the body of the section. " * 40           # ~1,300 chars, over MIN_SECTION


def filing(toc=True, business=LONG, risks=LONG, mdna=LONG, legal="None.", qq=LONG) -> str:
    """A 10-K shaped like the ones EDGAR serves: a contents table, then the items in order."""
    parts = ["<html><body>"]
    if toc:
        parts.append(
            "<table>"
            "<tr><td>Item 1.</td><td>Business</td><td>3</td></tr>"
            "<tr><td>Item 1A.</td><td>Risk Factors</td><td>12</td></tr>"
            "<tr><td>Item 1B.</td><td>Unresolved Staff Comments</td><td>30</td></tr>"
            "<tr><td>Item 2.</td><td>Properties</td><td>31</td></tr>"
            "<tr><td>Item 3.</td><td>Legal Proceedings</td><td>32</td></tr>"
            "<tr><td>Item 7.</td><td>Management's Discussion and Analysis</td><td>40</td></tr>"
            "<tr><td>Item 7A.</td><td>Quantitative and Qualitative Disclosures</td><td>60</td></tr>"
            "<tr><td>Item 8.</td><td>Financial Statements</td><td>65</td></tr>"
            "</table>")
    parts += [
        f"<p>Item 1. Business</p><p>{business}</p>",
        f"<p>Item 1A. Risk Factors</p><p>{risks}</p>",
        "<p>Item 1B. Unresolved Staff Comments</p><p>None.</p>",
        "<p>Item 1C. Cybersecurity</p><p>We manage risk.</p>",
        "<p>Item 2. Properties</p><p>We lease our offices.</p>",
        f"<p>Item 3. Legal Proceedings</p><p>{legal}</p>",
        "<p>Item 4. Mine Safety Disclosures</p><p>Not applicable.</p>",
        "<p>Item 5. Market for Registrant's Common Equity</p><p>NASDAQ.</p>",
        "<p>Item 6. [Reserved]</p>",
        f"<p>Item 7. Management's Discussion and Analysis</p><p>{mdna}</p>",
        f"<p>Item 7A. Quantitative and Qualitative Disclosures About Market Risk</p><p>{qq}</p>",
        "<p>Item 8. Financial Statements and Supplementary Data</p><p>See the index.</p>",
        "</body></html>"]
    return "".join(parts)


def parse(html):
    return sections(to_text(html))


# ---------------------------------------------------------------- the happy path

def test_finds_every_wanted_section():
    s = parse(filing())
    assert set(s) == {"item1", "item1a", "item3", "item7", "item7a"}


def test_a_section_holds_its_own_body_and_not_the_next_one():
    s = parse(filing(business="ALPHA " * 300, risks="BETA " * 300))
    assert "ALPHA" in s["item1"] and "BETA" not in s["item1"]
    assert "BETA" in s["item1a"] and "ALPHA" not in s["item1a"]


def test_the_heading_is_kept_so_a_reader_can_see_what_was_sliced():
    assert parse(filing())["item1a"].lower().startswith("item 1a")


def test_item_1_stops_at_item_1a_not_at_the_end_of_the_filing():
    s = parse(filing())
    assert "Financial Statements" not in s["item1"]


# ---------------------------------------------------------------- the table of contents

def test_the_contents_table_is_not_mistaken_for_the_body():
    """The whole point: with a contents table naming every item, Item 1 must still be the real
    Item 1 — a few paragraphs — and not the two-line gap between two rows of the table."""
    s = parse(filing(toc=True))
    assert len(s["item1"]) > 1_000


def test_a_filing_with_no_contents_table_parses_the_same_way():
    with_toc, without = parse(filing(toc=True)), parse(filing(toc=False))
    assert set(with_toc) == set(without)
    assert without["item1"].count("body of the section") == with_toc["item1"].count("body of the section")


def test_a_one_line_item_takes_its_body_not_its_contents_row():
    """1B, 1C, 2, 3 and 4 are five distinct items inside a few hundred characters — the same
    shape as a contents table, and Item 3's body reaches no further than its contents row does.
    The tie goes to the later one, because the body always follows the contents."""
    s = parse(filing(legal="We are defending a patent claim brought in 2026."))
    assert "patent claim" in s["item3"]
    assert "Risk Factors" not in s["item3"]      # not the contents row, which reads on into 1A


def test_a_contents_table_running_straight_into_item_1_still_parses():
    """The shape that broke the first attempt at this: no forward-looking-statements page, no
    page break — the last contents row is a few characters from the real Item 1 heading, so any
    rule that cuts out a dense run of headings cuts out the section itself."""
    html = ("<html><body><table>"
            "<tr><td>Item 1.</td><td>Business</td></tr>"
            "<tr><td>Item 1A.</td><td>Risk Factors</td></tr>"
            "<tr><td>Item 7.</td><td>Management's Discussion and Analysis</td></tr>"
            "</table>"
            f"<p>Item 1. Business</p><p>{'SELLS BOOTS ' * 200}</p>"
            f"<p>Item 1A. Risk Factors</p><p>{LONG}</p></body></html>")
    s = parse(html)
    assert "SELLS BOOTS" in s["item1"]
    assert len(s["item1"]) > 1_000


def test_a_heading_repeated_in_a_page_header_does_not_win():
    """Filings that print "Item 1A. Risk Factors" in the running header of every page offer a
    dozen candidates. The one that reaches the next item is the section."""
    pages = "".join(f"<p>Item 1A. Risk Factors</p><p>page {i} of risk text. {LONG}</p>"
                    for i in range(4))
    html = (f"<html><body><p>Item 1. Business</p><p>{LONG}</p>{pages}"
            f"<p>Item 8. Financial Statements</p><p>See the index.</p></body></html>")
    s = parse(html)
    assert "page 0 of risk text" in s["item1a"]
    assert "page 3 of risk text" in s["item1a"]   # one section, not the last page only


# ---------------------------------------------------------------- false headings

def test_a_cross_reference_mid_sentence_does_not_start_a_section():
    body = ("We depend on one supplier, as described in Item 1A. Risk Factors below, and the "
            "loss of that supplier would matter. ") * 20
    s = parse(filing(business=body))
    assert "one supplier" in s["item1"]
    assert len(s["item1a"]) > 1_000          # the real Item 1A, not the cross-reference


def test_a_heading_without_its_prescribed_title_is_not_a_heading():
    """"Item 1" followed by anything other than Business is a numbered list, not the form."""
    html = ("<html><body><p>Item 1. Our first commitment</p><p>We care about people.</p>"
            f"<p>Item 1. Business</p><p>{'REAL ' * 300}</p>"
            f"<p>Item 1A. Risk Factors</p><p>{LONG}</p></body></html>")
    assert "REAL" in parse(html)["item1"]


def test_a_stub_shorter_than_the_minimum_is_reported_missing_not_stored():
    s = parse(filing(business="Too short."))
    assert "item1" not in s
    assert "item1a" in s                     # the rest of the filing still parses


def test_item_3_may_legitimately_be_one_word():
    """Item 1 has a floor because a short Item 1 means a mis-slice. Item 3 does not: "None."
    is the commonest Legal Proceedings disclosure in the index."""
    assert parse(filing(legal="None."))["item3"].lower().endswith("none.")


# ---------------------------------------------------------------- real-filing shapes

def test_headings_split_across_inline_xbrl_spans_are_still_found():
    """Modern 10-Ks are inline XBRL and break words across tags. Stripping tags to nothing
    would join "Item" to "1A"; stripping them to a space keeps the heading readable."""
    html = ("<html><body>"
            "<p><span>Item</span><span>&#160;1.</span><span> Business</span></p>"
            f"<p>{LONG}</p>"
            f"<p><span>Item</span> <span>1A.</span> <span>Risk Factors</span></p><p>{LONG}</p>"
            "</body></html>")
    s = parse(html)
    assert "item1" in s and "item1a" in s


def test_a_part_prefix_on_the_heading_line_is_tolerated():
    html = ("<html><body>"
            f"<p>PART I &#8212; Item 1. BUSINESS</p><p>{LONG}</p>"
            f"<p>PART I &#8212; Item 1A. RISK FACTORS</p><p>{LONG}</p></body></html>")
    assert set(parse(html)) >= {"item1", "item1a"}


def test_entities_are_decoded_and_whitespace_collapsed():
    html = f"<html><body><p>Item 1. Business</p><p>Caf&#233;s &amp;&#160;&#160;bars. {LONG}</p>" \
           f"<p>Item 1A. Risk Factors</p><p>{LONG}</p></body></html>"
    assert "Cafés & bars." in parse(html)["item1"]


def test_a_filing_with_no_item_headings_at_all_yields_nothing():
    assert parse("<html><body><p>Annual report.</p><p>We had a good year.</p></body></html>") == {}


def test_an_item_incorporated_by_reference_is_absent_rather_than_invented():
    """Some filers put MD&A in an exhibit. There is then no Item 7 to slice, and the builder
    reports the gap instead of handing a brief someone else's words."""
    html = ("<html><body>"
            f"<p>Item 1. Business</p><p>{LONG}</p>"
            f"<p>Item 1A. Risk Factors</p><p>{LONG}</p>"
            "<p>Item 8. Financial Statements</p><p>See the index.</p></body></html>")
    s = parse(html)
    assert "item1" in s and "item7" not in s


# ---------------------------------------------------------------- storage

def test_gzip_is_deterministic_so_an_unchanged_filing_does_not_churn_the_repo():
    """gzip stamps the current time into its header by default, which would rewrite all five
    hundred files on every run and make the diff useless."""
    a = gz_bytes({"cik": 1, "sections": {"item1": "x"}})
    b = gz_bytes({"cik": 1, "sections": {"item1": "x"}})
    assert a == b


def test_what_is_written_reads_back_as_what_went_in():
    body = gz_bytes({"cik": 320193, "sections": {"item1": "Cafés & bars."}})
    with gzip.open(io.BytesIO(body), "rt") as fh:
        assert json.load(fh)["sections"]["item1"] == "Cafés & bars."
