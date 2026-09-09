#!/usr/bin/env python3
"""
build_sec_filings.py — the narrative half of the dataset: what each company says it does.

build_sec_dataset.py gives us the numbers and build_sec_events.py the filing calendar. Neither
carries a word of prose, and the business briefs the monitors read are prose: what a company
sells and to whom, the two or three dependencies that could actually break, and the line in a
filing that would show one breaking. Until this existed those briefs had to be written from a
vendor's copy of the filing text, and on 9 Sep 2026 that route turned out to be unusable — the
vendor's index listed every 10-K but its reader returned "content is not available" for DECK,
DUK, AEP, FCX and VMC, and for their prior-year filings too. A brief is only worth reading if it
came from the company's own words, so those words belong in our own data.

Scope is the S&P 500 (data/sp500.json), which is the universe every task screens from. Storing
the narrative for 7,411 filers would be several gigabytes of text nobody reads.

Outputs (committed to data/):
    filings/<CIK>.json.gz  — {cik, name, tickers, form, accession, filed, period, url,
                              sections: {item1, item1a, item3, item7, item7a}, chars, truncated}
                             gzip because the plain text of one 10-K's narrative items runs to a
                             few hundred kilobytes and 500 of them would double the repo.
    filings_report.md      — coverage: companies stored, and how many carry each section.

A 10-K never changes once filed, so a company whose stored accession is still the latest 10-K is
skipped without a single request. The first run pays for everything; later runs pay only for the
companies that have filed since, which outside February is nearly none.

Rate limits: the SEC asks for <= 10 requests/second and a descriptive User-Agent (SEC_USER_AGENT).
"""
from __future__ import annotations

import gzip
import html as html_mod
import io
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

USER_AGENT = os.environ.get("SEC_USER_AGENT", "sec-dataset research (set SEC_USER_AGENT)")
HEADERS = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
ARCHIVE_DOC = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{doc}"

OUT_DIR = Path("data")
FIL_DIR = OUT_DIR / "filings"
EV_DIR = OUT_DIR / "events"
SP500_PATH = OUT_DIR / "sp500.json"

# Fetches per run. The S&P 500 fits in one run; the cap exists so a bad day at EDGAR costs a
# partial run rather than a six-hour one, and the rest resolves on the next run.
FETCH_CAP = int(os.environ.get("FILINGS_LIMIT", "600"))
# Restrict a run to named tickers, comma-separated. For proving a change on five companies
# instead of five hundred — the parser can only be tested against real filings on the runner,
# because the SEC refuses requests that do not carry the declared contact in SEC_USER_AGENT.
ONLY = {t.strip().upper() for t in os.environ.get("FILINGS_TICKERS", "").split(",") if t.strip()}
# Re-fetch and re-parse filings already stored. The stored text is only as good as the parser
# that made it, so every change to the extractor leaves the data behind — and the alternative,
# deleting files out of data/ by hand, is the one thing nobody may do here.
REFRESH = os.environ.get("FILINGS_REFRESH", "").strip().lower() in {"1", "true", "yes"}
# Dump the heading table for every company in scope, to the workflow log, and write nothing.
# The only way to see what a real filing looks like to the parser: it cannot be fetched anywhere
# but the runner. Use it with FILINGS_TICKERS or it prints five hundred tables.
DEBUG = os.environ.get("FILINGS_DEBUG", "").strip().lower() in {"1", "true", "yes"}

# Each stored section is capped. Item 1A alone runs past 200,000 characters at some banks, and
# nothing downstream reads that far — a brief needs the dependencies, which are stated up front.
SECTION_CAP = 80_000
# Below this a "section" is a false heading — a cross-reference or a table-of-contents remnant —
# not the real thing. Item 3 and Item 7A are exempt: "None." is a legitimate Item 3.
MIN_SECTION = {"item1": 1_000, "item1a": 1_000, "item7": 1_000, "item3": 0, "item7a": 0}
# Refuse to publish a run that parsed this badly: the filings did not change overnight, so a
# collapse in coverage is our parser breaking, and a broken parser must not overwrite good text.
MIN_COVERAGE = 0.60
MIN_ATTEMPTS_FOR_GUARD = 20

_last = [0.0]


