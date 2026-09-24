#!/usr/bin/env python3
"""Daily PATCH-ONLY refresh of data/companies/<CIK>.json — only for companies that filed.

WHY THIS EXISTS. `sec.yml` rebuilds every company file once a week, and a reader that values
companies every day could wait up to seven days for a 10-Q or 10-K the events feed already knows
about. Running the full build daily was rejected: it rewrites ~13,700 files every time
(`quarter_age_days` moves daily) and that churn would land in never-pruned history seven times a
week (NOTES §20, §21).

WHAT IT DOES. It reads the nightly events feed (`data/events/<CIK>.json`) against each company file
and picks a company only when a 10-Q or 10-K (amendments included) is newer than what the file
holds — see `select_targets`. For each pick it fetches that ONE company's companyfacts from
data.sec.gov (the same payload the bulk zip carries for it) and runs the weekly build's own code on
it: `normalise_company`, `company_record`, then — if companyfacts is still behind the filing — the
same filing-instance fallback (`newer_filings` + `patch_company`). So a company it rewrites comes
out exactly as `sec.yml` would write it that day.

WHAT IT NEVER DOES. Touch a company it did not pick; delete anything (a company the weekly build
would drop is LEFT AS IS — pruning belongs to the weekly build alone); add a filer that has no file
yet (the weekly build does that); rewrite a file whose only difference is `quarter_age_days`, which
moves every day by itself; write the manifest when no company changed. Re-running it is a no-op.

It needs SEC_USER_AGENT and belongs in CI (`.github/workflows/companies-patch.yml`), not a sandbox —
see CLAUDE.md. `--select-only` makes no requests at all and prints what would be fetched.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, timedelta

import build_sec_dataset as B

COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
MAX_COMPANIES = 1000           # companies per run; each is one companyfacts request (+2 per filing read)
# and never more than this much wall-clock on them. 120 of the job's 180 minutes (cut from 150,
# 24 Sep 2026): the limit is checked only BETWEEN companies, and the commit comes after the loop, so
# one slow company near the end must not run the job into its timeout and lose the whole day's work.
RUN_SECONDS = 120 * 60
# Filing instances read per run (the weekly build's PATCH_CAP is 600). Raised 24 Sep 2026 with the two
# limits above so a heavy earnings night finishes: the job starts 07:00 UTC and readers look ~18:30 UTC.
PATCH_INSTANCES = 2000
# A 10-Q/10-K filed after everything the file holds but for a period it already holds — in
# practice an amendment — is looked at for this many days, then left to the weekly build. Without
# the window a 10-K/A carrying only Part III (no financial statements, and very common) would be
# refetched every day for the 400 days the events feed keeps it.
RECENT_FILED_DAYS = 14
FORMS = ("10-Q", "10-K")       # startswith: 10-Q/A and 10-K/A are included, NT 10-K is not


def _latest(rows: list[dict], key: str) -> str | None:
    vals = [r.get(key) for r in rows if r.get(key)]
    return max(vals) if vals else None


def why_behind(rec: dict, evs: list[dict], today: date) -> list[str]:
    """The reasons this company file is behind its own filings; empty when it is not.

    - `quarter`: a 10-Q/10-K for a period at least PATCH_MIN_GAP_DAYS past the newest quarter
      held — the weekly build's own patch rule (`newer_filings`), unchanged.
    - `annual`: a 10-K for a fiscal year at least PATCH_MIN_GAP_DAYS past the newest annual row,
      whose closing quarter the file holds ONLY from the filing fallback (`source: filing`). The
      fallback adds quarters, never annual rows, so such a company (Clorox, 23 Sep 2026: FY to
      2026-06-30 filed 7 Aug, Q4 read from the 10-K, newest annual row FY2025) lacks the year
      until companyfacts catches up, and this keeps it picked until then. A missing annual row
      with the quarter from companyfacts is NOT picked: companyfacts already holds that 10-K and
      publishes no full year from it (a post-merger stub year — Paramount Skydance — or a filer
      whose facts carry no FY label), so fetching it again every day would change nothing.
    - `filed`: a 10-Q/10-K (/A) filed after the newest filing any row holds, within
      RECENT_FILED_DAYS — an amendment restating a period already held."""
    why = []
    lq = (rec.get("checks") or {}).get("latest_quarter_end")
    if lq and B.newer_filings(evs, lq):
        why.append("quarter")
    la = _latest(rec.get("annual") or [], "period_end")
    from_filing = [q["period_end"] for q in rec.get("quarterly") or []
                   if q.get("source") == "filing" and q.get("period_end")]
    if la and any(str(e.get("form", "")).startswith("10-K") and e.get("period") and e.get("accession")
                  and B._later_quarter(e["period"], la)
                  and any(abs(B._days(q, e["period"])) < B.PATCH_MIN_GAP_DAYS for q in from_filing)
                  for e in evs):
        why.append("annual")
    held = _latest((rec.get("annual") or []) + (rec.get("quarterly") or []), "filed") or ""
    since = (today - timedelta(days=RECENT_FILED_DAYS)).isoformat()
    if any(str(e.get("form", "")).startswith(FORMS) and e.get("accession")
           and (e.get("date") or "") > held and (e.get("date") or "") >= since for e in evs):
        why.append("filed")
    return why


def select_targets(today: date, only: set[int] | None = None) -> list[dict]:
    """Every company with a file AND an events record showing a filing newer than the file.

    Ordered companies with a ticker first, then the LEAST behind first (the newest quarter held,
    latest first), then CIK. (An S&P 500 tier came first until 24 Sep 2026, when the S&P list was
    dropped; `fmp`, the only reader, buys any listed company.) That is NOT the weekly build's order (most stale first),
    on purpose: the first live dry run (23 Sep 2026) spent its then 25-minute limit on shells whose
    companyfacts stopped in 2012-2016 and never reached 34 listed companies a quarter behind. Order
    decides only WHO is reached in a capped run, never what is written for them."""
    comp_dir = B.OUT_DIR / "companies"
    out = []
    for p in sorted(B.EVENTS_DIR.glob("*.json")):
        if not p.stem.isdigit():
            continue
        cik = int(p.stem)
        if only is not None and cik not in only:
            continue
        cp = comp_dir / f"{cik}.json"
        if not cp.is_file():
            continue                                   # a new filer: the weekly build adds it
        try:
            evs = json.loads(p.read_text()).get("events", [])
            rec = json.loads(cp.read_text())
        except Exception:  # noqa: BLE001
            continue
        why = why_behind(rec, evs, today)
        if why:
            out.append({"cik": cik, "why": why, "events": evs,
                        "lq": (rec.get("checks") or {}).get("latest_quarter_end") or "",
                        "name": rec.get("sec_name"), "tickers": rec.get("tickers") or []})
    out.sort(key=lambda t: t["cik"])
    out.sort(key=lambda t: t["lq"], reverse=True)
    out.sort(key=lambda t: not t["tickers"])
    return out


def fetch_companyfacts(cik: int) -> dict:
    return B.get(COMPANYFACTS_URL.format(cik=cik), retries=2, timeout=180).json()


def _material(obj: dict) -> str:
    """A company file or manifest entry with the one field that moves by itself every day removed."""
    o = json.loads(json.dumps(obj))
    o.pop("quarter_age_days", None)
    if isinstance(o.get("checks"), dict):
        o["checks"].pop("quarter_age_days", None)
    return B.record_body(o)


def regressed(old: dict, new: dict) -> str | None:
    """Why a rebuilt record looks like a short read rather than news, or None. A daily run has no
    3,000-company floor to catch a truncated response, so one company's history must not shrink:
    the newest annual row and newest quarter never move backwards and annual rows never vanish.
    The weekly build stays the authority for anything this holds back."""
    for key, label in (("annual", "newest annual period"), ("quarterly", "newest quarter")):
        o, n = _latest(old.get(key) or [], "period_end"), _latest(new.get(key) or [], "period_end")
        if o and (not n or n < o):
            return f"{label} would go from {o} to {n}"
    if len(new.get("annual") or []) < len(old.get("annual") or []):
        return f"annual rows would fall from {len(old['annual'])} to {len(new['annual'])}"
    return None


def rebuild(cik: int, old: dict, evs: list[dict], today: date, sics: dict, sic_codes: dict,
            budget: int) -> tuple[dict | None, dict | None, int, str]:
    """(record, manifest entry, budget left, what happened) for one picked company, by the weekly
    build's own steps 3 and 5. Tickers are carried from the file: they come from the SEC ticker
    map, which only the weekly build fetches, so every file and the manifest stay on one map."""
    facts = fetch_companyfacts(cik)
    if not isinstance(facts, dict) or not facts.get("facts", {}).get("us-gaap"):
        return None, None, budget, "held: companyfacts carries no us-gaap facts"
    norm = B.normalise_company(facts)
    built = B.company_record(facts, norm, cik, {cik: old.get("tickers") or []}, today, sics, sic_codes)
    if built is None:
        return None, None, budget, "held: the weekly build would drop it, and this run never prunes"
    rec, entry = built
    rec = json.loads(B.record_body(rec))           # what the weekly build's patch step reads back from disk
    how = "companyfacts"
    lq = rec["checks"]["latest_quarter_end"]
    filings = B.patch_window(B.newer_filings(evs, lq)) if lq else []
    if filings and budget > 0:
        ok, budget = B.patch_company(cik, rec, facts, filings, budget)
        if ok:
            entry.update(B.patched_manifest_fields(rec))
            how = "companyfacts+filing"
    return rec, entry, budget, how


def run(today: date | None = None, max_companies: int = MAX_COMPANIES, only: set[int] | None = None,
        select_only: bool = False) -> dict:
    today = today or date.today()
    comp_dir = B.OUT_DIR / "companies"
    targets = select_targets(today, only)
    summary = {"date": today.isoformat(), "behind": len(targets), "picked": min(len(targets), max_companies),
               "changed": [], "unchanged": [], "held": [], "failed": [], "not_reached": [],
               "targets": [{"cik": t["cik"], "tickers": t["tickers"], "name": t["name"], "why": t["why"]}
                           for t in targets]}
    if select_only:
        return summary

    manifest_path = B.OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    sics, sic_codes = B.load_sics()
    budget, t0 = PATCH_INSTANCES, time.time()
    for i, t in enumerate(targets):
        cik = t["cik"]
        if i >= max_companies or time.time() - t0 > RUN_SECONDS:
            summary["not_reached"].append(cik)
            continue
        path = comp_dir / f"{cik}.json"
        old_body = path.read_text()
        old = json.loads(old_body)
        try:
            rec, entry, budget, how = rebuild(cik, old, t["events"], today, sics, sic_codes, budget)
        except Exception as ex:  # noqa: BLE001
            summary["failed"].append({"cik": cik, "error": f"{type(ex).__name__}: {ex}"[:200]})
            continue
        print(f"  [{i + 1}/{len(targets)} {time.time() - t0:5.0f}s] {cik} {','.join(t['tickers']) or '-'}: {how}",
              flush=True)
        if rec is None:
            summary["held"].append({"cik": cik, "why": how})
            continue
        bad = regressed(old, rec)
        if bad:
            summary["held"].append({"cik": cik, "why": f"held: {bad}"})
            continue
        if _material(rec) == _material(old):
            summary["unchanged"].append(cik)
            continue
        path.write_text(B.record_body(rec))
        manifest["companies"][str(cik)] = entry
        summary["changed"].append({"cik": cik, "tickers": rec["tickers"], "via": how, "why": t["why"],
                                   "quarter": [(old.get("checks") or {}).get("latest_quarter_end"),
                                               rec["checks"]["latest_quarter_end"]],
                                   "annual": [_latest(old.get("annual") or [], "period_end"),
                                              _latest(rec["annual"], "period_end")]})
    if summary["changed"]:
        manifest_path.write_text(json.dumps(manifest, separators=(",", ":"), sort_keys=True))
    summary["filings_fetched"] = PATCH_INSTANCES - budget
    return summary


def report(s: dict, select_only: bool) -> str:
    def tk(t):
        return ",".join(t.get("tickers") or []) or "-"
    lines = [f"# Daily companies patch — {s['date']}", "",
             f"- companies behind their own 10-Q/10-K: {s['behind']}"]
    if select_only:
        lines += ["- select-only: no requests made", "", "| cik | tickers | name | why |", "|---|---|---|---|"]
        lines += [f"| {t['cik']} | {tk(t)} | {t['name']} | {'+'.join(t['why'])} |" for t in s["targets"]]
        return "\n".join(lines) + "\n"
    lines += [f"- rewritten: {len(s['changed'])}", f"- rebuilt, nothing new (companyfacts still behind): {len(s['unchanged'])}",
              f"- held back: {len(s['held'])}", f"- failed: {len(s['failed'])}",
              f"- not reached (cap or time): {len(s['not_reached'])}",
              f"- filing instances fetched: {s.get('filings_fetched', 0)}", ""]
    if s["changed"]:
        lines += ["| cik | tickers | via | why | newest quarter | newest annual |", "|---|---|---|---|---|---|"]
        lines += [f"| {c['cik']} | {tk(c)} | {c['via']} | {'+'.join(c['why'])} | "
                  f"{c['quarter'][0]} → {c['quarter'][1]} | {c['annual'][0]} → {c['annual'][1]} |" for c in s["changed"]]
    for h in s["held"]:
        lines.append(f"- held {h['cik']}: {h['why']}")
    for f in s["failed"]:
        lines.append(f"- failed {f['cik']}: {f['error']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--select-only", action="store_true", help="print the picks; make no requests, write nothing")
    ap.add_argument("--max-companies", type=int, default=int(os.environ.get("MAX_COMPANIES") or MAX_COMPANIES))
    ap.add_argument("--ciks", default=os.environ.get("ONLY_CIKS", ""), help="comma-separated CIKs to limit the run to")
    a = ap.parse_args(argv)
    only = {int(c) for c in a.ciks.replace(" ", "").split(",") if c} or None
    s = run(max_companies=a.max_companies, only=only, select_only=a.select_only)
    text = report(s, a.select_only)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as fh:
            fh.write(text)
    attempted = len(s["failed"]) + len(s["changed"]) + len(s["unchanged"]) + len(s["held"])
    if not a.select_only and s["failed"] and len(s["failed"]) == attempted:
        print("every company attempted failed — SEC unreachable or the user agent refused")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
