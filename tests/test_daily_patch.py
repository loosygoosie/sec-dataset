"""The daily patch-only run (`patch_companies.py`, `.github/workflows/companies-patch.yml`).

Three promises, each pinned here because breaking any of them is silent:

1. SELECTION — only a company whose events feed shows a 10-Q/10-K newer than its file is touched.
2. NOTHING ELSE MOVES — every other company file stays byte-identical, nothing is deleted, and a
   second run the same day writes nothing.
3. IDENTITY — a company the daily run rewrites is byte-for-byte what the weekly build (`main()`)
   writes for it from the same SEC data, whether companyfacts has caught up or the quarter has to
   be read from the filing's own XBRL instance.

No network: `get` and `filing_instance_url` are replaced, and the weekly build is run for real
against a tiny companyfacts zip with its 3,000-company floor lowered.
"""
from __future__ import annotations

import json
import shutil
import zipfile
from datetime import date

import pytest

from conftest import doc, fy_fact, q_fact, usd

TODAY = date.today()


# --------------------------------------------------------------------------
# Selection
# --------------------------------------------------------------------------
@pytest.fixture
def P():
    import patch_companies

    return patch_companies


def _rec(lq="2026-03-31", la="2025-12-31", filed="2026-04-30", q_source=None):
    q = {"period_end": lq, "filed": filed}
    if q_source:
        q["source"] = q_source
    return {"annual": [{"period_end": la, "filed": "2026-02-20"}], "quarterly": [q],
            "checks": {"latest_quarter_end": lq, "quarter_age_days": 100}}


def ev(form, period, filed, acc="0000000000-26-000001"):
    return {"form": form, "period": period, "date": filed, "accession": acc}


def test_a_newer_10q_is_picked(P):
    assert P.why_behind(_rec(), [ev("10-Q", "2026-06-30", "2026-07-30")], TODAY) == ["quarter"]


def test_a_filing_for_the_quarter_already_held_is_not(P):
    """A 52/53-week filer's quarter ends a few days off the calendar date: same quarter."""
    rec = _rec(lq="2026-06-27", filed="2026-07-31")
    assert P.why_behind(rec, [ev("10-Q", "2026-06-30", "2026-07-31")], TODAY) == []


def test_an_8k_never_picks_a_company(P):
    assert P.why_behind(_rec(), [ev("8-K", "2026-07-30", "2026-07-30")], TODAY) == []


def test_a_notification_of_late_filing_is_not_a_filing(P):
    assert P.why_behind(_rec(), [ev("NT 10-K", "2026-06-30", "2026-07-30")], TODAY) == []


def test_a_10k_whose_closing_quarter_came_only_from_the_filing_is_picked_for_its_annual_row(P):
    """The fallback adds quarters, never annual rows: Clorox's FY2026 Q4 was read from its 10-K
    and the year itself waits for companyfacts."""
    rec = _rec(lq="2026-06-30", la="2025-06-30", filed="2026-08-07", q_source="filing")
    assert P.why_behind(rec, [ev("10-K", "2026-06-30", "2026-08-07")], TODAY) == ["annual"]


def test_a_missing_annual_row_that_companyfacts_already_had_is_not_refetched(P):
    """Paramount Skydance: quarters from companyfacts run past its 10-K, and no full year comes
    out of it (a post-merger stub). Picking it would refetch the same answer every day."""
    rec = _rec(lq="2026-06-30", la="2024-12-31", filed="2026-08-04")
    assert P.why_behind(rec, [ev("10-K", "2025-12-31", "2026-02-25")], TODAY) == []


def test_a_recent_amendment_of_a_held_period_is_picked(P):
    recent = TODAY.isoformat()
    assert P.why_behind(_rec(), [ev("10-K/A", "2025-12-31", recent)], TODAY) == ["filed"]


def test_an_old_amendment_is_left_to_the_weekly_build(P):
    """A 10-K/A carrying only Part III changes nothing and would otherwise be refetched daily for
    the 400 days the events feed keeps it."""
    rec = _rec(filed="2026-01-15")                       # newest filing held: the 10-K of 2026-02-20
    assert P.why_behind(rec, [ev("10-K/A", "2025-12-31", "2026-03-01")], TODAY) == []