def get(url: str, retries: int = 4, timeout: int = 120) -> requests.Response | None:
    """One SEC request, under the rate limit. None on a 404 or after the retries are spent."""
    for i in range(retries):
        gap = time.time() - _last[0]
        if gap < 0.12:                        # ~8 requests/second, under the SEC's 10/s
            time.sleep(0.12 - gap)
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
        except requests.RequestException:
            time.sleep(2 * (i + 1))
            continue
        _last[0] = time.time()
        if r.status_code == 200:
            return r
        if r.status_code == 404:
            return None
        time.sleep(2 * (i + 1))
    return None


# ---------------------------------------------------------------- HTML to text

_SCRIPT = re.compile(r"(?is)<(script|style)\b.*?</\1\s*>")
_BLOCK = re.compile(r"(?i)</(p|div|tr|h[1-6]|li|table|td)\s*>|<br\s*/?>")
_TAG = re.compile(r"<[^>]+>")
_INLINE_WS = re.compile(r"[^\S\n]+")
_BLANKS = re.compile(r"\n{3,}")


def to_text(html: str) -> str:
    """A filing's HTML as plain text, with one line per block element.

    Tags become a space rather than nothing: modern 10-Ks are inline XBRL and split words across
    spans, and joining them bare turns "Item 1A" into "Item1A", which no heading pattern matches.
    The spurious spaces that costs are collapsed on the next line."""
    t = _SCRIPT.sub(" ", html)
    t = _BLOCK.sub("\n", t)
    t = _TAG.sub(" ", t)
    t = html_mod.unescape(t)
    t = t.replace("\xa0", " ").replace("’", "'").replace("“", '"').replace("”", '"')
    t = _INLINE_WS.sub(" ", t)
    t = "\n".join(line.strip() for line in t.split("\n"))
    return _BLANKS.sub("\n\n", t).strip()


# ---------------------------------------------------------------- item headings

# The order the items appear in, which is what tells us where a section ends: it runs to the
# next heading of any later item, whichever comes first.
ITEM_ORDER = ["1", "1a", "1b", "1c", "2", "3", "4", "5", "6", "7", "7a", "8",
              "9", "9a", "9b", "10", "11", "12", "13", "14", "15", "16"]
ITEM_INDEX = {k: i for i, k in enumerate(ITEM_ORDER)}

# The words the SEC's own form prescribes for each item. A heading has to carry them, which is
# what separates "Item 1A. Risk Factors" at the top of a page from "as described in Item 1A"
# in the middle of a sentence.
ITEM_TITLES = {
    "1": ("business",), "1a": ("risk factor",), "1b": ("unresolved staff",), "1c": ("cybersecurity",),
    "2": ("properties",), "3": ("legal proceeding",), "4": ("mine safety",),
    "5": ("market for", "registrant's common"), "6": ("reserved", "selected financial"),
    "7": ("management's discussion", "managements discussion"),
    "7a": ("quantitative and qualitative",), "8": ("financial statements",),
    "9": ("changes in and disagreements",), "9a": ("controls and procedures",),
    "9b": ("other information",), "10": ("directors",), "11": ("executive compensation",),
    "12": ("security ownership",), "13": ("certain relationships",),
    "14": ("principal account",), "15": ("exhibit",), "16": ("form 10-k summary",),
}

WANTED = ["item1", "item1a", "item3", "item7", "item7a"]
WANTED_KEY = {"item1": "1", "item1a": "1a", "item3": "3", "item7": "7", "item7a": "7a"}

# "Items 1. and 2. Business and Properties" is the standard heading in the extractive
# industries and in many REITs, and "Items 7. and 7A." is common wherever market risk is
# discussed inside MD&A. Requiring "item" to be followed straight away by a number missed both,
# which cost Freeport-McMoRan its entire Item 1 on the first real run. Only the first number is
# captured: the section starts there and runs to the next item either way.
_ITEM_RE = re.compile(
    r"(?im)^[^\S\n]{0,12}(?:part\s+[ivx]{1,4}\s*[\.\-–—:]?\s*)?"
    r"items?[\s\.]{0,3}([0-9]{1,2}[abc]?)[\s\.\-–—:\)]{0,4}(.{0,90})")


