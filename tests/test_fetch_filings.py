"""fetch_filings.py without the network: the text converter, the 10-K section splitter, the XBRL reader, the
change summary and the choice of filings to keep. The first run's bug is pinned: a hidden iXBRL header nested in
a display:none div left the rest of Apple's 10-K hidden (77K of 211K characters kept)."""
import datetime as dt

import fetch_filings as F


def test_text_skips_nested_hidden_blocks_and_resumes():
    raw = ('<html><body><div style="display:none"><div><ix:header><ix:hidden>SECRET</ix:hidden></ix:header></div>'
           '<div>also hidden</div></div><p>Item 1. Business</p><div>We sell things.</div>'
           '<table><tr><td>Revenue</td><td>100</td></tr></table></body></html>')
    t = F.to_text(raw)
    assert "SECRET" not in t and "also hidden" not in t
    assert "Item 1. Business" in t and "We sell things." in t
    assert "Revenue | 100" in t


def test_text_keeps_plain_text_filings():
    assert F.to_text("PLAIN FILING TEXT\nline two") == "PLAIN FILING TEXT\nline two"


def test_sections_use_the_heading_after_the_table_of_contents():
    toc = "\n".join(f"Item {i}. Heading {i}" for i in ("1", "1A", "7", "8"))
    body = "\n".join(f"Item {i}. Heading {i}\n" + "x" * 1000 for i in ("1", "1A", "7", "8"))
    text = "TABLE OF CONTENTS\n" + toc + "\n\nPART I\n" + body
    s = F.sections(text)
    assert set(s) == {"1", "1a", "7", "8"}
    start, end = s["7"]
    assert text[start:end].strip().startswith("Item 7.") and end - start > 1000
    assert start > text.index("PART I")                       # not the table-of-contents line


XBRL = b"""<?xml version="1.0"?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:us-gaap="http://fasb.org/us-gaap/2025"
 xmlns:dei="http://xbrl.sec.gov/dei/2025" xmlns:xbrldi="http://xbrl.org/2006/xbrldi"
 xmlns:iso4217="http://www.xbrl.org/2003/iso4217" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
 <xbrli:context id="D"><xbrli:entity><xbrli:identifier scheme="x">1</xbrli:identifier></xbrli:entity>
  <xbrli:period><xbrli:startDate>2025-01-01</xbrli:startDate><xbrli:endDate>2025-12-31</xbrli:endDate></xbrli:period></xbrli:context>
 <xbrli:context id="I"><xbrli:entity><xbrli:identifier scheme="x">1</xbrli:identifier></xbrli:entity>
  <xbrli:period><xbrli:instant>2026-02-01</xbrli:instant></xbrli:period></xbrli:context>
 <xbrli:context id="IA"><xbrli:entity><xbrli:identifier scheme="x">1</xbrli:identifier>
  <xbrli:segment><xbrldi:explicitMember dimension="us-gaap:StatementClassOfStockAxis">us-gaap:CommonClassAMember</xbrldi:explicitMember></xbrli:segment>
  </xbrli:entity><xbrli:period><xbrli:instant>2026-02-01</xbrli:instant></xbrli:period></xbrli:context>
 <xbrli:context id="IB"><xbrli:entity><xbrli:identifier scheme="x">1</xbrli:identifier>
  <xbrli:segment><xbrldi:explicitMember dimension="us-gaap:StatementClassOfStockAxis">us-gaap:CommonClassBMember</xbrldi:explicitMember></xbrli:segment>
  </xbrli:entity><xbrli:period><xbrli:instant>2026-02-01</xbrli:instant></xbrli:period></xbrli:context>
 <xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>
 <xbrli:unit id="sh"><xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unit>
 <us-gaap:Revenues contextRef="D" unitRef="usd" decimals="-6">1000000</us-gaap:Revenues>
 <us-gaap:DebtCurrent contextRef="I" unitRef="usd" xsi:nil="true"/>
 <dei:EntityCommonStockSharesOutstanding contextRef="IA" unitRef="sh">300</dei:EntityCommonStockSharesOutstanding>
 <dei:EntityCommonStockSharesOutstanding contextRef="IB" unitRef="sh">100</dei:EntityCommonStockSharesOutstanding>
 <dei:DocumentType contextRef="D">10-K</dei:DocumentType>
</xbrli:xbrl>"""


def test_xbrl_keeps_dimensioned_facts_and_skips_nil():
    f = F.xbrl_facts(XBRL)
    assert f["us-gaap:Revenues"] == [[1000000.0, "USD", "2025-01-01", "2025-12-31", {}]]
    assert "us-gaap:DebtCurrent" not in f                           # nil
    classes = {r[4]["us-gaap:StatementClassOfStockAxis"]: r[0] for r in f["dei:EntityCommonStockSharesOutstanding"]}
    assert classes == {"us-gaap:CommonClassAMember": 300.0, "us-gaap:CommonClassBMember": 100.0}
    assert f["dei:DocumentType"][0][0] == "10-K"


def test_summary_reports_every_share_class():
    s = F.summary(F.xbrl_facts(XBRL))
    assert s["revenue"] == [1000000.0, "2025-01-01", "2025-12-31"]
    assert s["shares_by_class"] == {"us-gaap:CommonClassAMember": 300.0, "us-gaap:CommonClassBMember": 100.0}


def test_plan_keeps_latest_10k_later_10qs_latest_proxy_and_recent_8ks():
    today = F.TODAY
    old = str(today - dt.timedelta(days=500))
    recent = str(today - dt.timedelta(days=30))
    rows = [("10-K", str(today - dt.timedelta(days=700)), "a1"), ("10-Q", str(today - dt.timedelta(days=600)), "a2"),
            ("10-K", str(today - dt.timedelta(days=200)), "a3"), ("10-Q", str(today - dt.timedelta(days=100)), "a4"),
            ("DEF 14A", str(today - dt.timedelta(days=400)), "a5"), ("DEF 14A", str(today - dt.timedelta(days=150)), "a6"),
            ("8-K", old, "a7"), ("8-K", recent, "a8"), ("4", recent, "a9")]
    sub = {"filings": {"recent": {"form": [r[0] for r in rows], "filingDate": [r[1] for r in rows],
                                  "accessionNumber": [r[2] for r in rows], "primaryDocument": ["d.htm"] * len(rows),
                                  "reportDate": [""] * len(rows)}}}
    assert sorted(x["acc"] for x in F.plan(sub)) == ["a3", "a4", "a6", "a8"]


def test_plan_without_a_10k_keeps_nothing():
    sub = {"filings": {"recent": {"form": ["8-K"], "filingDate": [str(F.TODAY)], "accessionNumber": ["x"],
                                  "primaryDocument": ["d"], "reportDate": [""]}}}
    assert F.plan(sub) == []