def _tree(tmp_path, monkeypatch, b, companies: dict, events: dict, sp500=()):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data/companies").mkdir(parents=True)
    (tmp_path / "data/events").mkdir(parents=True)
    for cik, rec in companies.items():
        (tmp_path / f"data/companies/{cik}.json").write_text(json.dumps({**rec, "cik": cik}))
    for cik, evs in events.items():
        (tmp_path / f"data/events/{cik}.json").write_text(json.dumps({"events": evs}))
    if sp500:
        (tmp_path / "data/sp500.json").write_text(json.dumps({"companies": [{"cik": c} for c in sp500]}))


def test_selection_needs_both_a_company_file_and_an_events_record(P, b, tmp_path, monkeypatch):
    new = ev("10-Q", "2026-06-30", "2026-07-30")
    _tree(tmp_path, monkeypatch, b, {1: _rec(), 2: _rec()}, {1: [new], 3: [new]})
    assert [t["cik"] for t in P.select_targets(TODAY, set())] == [1]


def test_index_members_first_then_the_most_stale(P, b, tmp_path, monkeypatch):
    new = ev("10-Q", "2026-06-30", "2026-07-30")
    old = {**_rec(), "checks": {"latest_quarter_end": "2026-03-31", "quarter_age_days": 300}}
    _tree(tmp_path, monkeypatch, b, {1: _rec(), 2: old, 3: _rec()}, {1: [new], 2: [new], 3: [new]}, sp500=(3,))
    assert [t["cik"] for t in P.select_targets(TODAY, P.load_priority())] == [3, 2, 1]


# --------------------------------------------------------------------------
# The weekly build and the daily run, side by side
# --------------------------------------------------------------------------
A, B_, C, D = 1001, 1002, 1003, 1004     # current; companyfacts caught up; companyfacts behind; no events


def _facts(cik, quarters):
    """FY2025 plus the given 2026 quarter ends, revenue and net income only."""
    rev = [fy_fact(4_000_000_000 + cik, "2025-12-31", filed="2026-02-20", fy=2025)]
    ni = [fy_fact(400_000_000 + cik, "2025-12-31", filed="2026-02-20", fy=2025)]
    for i, qe in enumerate(quarters):
        filed = {"2026-03-31": "2026-04-30", "2026-06-30": "2026-07-30"}[qe]
        rev.append(q_fact(1_000_000_000 + cik + i, qe, filed=filed, fy=2026))
        ni.append(q_fact(100_000_000 + cik + i, qe, filed=filed, fy=2026))
    return doc(us_gaap={"Revenues": usd(*rev), "NetIncomeLoss": usd(*ni)}, cik=cik, name=f"Filer {cik}")


V1 = {A: _facts(A, ["2026-03-31", "2026-06-30"]), B_: _facts(B_, ["2026-03-31"]),
      C: _facts(C, ["2026-03-31"]), D: _facts(D, ["2026-03-31"])}
V2 = {**V1, B_: _facts(B_, ["2026-03-31", "2026-06-30"])}       # B caught up in companyfacts; C did not

INSTANCE = """<?xml version="1.0"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:us-gaap="http://fasb.org/us-gaap/2026">
  <context id="q2"><entity><identifier scheme="x">1003</identifier></entity>
    <period><startDate>2026-04-01</startDate><endDate>2026-06-30</endDate></period></context>
  <unit id="usd"><measure>iso4217:USD</measure></unit>
  <us-gaap:Revenues contextRef="q2" unitRef="usd">1234000000</us-gaap:Revenues>
  <us-gaap:NetIncomeLoss contextRef="q2" unitRef="usd">123000000</us-gaap:NetIncomeLoss>
</xbrl>"""

EVENTS = {A: [ev("10-Q", "2026-06-30", "2026-07-30", "a-q2")],
          B_: [ev("10-Q", "2026-06-30", "2026-07-30", "b-q2")],
          C: [ev("10-Q", "2026-06-30", "2026-07-30", "c-q2"), ev("8-K", "2026-07-29", "2026-07-29", "c-8k")]}


