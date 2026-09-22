#!/usr/bin/env python3
"""
build_sec_insiders.py — insider buying and selling, straight from EDGAR's Form 4s.

Every night this reads the SEC's daily filing index for the last few days, takes every Form 4,
fetches the filing, and keeps the open-market trades an insider made in their own company:

    P  purchase — an insider paid cash for shares at the market (the signal most studied)
    S  sale     — an insider sold at the market

Grants, option exercises, tax withholding and gifts (codes A, M, F, G, ...) are compensation or
bookkeeping, not a decision to buy or sell, and are dropped.

Outputs (committed to data/):
    insiders/<ISSUER CIK>.json — every P/S trade this feed has seen for that company, merged by
                                 accession and row, never pruned: {cik, name, ticker, trades: [...]}.
                                 Each trade: accession, filed, date, code, shares, price, value,
                                 owned_after, direct ("D"/"I"), owner, owner_cik, roles, title.
    insiders_recent.json       — the last RECENT_DAYS days of trades across every company, newest
                                 first, under the key **`rows`** (cik is an INTEGER, as in
                                 events_recent.json). The file a scan reads.
    insiders_seen.json         — accessions already read, so the nightly overlap costs nothing.
    insiders_report.md         — counts, and the companies where two or more directors/officers
                                 bought in the last CLUSTER_DAYS days.

History starts the night this feed first runs. The SEC's quarterly Form 3/4/5 data sets
(2006 onward) hold the past; a backfill from them is a separate job, not this one.

Rate limits: the SEC asks for <= 10 requests/second and a descriptive User-Agent (SEC_USER_AGENT),
both inherited from build_sec_events.get().
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from build_sec_events import DAILY_INDEX, get, index_days

LOOKBACK_DAYS = int(os.environ.get("LOOKBACK_DAYS", "5"))
MAX_FILINGS = int(os.environ.get("MAX_FILINGS", "20000"))   # fetches per run; the rest resolve next run
RECENT_DAYS = 90
CLUSTER_DAYS = 30
SEEN_DAYS = 30                          # how long an accession stays in insiders_seen.json
KEEP_CODES = {"P", "S"}
ARCHIVES = "https://www.sec.gov/Archives/"
OUT_DIR = Path("data"); INS_DIR = OUT_DIR / "insiders"
SEEN_PATH = OUT_DIR / "insiders_seen.json"
_IDX = re.compile(r"^(\S[^ ]*(?: [^ ]+)*?)\s{2,}(.+?)\s{2,}(\d+)\s{2,}(\d{8})\s{2,}(\S+)\s*$")


def form4_paths(index_text: str) -> dict[str, str]:
    """accession -> archive path for every Form 4 in a daily form.idx. A Form 4 is listed once per
    filer on it (the issuer AND each reporting owner), so the same path appears more than once."""
    out: dict[str, str] = {}
    for line in index_text.splitlines():
        m = _IDX.match(line)
        if not m or m.group(1).strip() != "4":
            continue
        path = m.group(5)
        acc = path.rsplit("/", 1)[-1].removesuffix(".txt")
        out[acc] = path
    return out


def _v(node, path: str) -> str | None:
    """Text of `path` under node, reading through the <value> wrapper Form 4 puts on most fields."""
    if node is None:
        return None
    el = node.find(path)
    if el is None:
        return None
    val = el.find("value")
    txt = (val.text if val is not None else el.text) or ""
    return txt.strip() or None


def _flag(node, path: str) -> bool:
    return (_v(node, path) or "").lower() in ("1", "true")


def _num(s: str | None) -> float | None:
    try:
        return float(s) if s not in (None, "") else None
    except ValueError:
        return None


def parse_form4(text: str, accession: str, filed: str) -> tuple[dict, list[dict]]:
    """(issuer, trades) from a Form 4 submission. `text` is the full submission (.txt) or just the
    ownershipDocument XML. Returns ({}, []) when there is no parseable ownershipDocument."""
    m = re.search(r"<ownershipDocument>.*?</ownershipDocument>", text, re.S)
    if not m:
        return {}, []
    try:
        root = ET.fromstring(m.group(0))
    except ET.ParseError:
        return {}, []
    iss = root.find("issuer")
    try:
        cik = int(_v(iss, "issuerCik") or "")
    except ValueError:
        return {}, []
    issuer = {"cik": cik, "name": _v(iss, "issuerName"),
              "ticker": ((_v(iss, "issuerTradingSymbol") or "").upper() or None)}
    owners, roles, titles = [], [], []
    for ro in root.findall("reportingOwner"):
        owners.append((_v(ro, "reportingOwnerId/rptOwnerName"), _v(ro, "reportingOwnerId/rptOwnerCik")))
        rel = ro.find("reportingOwnerRelationship")
        r = [name for tag, name in (("isDirector", "director"), ("isOfficer", "officer"),
                                    ("isTenPercentOwner", "ten_percent_owner"), ("isOther", "other")) if _flag(rel, tag)]
        roles.append(r)
        titles.append(_v(rel, "officerTitle"))
    owner = "; ".join(o[0] for o in owners if o[0]) or None
    owner_cik = ";".join(str(int(o[1])) for o in owners if o[1] and o[1].isdigit()) or None
    all_roles = sorted({x for r in roles for x in r})
    title = "; ".join(t for t in titles if t) or None
    trades = []
    for n, tr in enumerate(root.findall("nonDerivativeTable/nonDerivativeTransaction")):
        code = _v(tr, "transactionCoding/transactionCode")
        if code not in KEEP_CODES:
            continue
        shares = _num(_v(tr, "transactionAmounts/transactionShares"))
        price = _num(_v(tr, "transactionAmounts/transactionPricePerShare"))
        trades.append({
            "accession": accession, "row": n, "filed": filed,
            "date": _v(tr, "transactionDate"), "code": code,
            "shares": shares, "price": price,
            "value": round(shares * price, 2) if shares is not None and price is not None else None,
            "owned_after": _num(_v(tr, "postTransactionAmounts/sharesOwnedFollowingTransaction")),
            "direct": _v(tr, "ownershipNature/directOrIndirectOwnership"),
            "security": _v(tr, "securityTitle"),
            "owner": owner, "owner_cik": owner_cik, "roles": all_roles, "title": title,
        })
    return issuer, trades


def merge_trades(existing: list[dict], new: list[dict]) -> list[dict]:
    """Union by (accession, row), newest filing first. A re-read filing replaces its old rows."""
    by = {(t["accession"], t["row"]): t for t in existing}
    for t in new:
        by[(t["accession"], t["row"])] = t
    return sorted(by.values(), key=lambda t: (t.get("filed") or "", t.get("date") or "", t["accession"], t["row"]), reverse=True)


def clusters(rows: list[dict], today: date, days: int = CLUSTER_DAYS) -> list[dict]:
    """Companies where two or more distinct directors/officers made open-market PURCHASES filed in
    the last `days` days — the pattern the insider-trading literature finds most informative.
    Pure ten-percent owners (often funds) are not counted as insiders here."""
    cut = (today - timedelta(days=days)).isoformat()
    agg: dict[int, dict] = {}
    for r in rows:
        if r["code"] != "P" or (r.get("filed") or "") < cut:
            continue
        if not ({"director", "officer"} & set(r.get("roles") or [])):
            continue
        a = agg.setdefault(r["cik"], {"cik": r["cik"], "ticker": r.get("ticker"), "name": r.get("name"),
                                       "buyers": set(), "value": 0.0, "last_filed": ""})
        a["buyers"].add(r.get("owner_cik") or r.get("owner"))
        a["value"] += r.get("value") or 0.0
        a["last_filed"] = max(a["last_filed"], r.get("filed") or "")
    out = [{**a, "buyers": len(a["buyers"]), "value": round(a["value"], 2)} for a in agg.values() if len(a["buyers"]) >= 2]
    return sorted(out, key=lambda a: (a["buyers"], a["value"]), reverse=True)


def main() -> int:
    t0 = time.time()
    OUT_DIR.mkdir(exist_ok=True); INS_DIR.mkdir(exist_ok=True)
    try:
        seen: dict[str, str] = json.loads(SEEN_PATH.read_text()).get("accessions", {})
    except Exception:  # noqa: BLE001
        seen = {}
    days = index_days(LOOKBACK_DAYS)
    print(f"1. daily indexes for {[d.isoformat() for d in days]}")
    todo: dict[str, tuple[str, str]] = {}
    for d in days:
        q = (d.month - 1) // 3 + 1
        r = get(DAILY_INDEX.format(year=d.year, q=q, ymd=d.strftime("%Y%m%d")))
        if r is None:
            continue
        got = form4_paths(r.text)
        print(f"  {d}: {len(got)} Form 4s")
        for acc, path in got.items():
            if acc not in seen:
                todo[acc] = (path, d.isoformat())
    print(f"  {len(todo)} not yet read" + (f"; reading the first {MAX_FILINGS}" if len(todo) > MAX_FILINGS else ""))

    print("2. filings")
    by_issuer: dict[int, tuple[dict, list[dict]]] = {}
    read = kept = 0
    for acc, (path, filed) in sorted(todo.items(), key=lambda kv: kv[1][1], reverse=True)[:MAX_FILINGS]:
        r = get(ARCHIVES + path)
        if r is None:
            continue                                  # unreadable: not marked seen, retried next run
        issuer, trades = parse_form4(r.text, acc, filed)
        seen[acc] = filed; read += 1
        if issuer and trades:
            meta, lst = by_issuer.setdefault(issuer["cik"], (issuer, []))
            lst += trades; kept += len(trades)
            if issuer.get("ticker"):
                meta["ticker"] = issuer["ticker"]
        if read % 500 == 0:
            print(f"  {read} read, {kept} P/S trades", flush=True)
    print(f"  {read} filings read, {kept} P/S trades across {len(by_issuer)} companies")

    changed = 0
    for cik, (issuer, trades) in by_issuer.items():
        p = INS_DIR / f"{cik}.json"
        rec = {"cik": cik, "name": issuer.get("name"), "ticker": issuer.get("ticker"), "trades": []}
        if p.exists():
            try:
                old = json.loads(p.read_text())
                rec = {**old, **{k: v for k, v in rec.items() if v and k != "trades"}, "trades": old.get("trades", [])}
            except Exception:  # noqa: BLE001
                pass
        rec["trades"] = merge_trades(rec["trades"], trades)
        body = json.dumps(rec, separators=(",", ":"), sort_keys=True)
        if not p.exists() or p.read_text() != body:
            p.write_text(body); changed += 1
    print(f"  {changed} company files changed")

    cut_seen = (date.today() - timedelta(days=SEEN_DAYS)).isoformat()
    seen = {a: d for a, d in seen.items() if d >= cut_seen}
    SEEN_PATH.write_text(json.dumps({"accessions": seen}, separators=(",", ":"), sort_keys=True))

    print("3. recent index")
    cutoff = (date.today() - timedelta(days=RECENT_DAYS)).isoformat()
    recent = []
    for p in INS_DIR.glob("*.json"):
        try:
            rec = json.loads(p.read_text())
        except Exception:  # noqa: BLE001
            continue
        for t in rec.get("trades", []):
            if (t.get("filed") or "") >= cutoff:
                recent.append({**t, "cik": rec["cik"], "ticker": rec.get("ticker"), "name": rec.get("name")})
    recent.sort(key=lambda t: (t.get("filed") or "", t["cik"], t["accession"], t["row"]), reverse=True)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (OUT_DIR / "insiders_recent.json").write_text(json.dumps({"generated_utc": generated, "days": RECENT_DAYS, "rows": recent}, separators=(",", ":")))

    cl = clusters(recent, date.today())
    n_by = defaultdict(int)
    for t in recent:
        n_by[t["code"]] += 1
    report = [f"# SEC insiders build — {generated}", "",
              f"- Form 4s read this run: {read}; P/S trades kept: {kept}",
              f"- trades filed in the last {RECENT_DAYS} days: purchases {n_by['P']}, sales {n_by['S']}", "",
              f"## Clusters: 2+ directors/officers buying in the last {CLUSTER_DAYS} days ({len(cl)})", "",
              "| ticker | company | buyers | $ bought | last filed |", "|---|---|---|---|---|"]
    report += [f"| {c['ticker'] or ''} | {c['name'] or ''} | {c['buyers']} | {c['value']:,.0f} | {c['last_filed']} |" for c in cl[:50]]
    (OUT_DIR / "insiders_report.md").write_text("\n".join(report) + "\n")
    print(f"done in {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
