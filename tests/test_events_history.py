"""events_history/: the never-pruned copy of the events feed, and the backfill reader.

`events/<CIK>.json` keeps 400 days, so a backtest over it could only ever cover about a year.
The history file keeps everything the feed has seen, merged by accession. No network."""
import json

import build_sec_events as be

BLOCK = {"form": ["8-K", "4", "10-Q", "8-K"], "filingDate": ["2026-09-01", "2026-08-20", "2026-08-05", "2020-02-03"],
         "accessionNumber": ["a1", "x", "a2", "a3"], "items": ["2.02,9.01", "", "", "5.02"],
         "primaryDocument": ["d1.htm", "f4.xml", "q.htm", "old.htm"], "reportDate": ["2026-09-01", "", "2026-06-30", "2020-02-01"]}


def test_rows_from_block_keeps_the_feed_forms_since_the_cutoff():
    rows = be.rows_from_block(BLOCK, 123, "2025-01-01")
    assert [r["accession"] for r in rows] == ["a1", "a2"]
    assert rows[0]["items"] == ["2.02", "9.01"] and rows[0]["url"].endswith("/123/a1/d1.htm")
    assert [r["accession"] for r in be.rows_from_block(BLOCK, 123, "2019-01-01")] == ["a1", "a2", "a3"]


def test_merge_is_a_union_that_keeps_resolved_exhibits():
    old = [{"accession": "a1", "date": "2026-09-01", "exhibits": [{"type": "EX-99.1", "url": "u"}]},
           {"accession": "a0", "date": "2024-01-02"}]
    new = [{"accession": "a1", "date": "2026-09-01", "items": ["2.02"]},
           {"accession": "a2", "date": "2026-09-10"}]
    got = be.merge_history(old, new)
    assert [e["accession"] for e in got] == ["a2", "a1", "a0"]          # nothing aged out, newest first
    assert got[1]["exhibits"] == [{"type": "EX-99.1", "url": "u"}] and got[1]["items"] == ["2.02"]


def test_seed_copies_existing_event_files_once(tmp_path, monkeypatch):
    ev, hist = tmp_path / "events", tmp_path / "events_history"
    ev.mkdir(); hist.mkdir()
    monkeypatch.setattr(be, "EV_DIR", ev); monkeypatch.setattr(be, "HIST_DIR", hist)
    (ev / "1.json").write_text(json.dumps({"cik": 1, "name": "A", "events": [{"accession": "a", "date": "2026-01-01"}]}))
    assert be.seed_history() == 1
    assert json.loads((hist / "1.json").read_text())["events"][0]["accession"] == "a"
    assert be.seed_history() == 0                                         # already seeded: untouched


def test_write_history_accumulates_across_runs(tmp_path, monkeypatch):
    monkeypatch.setattr(be, "HIST_DIR", tmp_path)
    meta = {"cik": 7, "name": "Z", "tickers": ["Z"]}
    assert be.write_history(7, meta, [{"accession": "a", "date": "2025-01-01"}])
    assert be.write_history(7, meta, [{"accession": "b", "date": "2026-01-01"}])
    assert not be.write_history(7, meta, [{"accession": "b", "date": "2026-01-01"}])   # nothing new
    assert [e["accession"] for e in json.loads((tmp_path / "7.json").read_text())["events"]] == ["b", "a"]


def test_backfill_reads_older_submission_pages(monkeypatch):
    class R:
        def __init__(self, j): self._j = j
        def json(self): return self._j
    recent = {"form": ["8-K"], "filingDate": ["2026-09-01"], "accessionNumber": ["new"], "items": ["8.01"],
              "primaryDocument": ["n.htm"], "reportDate": [""]}
    page = {"form": ["8-K", "8-K"], "filingDate": ["2019-05-01", "2010-01-01"], "accessionNumber": ["old", "older"],
            "items": ["1.01", "3.02"], "primaryDocument": ["o.htm", "p.htm"], "reportDate": ["", ""]}
    sub = {"name": "Z", "tickers": ["Z"], "filings": {"recent": recent, "files": [
        {"name": "CIK0000000007-submissions-001.json", "filingTo": "2019-12-31"},
        {"name": "CIK0000000007-submissions-002.json", "filingTo": "2008-12-31"}]}}
    calls = []
    def fake_get(url, *a, **k):
        calls.append(url)
        return R(page) if "submissions-001" in url else R(sub)
    monkeypatch.setattr(be, "get", fake_get)
    from datetime import date
    meta, rows, hist = be.company_events(7, date(2025, 9, 1), "2015-01-01")
    assert [r["accession"] for r in rows] == ["new"]                      # events/ window unchanged
    assert [r["accession"] for r in hist] == ["new", "old"]               # 2010 is before the backfill date
    assert not any("submissions-002" in c for c in calls)                 # a page wholly before it is skipped
