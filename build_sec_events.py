#!/usr/bin/env python3
"""
build_sec_events.py — the company-news feed, straight from EDGAR.

Every day this reads the SEC's daily filing index for the last few days, takes every 8-K
(and 10-K / 10-Q / 8-K/A), and for each filer pulls the SEC's own submissions record, which
carries the 8-K ITEM CODES — the company's own classification of what it is announcing:

    1.01 material agreement        2.02 results of operations / guidance
    2.04 triggering events         2.05 exit / disposal costs        2.06 impairments
    3.01 delisting notice          4.01 auditor change               4.02 non-reliance on prior financials (restatement)
    5.02 director / officer departure or appointment
    7.01 Reg FD disclosure         8.01 other events                 1.05 material cybersecurity incident

Outputs (committed to data/):
    events/<CIK>.json      — that company's filings in the last EVENT_DAYS days: date, form, items, accession,
                             primary document URL. Rewritten only when it changes.
    events_recent.json     — the last RECENT_DAYS days across every filer, newest first, one row per filing:
                             {date, cik, tickers, name, form, items, url}. Small; the monitors read this.
    events_report.md       — counts.

Rate limits: the SEC asks for ≤ 10 requests/second and a descriptive User-Agent (SEC_USER_AGENT).
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

USER_AGENT = os.environ.get("SEC_USER_AGENT", "sec-dataset research (set SEC_USER_AGENT)")
HEADERS = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}
DAILY_INDEX = "https://www.sec.gov/Archives/edgar/daily-index/{year}/QTR{q}/form.{ymd}.idx"
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
ARCHIVE_DOC = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{doc}"
FILING_INDEX = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{acc}-index.html"

LOOKBACK_DAYS = int(os.environ.get("LOOKBACK_DAYS", "5"))   # index days to scan each run (covers a weekend + a missed run)
EVENT_DAYS = 400                                            # per-company history kept
RECENT_DAYS = 90                                            # the cross-company recent file
FORMS = {"8-K", "8-K/A", "10-K", "10-K/A", "10-Q", "10-Q/A"}
EXHIBIT_FORMS = {"8-K", "8-K/A"}       # the substance of a 2.02 is in EX-99.1, not the cover page
EXHIBIT_DAYS = RECENT_DAYS             # resolve exhibits for the window the recent feed covers
EXHIBIT_CAP = 2000                     # index fetches per run; a filing's index never changes, so this is a one-off cost per filing
OUT_DIR = Path("data"); EV_DIR = OUT_DIR / "events"
CIK_OVERRIDES_PATH = OUT_DIR / "cik_overrides.json"   # hand-maintained; shared with build_sec_dataset.py

_last = [0.0]
def get(url: str, retries: int = 4, timeout: int = 60) -> requests.Response | None:
    for i in range(retries):
        gap = time.time() - _last[0]
        if gap < 0.12:                        # ~8 requests/second, under the SEC's 10/s
            time.sleep(0.12 - gap)
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        _last[0] = time.time()
        if r.status_code == 200:
            return r
        if r.status_code == 404:
            return None
        time.sleep(2 * (i + 1))
    return None


_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
_HREF = re.compile(r'href="([^"]+)"')
_TAGS = re.compile(r"<[^>]+>")


def exhibits_for(cik: int, accession: str) -> list[dict] | None:
    """The documents attached to a filing, from its EDGAR index page.

    `url` on an event is the primary document, which for an 8-K is the cover page — it says a
    2.02 happened but not what was announced. The earnings release itself is EX-99.1. The index
    page's document table carries a Type per row, which is the only place that label appears:
    index.json's `type` is the icon name, and the SGML header carries only the filing's own type.

    Returns [] when the filing genuinely attached nothing readable, and None when the index could
    not be read — the caller keeps those distinct so a transient failure is retried next run
    rather than cached as 'no exhibits'. EX-100/EX-101 rows are the XBRL taxonomy files, not
    something a reader would open."""
    r = get(FILING_INDEX.format(cik=cik, acc_nodash=accession.replace("-", ""), acc=accession))
    if r is None:
        return None
    out: list[dict] = []
    for row in _ROW.findall(r.text):
        cells = [_TAGS.sub("", c).strip() for c in _CELL.findall(row)]
        if len(cells) < 4:
            continue
        typ = cells[3]
        if not typ.startswith("EX-") or typ.startswith(("EX-100", "EX-101")):
            continue
        m = _HREF.search(row)
        if not m:
            continue
        href = m.group(1)
        if href.startswith("/ix?doc="):          # inline-XBRL documents are linked through the viewer
            href = href[len("/ix?doc="):]
        out.append({"type": typ, "url": "https://www.sec.gov" + href})
    return out


def load_ticker_overrides() -> dict[int, list[str]]:
    """cik -> tickers, inverted from the hand-maintained data/cik_overrides.json.

    When a reorganisation moves a ticker to a new holding CIK, the SEC's submissions record
    for the operating company carries no ticker at all, so its 8-Ks and 10-Qs arrive in the
    feed untagged and a monitor watching by ticker never sees them. The override puts the
    ticker back on that CIK. It does not take the ticker off the new registrant: during a
    reorganisation both entities file, and both streams matter."""
    try:
        j = json.loads(CIK_OVERRIDES_PATH.read_text())
    except FileNotFoundError:
        return {}
    except Exception as e:  # noqa: BLE001
        print(f"  cik_overrides.json unreadable ({type(e).__name__}); ignoring it")
        return {}
    out: dict[int, list[str]] = defaultdict(list)
    for t, v in (j.get("overrides") or {}).items():
        cik = v.get("cik") if isinstance(v, dict) else v
        try:
            out[int(cik)].append(t.upper().replace(".", "-"))
        except (TypeError, ValueError):
            print(f"  cik_overrides.json: skipping {t!r}, its cik is not a number")
    return {k: sorted(v) for k, v in out.items()}


def tickers_for(cik: int, rec_tickers: list[str] | None, overrides: dict[int, list[str]],
                manifest_tickers: dict[int, list[str]]) -> list[str]:
    """Which tickers a filing is tagged with: the hand-maintained override first, then the SEC's
    own submissions record, then the weekly manifest (which merges the SEC's ticker and exchange
    maps, and carries names the submissions record omits — American Electric Power, for one)."""
    return overrides.get(cik) or rec_tickers or manifest_tickers.get(cik, [])


def index_days(n: int) -> list[date]:
    """Today, plus the n most recent weekdays before it.

    EDGAR accepts filings 06:00-22:00 ET, so at the 03:00 UTC run time today's index does
    not exist yet and get() returns None for it. Counting today towards n therefore made
    the nightly LOOKBACK_DAYS=5 cover only four published days, eating the margin that is
    meant to absorb a weekend plus a missed run. Today is still scanned — a manual midday
    dispatch should see the current day — it just no longer consumes the budget."""
    out, d = [], date.today() - timedelta(days=1)
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d -= timedelta(days=1)
    today = date.today()
    return ([today] if today.weekday() < 5 else []) + out


def filings_from_daily_index(d: date) -> set[int]:
    """CIKs that filed one of FORMS on day d, from form.YYYYMMDD.idx (fixed-width: Form Type | Company | CIK | Date | File)."""
    q = (d.month - 1) // 3 + 1
    r = get(DAILY_INDEX.format(year=d.year, q=q, ymd=d.strftime("%Y%m%d")))
    if r is None:
        return set()
    ciks: set[int] = set()
    for line in r.text.splitlines():
        m = re.match(r"^(\S[^ ]*(?: [^ ]+)*?)\s{2,}(.+?)\s{2,}(\d+)\s{2,}(\d{8})\s{2,}(\S+)\s*$", line)
        if not m:
            continue
        form = m.group(1).strip()
        if form in FORMS:
            ciks.add(int(m.group(3)))
    return ciks


def company_events(cik: int, since: date) -> tuple[dict, list[dict]]:
    """From the submissions record: recent filings of FORMS since `since`, with 8-K item codes."""
    r = get(SUBMISSIONS.format(cik=cik))
    if r is None:
        return {}, []
    j = r.json()
    rec = j.get("filings", {}).get("recent", {})
    keys = ["form", "filingDate", "accessionNumber", "items", "primaryDocument", "reportDate"]
    cols = {k: rec.get(k, []) for k in keys}
    n = len(cols["form"])
    rows = []
    for i in range(n):
        form = cols["form"][i]
        if form not in FORMS:
            continue
        fd = cols["filingDate"][i]
        if fd < since.isoformat():
            continue
        acc = cols["accessionNumber"][i]
        doc = cols["primaryDocument"][i] if i < len(cols["primaryDocument"]) else ""
        items = [x.strip() for x in (cols["items"][i] if i < len(cols["items"]) else "").split(",") if x.strip()]
        rows.append({"date": fd, "form": form, "items": items, "period": (cols["reportDate"][i] if i < len(cols["reportDate"]) else None),
                     "accession": acc, "url": ARCHIVE_DOC.format(cik=cik, acc_nodash=acc.replace("-", ""), doc=doc) if doc else None})
    meta = {"cik": cik, "name": j.get("name"), "tickers": j.get("tickers", []), "sic": j.get("sicDescription")}
    rows.sort(key=lambda x: x["date"], reverse=True)
    return meta, rows


def main() -> int:
    t0 = time.time()
    OUT_DIR.mkdir(exist_ok=True); EV_DIR.mkdir(exist_ok=True)
    days = index_days(LOOKBACK_DAYS)
    print(f"1. daily indexes for {[d.isoformat() for d in days]}")
    ciks: set[int] = set()
    for d in days:
        got = filings_from_daily_index(d)
        print(f"  {d}: {len(got)} filers")
        ciks |= got
    print(f"  {len(ciks)} filers to refresh")

    since = date.today() - timedelta(days=EVENT_DAYS)
    overrides = load_ticker_overrides()
    if overrides:
        print(f"  ticker overrides in force: {overrides}")
    print("2. submissions records")
    ex_cutoff = (date.today() - timedelta(days=EXHIBIT_DAYS)).isoformat()
    ex_budget, ex_fetched, ex_reused = EXHIBIT_CAP, 0, 0
    written = changed = 0
    for i, cik in enumerate(sorted(ciks), 1):
        meta, rows = company_events(cik, since)
        if not meta:
            continue
        if cik in overrides:
            meta["tickers"] = overrides[cik]

        # A filing's index never changes, so exhibits already resolved in the file on disk are
        # reused: the fetch is a one-off cost per filing, not per run.
        p = EV_DIR / f"{cik}.json"
        cached: dict[str, list[dict]] = {}
        if p.exists():
            try:
                for e in json.loads(p.read_text()).get("events", []):
                    if e.get("exhibits") is not None:
                        cached[e["accession"]] = e["exhibits"]
            except Exception:  # noqa: BLE001
                pass
        for e in rows:
            if e["form"] not in EXHIBIT_FORMS or e["date"] < ex_cutoff:
                continue                       # older than the recent window: `url` alone, as before
            if e["accession"] in cached:
                e["exhibits"] = cached[e["accession"]]; ex_reused += 1
            elif ex_budget > 0:
                ex_budget -= 1
                got = exhibits_for(cik, e["accession"])
                if got is not None:            # None = index unreadable; leave the key off and retry next run
                    e["exhibits"] = got; ex_fetched += 1

        rec = {**meta, "events": rows}
        body = json.dumps(rec, separators=(",", ":"), sort_keys=True)
        if not p.exists() or p.read_text() != body:
            p.write_text(body); changed += 1
        written += 1
        if i % 100 == 0:
            print(f"  {i}/{len(ciks)}", flush=True)
    print(f"  {written} records, {changed} changed")
    print(f"  exhibits: {ex_fetched} filings indexed this run, {ex_reused} reused"
          + ("" if ex_budget else f" (hit the {EXHIBIT_CAP} cap; the rest resolve next run)"))

    # prune companies whose newest kept filing has aged out of the EVENT_DAYS window
    pruned = 0
    for p in EV_DIR.glob("*.json"):
        try:
            ev = json.loads(p.read_text()).get("events", [])
        except Exception:  # noqa: BLE001
            p.unlink(); pruned += 1; continue
        if not ev or max(e["date"] for e in ev) < since.isoformat():
            p.unlink(); pruned += 1
    print(f"  {pruned} stale records removed")

    # A company that has not filed inside the lookback window is never refreshed above, so its
    # 8-Ks would never pick up exhibits however many times the feed runs — ADSK's 27 Aug earnings
    # release was still bare after a 5-day run. Sweep whatever is left of the window with the
    # remaining budget, newest first, so the filings a monitor is most likely to open come first.
    if ex_budget > 0:
        todo: list[tuple[str, int, str]] = []
        for p in EV_DIR.glob("*.json"):
            try:
                rec = json.loads(p.read_text())
            except Exception:  # noqa: BLE001
                continue
            for e in rec.get("events", []):
                if e["form"] in EXHIBIT_FORMS and e["date"] >= ex_cutoff and e.get("exhibits") is None:
                    todo.append((e["date"], rec["cik"], e["accession"]))
        todo.sort(reverse=True)
        found: dict[int, dict[str, list]] = defaultdict(dict)
        for _, cik, acc in todo[:ex_budget]:
            got = exhibits_for(cik, acc)
            if got is not None:
                found[cik][acc] = got
        for cik, got in found.items():
            p = EV_DIR / f"{cik}.json"
            try:
                rec = json.loads(p.read_text())
            except Exception:  # noqa: BLE001
                continue
            for e in rec["events"]:
                if e["accession"] in got:
                    e["exhibits"] = got[e["accession"]]
            p.write_text(json.dumps(rec, separators=(",", ":"), sort_keys=True))
            changed += 1
        done = sum(len(v) for v in found.values())
        print(f"  backfill: {done} of {len(todo)} older filings indexed"
              + (f"; {len(todo) - done} left for the next run" if len(todo) > done else ""))

    print("3. recent index")
    # The SEC's submissions record sometimes carries no tickers (American Electric Power, for one);
    # fall back to the weekly build's manifest, which merges the SEC's ticker and exchange maps.
    manifest_tickers: dict[int, list[str]] = {}
    try:
        for k, v in json.loads((OUT_DIR / "manifest.json").read_text()).get("companies", {}).items():
            manifest_tickers[int(k)] = v.get("tickers", [])
    except Exception:  # noqa: BLE001
        pass
    cutoff = (date.today() - timedelta(days=RECENT_DAYS)).isoformat()
    recent = []
    for p in EV_DIR.glob("*.json"):
        try:
            rec = json.loads(p.read_text())
        except Exception:  # noqa: BLE001
            continue
        for e in rec.get("events", []):
            if e["date"] >= cutoff:
                tickers = tickers_for(rec["cik"], rec.get("tickers"), overrides, manifest_tickers)
                row = {"date": e["date"], "cik": rec["cik"], "tickers": tickers, "name": rec.get("name"),
                       "form": e["form"], "items": e["items"], "period": e.get("period"), "url": e.get("url")}
                if e.get("exhibits"):
                    row["exhibits"] = e["exhibits"]
                recent.append(row)
    recent.sort(key=lambda x: (x["date"], x["cik"]), reverse=True)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (OUT_DIR / "events_recent.json").write_text(json.dumps({"generated_utc": generated, "days": RECENT_DAYS, "rows": recent}, separators=(",", ":")))
    by_item: dict[str, int] = defaultdict(int)
    for r in recent:
        for it in r["items"]:
            by_item[it] += 1
    report = [f"# SEC events build — {generated}", "", f"- filers refreshed this run: {written} (changed: {changed})",
              f"- filings in the last {RECENT_DAYS} days: {len(recent)}", "", "## 8-K items in the window", ""]
    report += [f"- {k}: {v}" for k, v in sorted(by_item.items())]
    (OUT_DIR / "events_report.md").write_text("\n".join(report) + "\n")
    print(f"done in {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