class _Resp:
    def __init__(self, payload):
        self._p = payload
        self.text = payload if isinstance(payload, str) else json.dumps(payload)

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def sec(b, monkeypatch):
    """A fake SEC: companyfacts per CIK from `sec.facts`, one instance per accession. Records
    every URL asked for, so a test can say what was NOT fetched."""
    class Fake:
        facts: dict = V2
        asked: list = []

        def get(self, url, *a, **kw):
            self.asked.append(url)
            if "companyfacts" in url:
                return _Resp(self.facts[int(url.split("CIK")[1][:10])])
            assert url == "inst://c-q2", url
            return _Resp(INSTANCE)

    f = Fake()
    f.asked = []
    monkeypatch.setattr(b, "get", f.get)
    monkeypatch.setattr(b, "filing_instance_url", lambda cik, acc: f"inst://{acc}")
    return f


def _weekly(b, monkeypatch, root, facts, events):
    """Run the real weekly build in `root` against a companyfacts zip holding `facts`."""
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(root)
    (root / "work").mkdir(exist_ok=True)
    (root / "data/events").mkdir(parents=True, exist_ok=True)
    for p in (root / "data/events").glob("*.json"):
        p.unlink()
    for cik, evs in events.items():
        (root / f"data/events/{cik}.json").write_text(json.dumps({"cik": cik, "events": evs}))
    with zipfile.ZipFile(root / "work/companyfacts.zip", "w") as z:
        for cik, f in facts.items():
            z.writestr(f"CIK{cik:010d}.json", json.dumps(f))
    monkeypatch.setattr(b, "MIN_COMPANIES", 1)
    monkeypatch.setattr(b, "load_ticker_maps", lambda: ({"AAA": {"cik": A, "name": "a"}}, {A: ["AAA"]}))
    monkeypatch.setattr(b, "sp500_snapshot", lambda *a, **k: (None, "offline test"))
    assert b.main() == 0
    (root / "work/companyfacts.zip").unlink()


def _snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in (root / "data").rglob("*") if p.is_file()}


@pytest.fixture
def worlds(b, sec, monkeypatch, tmp_path):
    """`before`: last Sunday's build, before B or C filed their June quarter. `weekly`: what a build
    run today writes. `daily`: last Sunday's files plus today's events, patched by the daily run."""
    _weekly(b, monkeypatch, tmp_path / "before", V1, {})
    _weekly(b, monkeypatch, tmp_path / "weekly", V2, EVENTS)
    daily = tmp_path / "daily"
    shutil.copytree(tmp_path / "before", daily)
    for cik, evs in EVENTS.items():
        (daily / f"data/events/{cik}.json").write_text(json.dumps({"cik": cik, "events": evs}))
    monkeypatch.chdir(daily)
    sec.asked.clear()
    return tmp_path


def test_the_daily_run_writes_exactly_what_the_weekly_build_writes(P, worlds):
    s = P.run()
    for cik in (B_, C):
        name = f"data/companies/{cik}.json"
        assert (worlds / "daily" / name).read_bytes() == (worlds / "weekly" / name).read_bytes(), cik
    assert {c["cik"]: c["via"] for c in s["changed"]} == {B_: "companyfacts", C: "companyfacts+filing"}


def test_the_filing_fallback_really_ran_for_the_company_companyfacts_has_not_caught_up_with(P, worlds):
    P.run()
    q = json.loads((worlds / "daily" / f"data/companies/{C}.json").read_text())["quarterly"][-1]
    assert (q["period_end"], q.get("source"), q["revenue"]) == ("2026-06-30", "filing", 1234000000)


def test_the_manifest_entries_it_rewrites_match_the_weekly_build_and_no_other_moves(P, worlds):
    before = json.loads((worlds / "before/data/manifest.json").read_text())
    weekly = json.loads((worlds / "weekly/data/manifest.json").read_text())
    P.run()
    daily = json.loads((worlds / "daily/data/manifest.json").read_text())
    for cik in (B_, C):
        assert daily["companies"][str(cik)] == weekly["companies"][str(cik)]
    for cik in (A, D):
        assert daily["companies"][str(cik)] == before["companies"][str(cik)]
    assert {k: v for k, v in daily.items() if k != "companies"} == \
           {k: v for k, v in before.items() if k != "companies"}