def _squash(s: str) -> str:
    """Letters and digits only, lowercased.

    Filings wrap the first letter of a heading in its own span for a drop cap, and stripping
    tags to a space then puts that space inside the word: Microsoft's Item 1 reads "B usiness"
    and Church & Dwight's Item 5 reads "mar ket for". Comparing squashed forms makes the split
    invisible, and it takes the apostrophe out of "Management's" at the same time."""
    return re.sub(r"[^a-z0-9]+", "", s.lower())


_SQUASHED_TITLES = {k: tuple(_squash(t) for t in v) for k, v in ITEM_TITLES.items()}


def _matches(text: str) -> list[tuple[int, str, str]]:
    """Every line that opens like an item heading, as (position, item key, rest of the line)."""
    out = []
    for m in _ITEM_RE.finditer(text):
        key = m.group(1).lower()
        if key in ITEM_INDEX:
            out.append((m.start(), key, _squash(m.group(2))))
    return out


def _contents(ms: list[tuple[int, str, str]], length: int) -> set[int]:
    """The indexes of matches that are rows of a table of contents rather than headings.

    A table of items is a run of mentions packed a few hundred characters apart whose item
    numbers only ever go up. Density alone would swallow the real Item 1 in the filings where
    the contents run straight into it with nothing between — but the table ends at Item 15 and
    the body restarts at Item 1, and that fall is where the run breaks.

    Two kinds of table exist and only one is at the front. General Electric's 10-K carries no
    item headings at all: it is an integrated report with a **cross-reference index at the back**
    mapping each item to a page, and on the first full run all 22 of its rows sat at 99% of the
    document and three of them were stored as if they were sections — "Item 3. Legal Proceedings
    70-71" is a page reference, not a disclosure. So a long run is a table wherever it sits.

    Any other run is a table only at the front, because the body has one of its own that looks
    the same: "Item 1B. Unresolved Staff Comments. None." followed by 1C, 2, 3, 4, 5 and 6 is
    six increasing items inside a page, and Item 7 can follow immediately. That one sits past
    the first quarter of the filing, because Item 1A stands in front of it and is the longest
    item in the form."""
    flagged: set[int] = set()
    i = 0
    while i < len(ms):
        j = i
        while (j + 1 < len(ms) and ms[j + 1][0] - ms[j][0] < 600
               and ITEM_INDEX[ms[j + 1][1]] > ITEM_INDEX[ms[j][1]]):
            j += 1
        keys = {m[1] for m in ms[i:j + 1]}
        # A run that reaches from Item 1 to Item 10 or beyond is a table of the whole form. No
        # body does that: Item 1 is never one line, so it can never sit inside a dense run.
        whole_form = bool(keys & {"1", "1a"}) and max(ITEM_INDEX[k] for k in keys) >= ITEM_INDEX["10"]
        if whole_form or (len(keys) >= 5 and ms[i][0] < 0.25 * length):
            flagged.update(range(i, j + 1))
        i = j + 1
    return flagged


def sections(text: str) -> dict[str, str]:
    """The narrative items of a 10-K, keyed item1 / item1a / item3 / item7 / item7a.

    Every filing names its items more than once — the table of contents, the heading over the
    section itself, and in many filers a running page header that repeats it on every page. The
    contents rows are identified and dropped by _contents. What separates the heading from the
    page headers is how far it reaches: the first one runs the whole section, each later one
    reaches less. So the candidate with the longest reach wins, and an exact tie goes to the
    earliest, which is the top of the section.

    Missing keys mean the heading was never found, which happens legitimately: a filing that
    incorporates Item 7 by reference to an exhibit has no Item 7 to extract. The caller reports
    those rather than inventing them."""
    ms = _matches(text)
    if not ms:
        return {}
    skip = _contents(ms, len(text))
    bounds = [(pos, ITEM_INDEX[key]) for pos, key, _ in ms]
    out: dict[str, str] = {}
    for name in WANTED:
        key = WANTED_KEY[name]
        idx, titles = ITEM_INDEX[key], _SQUASHED_TITLES[key]
        spans = []
        for n, (pos, k, title) in enumerate(ms):
            if n in skip or k != key or not any(t in title for t in titles):
                continue
            after = [q for q, i in bounds if q > pos and i > idx]
            # A candidate with no later item at all is usually the last page of an exhibit, not
            # a section; bounding it at the cap stops it out-reaching the real heading.
            end = min(after) if after else min(len(text), pos + SECTION_CAP)
            spans.append((pos, end))
        if not spans:
            continue
        s, e = max(spans, key=lambda sp: (sp[1] - sp[0], -sp[0]))
        seg = text[s:e].strip()
        if len(seg) >= MIN_SECTION[name]:
            out[name] = seg
    return out


