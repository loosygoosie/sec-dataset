#!/usr/bin/env python3
"""Which XBRL tags can this builder actually SEE for a company, and which are unreachable.

WHY THIS EXISTS. A field comes back empty for a company that plainly reports the figure, and there
are two very different reasons for it, which look identical from the outside:

  1. THE COMPANY USES A TAG THIS BUILDER DOES NOT LIST. A tag addition fixes it.
  2. THE COMPANY TAGS THE FIGURE ONLY WITH A DIMENSION — by award type, share class, segment,
     regulatory entity. **companyfacts carries no dimensioned facts**, so the figure is not
     missing from our list, it is unreachable from this source at all, and no tag addition
     recovers it. Visa's share counts are the standing example (NOTES, "Multi-class filer").

Guessing between them is how a tag list grows tags that resolve nothing. This reads the SAME source
the builder reads and prints every tag matching a pattern that carries UNDIMENSIONED facts — so an
empty result IS the evidence for case 2, and a hit is the tag to add.

It also prints what the last build resolved, from `data/companies/<cik>.json`'s `tags_used`. Those
two answers should agree. **If the probe finds facts under a tag the builder already lists and the
build resolved nothing, that is a builder bug** — CLAUDE.md says stop and report it.

Reads companyfacts per company from data.sec.gov, which is the same payload the bulk zip carries
for that company. It needs SEC_USER_AGENT, so it belongs in CI (`.github/workflows/probe-tags.yml`)
and not in a sandbox — see CLAUDE.md. **It never writes to `data/`, and never prints the
user-agent.**

    python probe_tags.py --pattern ShareBased --field stock_comp --tickers XOM,VZ,MO
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import build_sec_dataset as B

COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
SP500_PATH = Path("data/sp500.json")
COMPANIES_DIR = Path("data/companies")


def matching_tags(facts: dict, pattern: re.Pattern) -> list[dict]:
    """Every us-gaap tag whose name matches, with what companyfacts actually carries for it.

    Only tags with at least one fact survive: a tag present with an empty unit list is as absent as
    one that is not there, and reporting it would read as a tag worth adding."""
    out = []
    for tag, node in (facts.get("facts", {}).get("us-gaap") or {}).items():
        if not pattern.search(tag):
            continue
        for unit, rows in (node.get("units") or {}).items():
            if not rows:
                continue
            fys = sorted({r.get("fy") for r in rows if r.get("fy") is not None})
            latest = max(rows, key=lambda r: (r.get("end") or "", r.get("filed") or ""))
            out.append({"tag": tag, "unit": unit, "facts": len(rows),
                        "fy_first": fys[0] if fys else None, "fy_last": fys[-1] if fys else None,
                        "latest_end": latest.get("end"), "latest_val": latest.get("val")})
    return sorted(out, key=lambda r: (-r["facts"], r["tag"]))


def listed_for(field: str | None) -> list[str]:
    """The tags the builder already tries for a field, so the output says what is NEW."""
    if not field:
        return []
    spec = B.CONCEPTS.get(field)
    if spec is None:
        raise SystemExit(f"no such field: {field}. See CONCEPTS in build_sec_dataset.py")
    return list(spec.get("tags") or [])


def resolved_for(cik: int, field: str | None) -> str | None | bool:
    """What the last build recorded under `tags_used` — False where no file was published."""
    if not field:
        return None
    p = COMPANIES_DIR / f"{cik}.json"
    if not p.is_file():
        return False
    return (json.loads(p.read_text()).get("tags_used") or {}).get(field)


def ticker_map() -> dict[str, int]:
    sp = json.loads(SP500_PATH.read_text())
    return {c["ticker"]: c["cik"] for c in sp.get("companies", [])}


def line(h: dict, mark: str) -> str:
    """One tag's row. The value is formatted only when it IS a number — companyfacts carries
    strings under some units, and a format crash in a diagnostic reads as a missing tag."""
    v = h["latest_val"]
    val = f"{v:,}" if isinstance(v, (int, float)) else str(v)
    return (f"{h['tag']:<66s} {h['unit']:<10s} {h['facts']:>4d} facts  "
            f"FY{h['fy_first']}-{h['fy_last']}  latest {h['latest_end']} {val}  [{mark}]")


def probe(tickers: list[str], pattern: re.Pattern, field: str | None) -> int:
    """Print one block per company. Returns the number of BUILDER BUGS found, which is the exit
    code: a tag listed, carrying facts, and resolved to nothing is not a reporting matter."""
    ciks, bugs = ticker_map(), 0
    listed = listed_for(field)
    if field:
        print(f"field {field!r} currently lists: {', '.join(listed)}\n")
    for tk in tickers:
        cik = ciks.get(tk)
        if cik is None:
            print(f"{tk}: not in data/sp500.json — skipped\n")
            continue
        facts = B.get(COMPANYFACTS_URL.format(cik=cik)).json()
        hits = matching_tags(facts, pattern)
        used = resolved_for(cik, field)
        print(f"{tk}  CIK {cik}")
        if field:
            where = ("no company file published" if used is False else
                     f"build resolved: {used}" if used else "build resolved: NOTHING")
            print(f"  {where}")
        if not hits:
            print(f"  no undimensioned tag matches /{pattern.pattern}/ — the figure is either not"
                  f" reported or tagged only with a dimension, which companyfacts drops.")
        for h in hits:
            mark = "listed" if h["tag"] in listed else "NOT LISTED"
            print("  " + line(h, mark))
            if mark == "listed" and not used:
                bugs += 1
                print("      ^^ BUILDER BUG: this tag is listed and carries facts, and the build"
                      " resolved nothing for this field. Stop and report it (CLAUDE.md).")
        print()
    return bugs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pattern", required=True, help="regex matched against us-gaap tag names")
    ap.add_argument("--tickers", required=True, help="comma-separated, e.g. XOM,VZ,MO")
    ap.add_argument("--field", help="a CONCEPTS field, to mark which hits are already listed")
    a = ap.parse_args()
    tickers = [t.strip().upper() for t in a.tickers.split(",") if t.strip()]
    if not tickers:
        raise SystemExit("--tickers matched nothing")
    bugs = probe(tickers, re.compile(a.pattern, re.I), a.field)
    if bugs:
        print(f"{bugs} builder bug(s) found — see above.")
    return 1 if bugs else 0


if __name__ == "__main__":
    raise SystemExit(main())