def test_every_other_file_stays_byte_identical_and_nothing_is_deleted(P, worlds):
    root = worlds / "daily"
    was = _snapshot(root)
    mtimes = {p: (root / p).stat().st_mtime_ns for p in was}
    P.run()
    now = _snapshot(root)
    assert set(now) == set(was), "a file appeared or vanished"
    moved = {p for p in was if now[p] != was[p]}
    assert moved == {f"data/companies/{B_}.json", f"data/companies/{C}.json", "data/manifest.json"}
    for p in was:
        if p not in moved:
            assert (root / p).stat().st_mtime_ns == mtimes[p], f"{p} was rewritten"


def test_only_the_picked_companies_are_fetched(P, worlds, sec):
    P.run()
    assert sorted(u for u in sec.asked if "companyfacts" in u) == sorted(
        P.COMPANYFACTS_URL.format(cik=c) for c in (B_, C))
    assert "inst://c-q2" in sec.asked and not any(u.startswith("inst://a") for u in sec.asked)


def test_a_second_run_writes_nothing(P, worlds):
    P.run()
    root = worlds / "daily"
    was = _snapshot(root)
    s = P.run()
    assert _snapshot(root) == was
    assert s["changed"] == []


def test_select_only_makes_no_request_and_writes_nothing(P, worlds, sec):
    root = worlds / "daily"
    was = _snapshot(root)
    s = P.run(select_only=True)
    assert sec.asked == [] and _snapshot(root) == was
    assert sorted(t["cik"] for t in s["targets"]) == [B_, C]


def test_a_company_the_weekly_build_would_drop_is_left_alone_not_pruned(P, worlds, sec):
    sec.facts = {**V2, B_: doc(us_gaap={}, cik=B_)}      # nothing readable comes back
    root = worlds / "daily"
    was = (root / f"data/companies/{B_}.json").read_bytes()
    s = P.run()
    assert (root / f"data/companies/{B_}.json").read_bytes() == was
    assert B_ in [h["cik"] for h in s["held"]]


def test_a_short_read_that_would_lose_history_is_held_back(P, worlds, sec):
    sec.facts = {**V2, B_: _facts(B_, [])}               # companyfacts without the quarters we hold
    root = worlds / "daily"
    was = (root / f"data/companies/{B_}.json").read_bytes()
    s = P.run()
    assert (root / f"data/companies/{B_}.json").read_bytes() == was
    assert any(h["cik"] == B_ and "newest quarter" in h["why"] for h in s["held"])


def test_the_cap_leaves_the_rest_for_tomorrow(P, worlds, sec):
    s = P.run(max_companies=1)
    assert len(s["changed"]) == 1 and len(s["not_reached"]) == 1
    assert len([u for u in sec.asked if "companyfacts" in u]) == 1


# --------------------------------------------------------------------------
# The workflow: cannot race the weekly build, gated at least as hard, dry by default by hand
# --------------------------------------------------------------------------
import pathlib  # noqa: E402
import re  # noqa: E402

WF = pathlib.Path(__file__).resolve().parent.parent / ".github/workflows"


def _group(text):
    m = re.search(r"^concurrency:\s*\n\s+group:\s*(\S+)", text, re.M)
    return m and m.group(1)


def test_it_shares_the_weekly_builds_concurrency_group():
    """Both write data/companies/ and the manifest; running at once would interleave commits."""
    assert _group((WF / "companies-patch.yml").read_text()) == _group((WF / "sec.yml").read_text()) == "sec-dataset"


def test_it_gates_on_every_suite_the_weekly_build_gates_on():
    gated = lambda t: set(re.findall(r"tests/test_\w+\.py", t.split("Prove the builder", 1)[1].split("- name:", 1)[0]))
    weekly, daily = gated((WF / "sec.yml").read_text()), gated((WF / "companies-patch.yml").read_text())
    assert weekly and weekly <= daily and "tests/test_daily_patch.py" in daily


def test_a_manual_run_commits_nothing_unless_asked():
    t = (WF / "companies-patch.yml").read_text()
    assert re.search(r"dry_run:\s*\n(\s+\w+:.*\n)*?\s+default:\s*\"true\"", t)
    assert "if: github.event_name == 'schedule' || inputs.dry_run == 'false'" in t
    assert "[skip ci]" in t and "SEC_USER_AGENT: ${{ secrets.SEC_USER_AGENT }}" in t


def test_it_never_runs_on_the_weekly_builds_day():
    assert re.search(r'cron:\s*"0 7 \* \* 1-6"', (WF / "companies-patch.yml").read_text())