# ---------------------------------------------------------------- which filing

def latest_10k_from_events(cik: int) -> dict | None:
    """The newest 10-K in this company's event record, which the events feed already fetched.

    Free — it is on disk. It only misses a company whose 10-K has aged past the feed's window,
    which the submissions fallback then covers."""
    p = EV_DIR / f"{cik}.json"
    if not p.exists():
        return None
    try:
        rec = json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return None
    tens = [e for e in rec.get("events", []) if e.get("form") == "10-K" and e.get("url")]
    if not tens:
        return None
    e = max(tens, key=lambda x: x["date"])
    return {"accession": e["accession"], "filed": e["date"], "period": e.get("period"),
            "url": e["url"], "form": "10-K"}


def latest_10k_from_submissions(cik: int) -> dict | None:
    """The newest 10-K in the SEC's submissions record. One request, used only as a fallback."""
    r = get(SUBMISSIONS.format(cik=cik))
    if r is None:
        return None
    try:
        recent = r.json().get("filings", {}).get("recent", {})
    except ValueError:
        return None
    forms = recent.get("form", [])
    best = None
    for i, form in enumerate(forms):
        if form != "10-K":
            continue
        filed = recent.get("filingDate", [None] * len(forms))[i]
        if best and filed <= best["filed"]:
            continue
        acc = recent.get("accessionNumber", [None] * len(forms))[i]
        doc = recent.get("primaryDocument", [None] * len(forms))[i]
        if not (acc and doc and filed):
            continue
        best = {"accession": acc, "filed": filed,
                "period": recent.get("reportDate", [None] * len(forms))[i],
                "url": ARCHIVE_DOC.format(cik=cik, acc_nodash=acc.replace("-", ""), doc=doc),
                "form": "10-K"}
    return best


def stored_accession(cik: int) -> str | None:
    p = FIL_DIR / f"{cik}.json.gz"
    if not p.exists():
        return None
    try:
        with gzip.open(p, "rt") as fh:
            return json.load(fh).get("accession")
    except Exception:  # noqa: BLE001
        return None


def gz_bytes(obj: dict) -> bytes:
    """Deterministic gzip: no mtime, so an unchanged filing produces identical bytes and git
    sees no change. The default stamps the current time into every file and would rewrite all
    five hundred of them on every run."""
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as fh:
        fh.write(json.dumps(obj, separators=(",", ":"), sort_keys=True).encode())
    return buf.getvalue()


def main() -> int:
    t0 = time.time()
    if not SP500_PATH.exists():
        raise SystemExit("REFUSING TO RUN — data/sp500.json is missing; run build_sec_dataset.py first")
    universe = json.loads(SP500_PATH.read_text()).get("companies", [])
    if ONLY:
        universe = [c for c in universe if c.get("ticker", "").upper() in ONLY]
        print(f"restricted to {len(universe)} companies: {', '.join(sorted(ONLY))}")
    if not universe:
        raise SystemExit("REFUSING TO RUN — no companies in scope")
    FIL_DIR.mkdir(parents=True, exist_ok=True)

    print(f"1. {len(universe)} companies in scope, cap {FETCH_CAP} fetches"
          + (" — REFRESH: re-parsing filings already stored" if REFRESH else ""))
    budget = FETCH_CAP
    results: dict[int, bytes] = {}
    skipped = attempted = no_filing = no_text = 0
    found: dict[str, int] = defaultdict(int)
    empty: list[str] = []
    short: list[str] = []
    for n, c in enumerate(universe, 1):
        cik, ticker = int(c["cik"]), c.get("ticker", "")
        filing = latest_10k_from_events(cik)
        if filing is None:
            if budget <= 0:
                continue
            budget -= 1
            filing = latest_10k_from_submissions(cik)
        if filing is None:
            no_filing += 1
            empty.append(f"{ticker} (no 10-K found)")
            continue
        if not REFRESH and stored_accession(cik) == filing["accession"]:
            skipped += 1
            continue
        if budget <= 0:
            continue
        budget -= 1
        attempted += 1
        url = filing["url"]
        if "/ix?doc=" in url:                 # inline-XBRL documents are linked through the viewer
            url = "https://www.sec.gov" + url.split("/ix?doc=", 1)[1]
        r = get(url)
        if r is None:
            no_text += 1
            empty.append(f"{ticker} (document unreadable)")
            continue
        text = to_text(r.text)
        if DEBUG:
            ms = _matches(text)
            skip = _contents(ms, len(text))
            print(f"\n=== {ticker} {url}")
            print(f"    raw {len(r.text)} chars, text {len(text)} chars, {len(ms)} item matches")
            for n, (pos, k, title) in enumerate(ms[:70]):
                mark = "TOC" if n in skip else "   "
                print(f"    {mark} {pos:8d} item{k:<3s} {title[:64]!r}")
            if len(ms) > 70:
                print(f"    ... {len(ms) - 70} more")
            print(f"    parsed: {sorted(sections(text))}")
            continue
        secs = sections(text)
        if not secs:
            no_text += 1
            empty.append(f"{ticker} (no item headings parsed)")
            continue
        truncated = [k for k, v in secs.items() if len(v) > SECTION_CAP]
        secs = {k: v[:SECTION_CAP] for k, v in secs.items()}
        for k in secs:
            found[k] += 1
        gap = [k for k in WANTED if k not in secs]
        if gap:
            short.append(f"{ticker}: {', '.join(gap)}")
        results[cik] = gz_bytes({
            "cik": cik, "name": c.get("name"), "tickers": [ticker] if ticker else [],
            "form": filing["form"], "accession": filing["accession"], "filed": filing["filed"],
            "period": filing.get("period"), "url": url,
            "sections": secs, "chars": {k: len(v) for k, v in secs.items()},
            "truncated": truncated,
        })
        if n % 25 == 0:
            print(f"  {n}/{len(universe)}  fetched {attempted}, cached {skipped}", flush=True)

    print(f"  {attempted} fetched, {skipped} already current, {no_filing} without a 10-K, "
          f"{no_text} unreadable, {budget} of {FETCH_CAP} fetches left")

    # The guard, before anything is written. A run that suddenly stops finding Item 1 is our
    # parser breaking against a filing format, not five hundred companies rewriting their 10-Ks.
    if attempted >= MIN_ATTEMPTS_FOR_GUARD:
        rate = found["item1"] / attempted
        if rate < MIN_COVERAGE:
            raise SystemExit(f"REFUSING TO WRITE — Item 1 parsed for only {found['item1']} of "
                             f"{attempted} filings ({rate:.0%}); the parser is broken")

    print("2. writing")
    changed = 0
    for cik, body in results.items():
        p = FIL_DIR / f"{cik}.json.gz"
        if not p.exists() or p.read_bytes() != body:
            p.write_bytes(body)
            changed += 1
    # Drop companies that have left the index: their text is no longer anything we screen.
    keep = {int(c["cik"]) for c in universe} if not ONLY else None
    pruned = 0
    if keep is not None:
        for p in FIL_DIR.glob("*.json.gz"):
            if int(p.name.split(".")[0]) not in keep:
                p.unlink()
                pruned += 1
    stored = len(list(FIL_DIR.glob("*.json.gz")))
    print(f"  {changed} written, {pruned} pruned, {stored} companies stored")

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report = [f"# SEC filing text build — {generated}", "",
              f"- companies in scope (S&P 500): {len(universe)}",
              f"- companies with stored filing text: {stored}",
              f"- fetched this run: {attempted} (already current: {skipped})",
              f"- written this run: {changed}", "",
              "## Sections found, of the filings fetched this run", ""]
    for k in WANTED:
        report.append(f"- {k}: {found[k]}")
    if short:
        report += ["", "## Sections not found, by company", "",
                   "A missing `item7` is often the filing's own doing — some filers put MD&A in an",
                   "exhibit and incorporate it by reference. A missing `item1` is the parser.", ""]
        report += [f"- {e}" for e in sorted(short)]
    if empty:
        report += ["", "## Left without text this run", ""] + [f"- {e}" for e in sorted(empty)]
    (OUT_DIR / "filings_report.md").write_text("\n".join(report) + "\n")
    print(f"done in {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
