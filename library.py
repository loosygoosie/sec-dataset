"""Complete filing library (owner, 25 Sep 2026: "fix the sec-dataset library to fetch everything").

EVERY filing each universe company made in the window (LIBRARY_YEARS, default 3 years, all forms) and EVERY document
in each filing, checked against EDGAR's own filing list. pipeline_v2.py calls run() for its universe (>= $15B).

Why: fetch_filings.py's EVERYTHING mode still kept a subset (the latest 10-K + 2 prior, 10-Qs only after the latest
10-K, the latest DEF 14A, 8-Ks and insider forms of 400 days, capped 424Bs, and no Form 425 / ARS / 11-K / SD /
PX14A6G / FWP ...). On Cintas it held 83 of the 201 filings made since Jan 2024. fmp's owner/fetch_company.py showed
the way that gets all of them fast: ONE request per filing, for the complete submission file
    https://www.sec.gov/Archives/edgar/data/<cik>/<acc_nodash>/<acc>.txt
which holds every document of the filing (exhibits, PDFs uuencoded, the XBRL instance). It is split into its
<DOCUMENT> blocks here; HTML becomes text (fetch_filings.to_text), PDFs are uudecoded and read with pypdf, Forms
3/4/5 become one line per transaction (fetch_filings.ownership_lines), other XML becomes 'element: value' lines,
and the XBRL instance of each 10-K / 10-Q is kept whole. Graphics, R*.htm pages, FilingSummary, Excel/JSON/ZIP
files and the EX-101 schema/linkbase files are skipped (no text, or rebuilt from the instance).

SEC fair access: THREADS filings in flight under ONE shared throttle of 8 requests/second (the SEC's limit is 10/s;
SEC_MIN_GAP slows it further). The user agent comes only from SEC_USER_AGENT (build_sec_events.HEADERS). Never
rotate IPs or user agents.

Storage: GitHub RELEASE ASSETS on the fixed tag `library` of this repo (public, no auth to download), NOT a git branch
(a force-pushed 1.7 GB branch bloats the repo and runs into GitHub's limits):
    <cik>.tar.gz          one per company, extracting to <cik>/:
        <acc>_<filed>_<form>[_<doc type>].txt.gz   the text of each document (the first is the filing's main one)
        xbrl/<acc>.xml.gz                          the XBRL instance of each 10-K / 10-Q (and amendments)
        forms/<acc>.xml.gz                         the raw XML of each Form 3/4/5
        manifest.json                              the filing list (acc, form, filed, report, files, xbrl, raw),
                                                   edgar_filings (EDGAR's count in the window), saved_filings,
                                                   failures, deferred
    index.json            per company: ticker, name, asset, bytes, edgar_filings, saved_filings, documents, failures,
                          deferred, complete, updated, checked; plus run totals
    accessions.json.gz    {cik: [accession, ...]} saved per company: how a run knows what is new without
                          downloading every company's asset
An asset is replaced only when that company changed (a new filing saved or one left the window).

Incremental: EDGAR's list in the window (the submissions JSON, merged with its older pages when the `recent` block
does not reach back far enough) minus the accessions already saved = the filings fetched. A failure is not saved, so
it is retried on the next run; filings that left the window are dropped. LIBRARY_MINUTES (default 180) and
MAX_NEW_FILINGS (0 = no cap) bound one run; what is left is fetched on the next run and shows as `deferred`.
The daily index is not needed: the per-company submissions come from pipeline v2's submissions.zip (0 requests).

Every company's completeness (EDGAR's count vs saved, and every failure) is in its manifest, in index.json and in the
run report (data/v2/report.md), so a company with gaps is visible.

Read one company:  curl -sL https://github.com/<repo>/releases/download/library/<cik>.tar.gz | tar xz -C <dir>
"""
from __future__ import annotations

import binascii
import datetime as dt
import gzip
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import build_sec_events as _ev
import fetch_filings as ff

YEARS = float(os.environ.get("LIBRARY_YEARS", "3") or 3)
THREADS = int(os.environ.get("LIBRARY_THREADS", "6") or 6)
MINUTES = float(os.environ.get("LIBRARY_MINUTES", "180") or 180)
MAX_NEW = int(os.environ.get("MAX_NEW_FILINGS", "0") or 0)
TAG = os.environ.get("LIBRARY_TAG", "library")
REPO = os.environ.get("LIBRARY_REPO") or os.environ.get("GITHUB_REPOSITORY") or "loosygoosie/sec-dataset"
WORK = Path(os.environ.get("LIBRARY_WORK", "work/library"))
RATE = max(0.125, float(os.environ.get("SEC_MIN_GAP", "0") or 0))   # seconds between SEC requests, all threads
GRACE_DAYS = 30                     # a company out of the universe this long loses its asset (a dip is not a delete)
TODAY = dt.date.today()

ARCHIVE_TXT = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{acc}.txt"
XBRL_FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A", "10-KT", "10-KT/A", "10-QT", "10-QT/A"}
INSIDER_FORMS = {"3", "4", "5", "3/A", "4/A", "5/A"}
SKIP_TYPES = ("GRAPHIC", "ZIP", "EXCEL", "JSON", "EX-101")
SKIP_NAMES = re.compile(r"(^R\d+\.htm$|^FilingSummary|\.(xsd|css|js|jpg|jpeg|gif|png|bmp|tif|tiff|zip|xlsx|xls|json)$)",
                        re.I)


# ================================================================ SEC access (shared throttle)
_lock, _next = threading.Lock(), [0.0]


def sec_get(url: str, tries: int = 4) -> bytes | None:
    """GET under one throttle shared by every thread (RATE seconds apart, 8/s at most). None on 404 or after
    `tries` failures. A 403/429 (rate limit) pushes every thread back."""
    import requests
    for k in range(tries):
        with _lock:
            wait = _next[0] - time.time()
            if wait > 0:
                time.sleep(wait)
            _next[0] = time.time() + RATE
        try:
            r = requests.get(url, headers=_ev.HEADERS, timeout=120)
        except Exception as e:                                      # noqa: BLE001
            print(f"    retry {k + 1} {url[-70:]}: {type(e).__name__}", flush=True)
            time.sleep(2 * (k + 1))
            continue
        if r.status_code == 200:
            return r.content
        if r.status_code == 404:
            return None
        if r.status_code in (403, 429):
            with _lock:
                _next[0] = max(_next[0], time.time() + 30 * (k + 1))
        time.sleep(2 * (k + 1))
    return None


# ================================================================ the complete submission file
def _decode(b: bytes) -> str:
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("cp1252", "replace")


def _tag(block: bytes, name: str) -> str:
    m = re.search(rb"<" + name.encode() + rb">([^\r\n<]*)", block)
    return _decode(m.group(1)).strip() if m else ""


def split_submission(raw: bytes) -> list[tuple[str, str, str]]:
    """The complete submission file (<acc>.txt) -> [(TYPE, FILENAME, body text)], one per <DOCUMENT> block, in order
    (the filing's main document first)."""
    out = []
    for m in re.finditer(rb"<DOCUMENT>(.*?)</DOCUMENT>", raw, re.S):
        d = m.group(1)
        body = re.search(rb"<TEXT>(.*)</TEXT>", d, re.S)
        out.append((_tag(d, "TYPE"), _tag(d, "FILENAME"), _decode(body.group(1)) if body else ""))
    return out


def uudecode(text: str) -> bytes:
    """A uuencoded block (how the submission file carries PDFs) -> bytes. Lines before `begin` (a <PDF> wrapper)
    are ignored; a line with trailing garbage is cut to the length its first character declares."""
    lines = text.splitlines()
    start = next((i for i, x in enumerate(lines) if x.startswith("begin ")), None)
    if start is None:
        return b""
    out = bytearray()
    for line in lines[start + 1:]:
        if line.strip() == "end":
            break
        if not line:
            continue
        try:
            out += binascii.a2b_uu(line)
        except binascii.Error:
            n = (((ord(line[0]) - 32) & 63) * 4 + 5) // 3
            try:
                out += binascii.a2b_uu(line[:n])
            except binascii.Error:
                pass
    return bytes(out)


def _inner_xml(body: str) -> bytes:
    x = re.search(r"<XML>(.*)</XML>", body, re.S)
    return (x.group(1) if x else body).strip().encode("utf-8")


def safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", s or "")


def is_instance(typ: str, fn: str, body: str) -> bool:
    return typ.upper().startswith("EX-101.INS") or (fn.lower().endswith("_htm.xml") and "xbrl" in body[:3000].lower())


def process_submission(raw: bytes, f: dict) -> dict:
    """One filing's submission file -> {docs: [(name, type, filename, text)], xbrl: bytes|None, raw: bytes|None
    (Form 3/4/5 XML), errors: [...], listed: [(type, filename)]}. No I/O: save_filing writes it."""
    acc, form, filed = f["acc"], f["form"], f["date"]
    base = f"{acc}_{filed}_{safe(form)}"
    res = dict(docs=[], xbrl=None, raw=None, errors=[], listed=[])
    names: set = set()
    for typ, fn, body in split_submission(raw):
        res["listed"].append((typ, fn))
        low = fn.lower()
        try:
            if is_instance(typ, fn, body):
                if form in XBRL_FORMS:
                    res["xbrl"] = _inner_xml(body)
                continue
            if typ.upper().startswith(SKIP_TYPES) or SKIP_NAMES.search(fn) or typ.upper() == "XML":
                continue
            if low.endswith(".pdf"):
                text = ff.pdf_text(uudecode(body)) or "(PDF without a text layer)"
            elif low.endswith(".xml"):
                xml = _inner_xml(body)
                if form in INSIDER_FORMS:
                    res["raw"] = xml
                    text = "\n".join(ff.ownership_lines(xml, acc, form, filed))
                else:
                    text = ff.xml_text(xml)
            else:
                text = ff.to_text(body)
            if not text or not text.strip():
                continue
            tag = "" if not res["docs"] else "_" + (safe(typ) or "DOC")
            name, k = f"{base}{tag}.txt.gz", 2
            while name in names:
                name, k = f"{base}{tag}{k}.txt.gz", k + 1
            names.add(name)
            res["docs"].append((name, typ, fn, text))
        except Exception as e:                                      # noqa: BLE001
            res["errors"].append(f"{typ} {fn}: {type(e).__name__}: {e}"[:300])
    if not res["docs"]:
        # a filing with no text at all (a paper filing's header, graphics only): say so, and count it as held
        listed = "; ".join(f"{t} {n}".strip() for t, n in res["listed"]) or "no documents"
        res["docs"].append((f"{base}.txt.gz", form, "", f"(no text documents in this filing: {listed})"))
        res["note"] = "no text documents"
    return res


def save_filing(d: Path, f: dict, res: dict) -> dict:
    """Writes one processed filing under the company folder d and returns its manifest entry."""
    for name, _t, _n, text in res["docs"]:
        with gzip.open(d / name, "wt", encoding="utf-8") as fh:
            fh.write(text)
    e = dict(acc=f["acc"], form=f["form"], filed=f["date"], report=f.get("report") or "",
             files=[dict(file=n, type=t, name=fn, chars=len(x)) for n, t, fn, x in res["docs"]])
    if res.get("xbrl"):
        (d / "xbrl").mkdir(exist_ok=True)
        with gzip.open(d / "xbrl" / f"{f['acc']}.xml.gz", "wb") as fh:
            fh.write(res["xbrl"])
        e["xbrl"] = f"xbrl/{f['acc']}.xml.gz"
    if res.get("raw"):
        (d / "forms").mkdir(exist_ok=True)
        with gzip.open(d / "forms" / f"{f['acc']}.xml.gz", "wb") as fh:
            fh.write(res["raw"])
        e["raw"] = f"forms/{f['acc']}.xml.gz"
    if res.get("note"):
        e["note"] = res["note"]
    if res.get("errors"):
        e["doc_errors"] = res["errors"]
    return e


def remove_filing(d: Path, e: dict):
    for x in e.get("files", []):
        (d / x["file"]).unlink(missing_ok=True)
    for k in ("xbrl", "raw"):
        if e.get(k):
            (d / e[k]).unlink(missing_ok=True)


# ================================================================ what EDGAR lists, what is new
def window_start(today: dt.date = TODAY, years: float = YEARS) -> str:
    return str(today - dt.timedelta(days=int(round(years * 365.25))))


def _rows(block: dict) -> list[dict]:
    return [dict(form=f, date=d, acc=a, report=r) for f, d, a, r in
            zip(block.get("form", []), block.get("filingDate", []), block.get("accessionNumber", []),
                block.get("reportDate", []) or [""] * len(block.get("form", [])))]


def window_rows(sub: dict, since: str, load_page) -> list[dict]:
    """EVERY filing EDGAR lists for the company on or after `since`, newest first, one per accession. The `recent`
    block holds ~1,000 filings (or a year); the older pages in `files` are merged when their range reaches the
    window. A page that cannot be read raises: an undercounted EDGAR list would pass for complete."""
    fl = sub.get("filings", {})
    rows = _rows(fl.get("recent", {}))
    for page in fl.get("files", []) or []:
        if (page.get("filingTo") or "9999") < since:
            continue
        p = load_page(page["name"])
        if p is None:
            raise RuntimeError(f"submissions page {page['name']} not read")
        rows += _rows(p)
    seen, out = set(), []
    for r in rows:
        if r["date"] >= since and r["acc"] not in seen:
            seen.add(r["acc"])
            out.append(r)
    return sorted(out, key=lambda r: (r["date"], r["acc"]), reverse=True)


def plan_fetch(rows: list[dict], saved: dict) -> tuple[list[dict], dict, list[str]]:
    """(filings to fetch = EDGAR's rows not saved yet, saved entries still in the window, accessions to drop)."""
    in_window = {r["acc"] for r in rows}
    todo = [r for r in rows if r["acc"] not in saved]
    keep = {a: e for a, e in saved.items() if a in in_window}
    return todo, keep, sorted(set(saved) - in_window)


def completeness(rows: list[dict], filings: dict, failures: list | None = None, deferred: int = 0) -> dict:
    """EDGAR's count in the window vs what is saved; `missing` names every accession not held."""
    missing = [r["acc"] for r in rows if r["acc"] not in filings]
    return dict(edgar_filings=len(rows), saved_filings=len(rows) - len(missing), missing=missing,
                failures=len(failures or []), deferred=deferred, complete=not missing)


def needs_update(rows: list[dict], saved_accs: set, entry: dict | None) -> bool:
    """A company is opened (asset downloaded, filings fetched, repacked) only when EDGAR's window differs from what
    is saved: a new filing, a failure to retry, or a filing that left the window."""
    return entry is None or {r["acc"] for r in rows} != set(saved_accs)


# ================================================================ where the library lives
class Release:
    """The release assets of REPO@TAG. Downloads are public (no token); uploads and deletes use the gh CLI with
    GH_TOKEN (the workflow's GITHUB_TOKEN, contents: write)."""

    def __init__(self, repo: str = REPO, tag: str = TAG):
        self.repo, self.tag = repo, tag

    def get(self, name: str) -> bytes | None:
        """The asset's bytes; None when it does not exist (404). Any other failure raises."""
        import requests
        url = f"https://github.com/{self.repo}/releases/download/{self.tag}/{name}"
        err = None
        for k in range(4):
            try:
                r = requests.get(url, timeout=600)
                if r.status_code == 200:
                    return r.content
                if r.status_code == 404:
                    return None
                err = f"HTTP {r.status_code}"
            except Exception as e:                                  # noqa: BLE001
                err = type(e).__name__
            time.sleep(5 * (k + 1))
        raise RuntimeError(f"release asset {name}: {err}")

    def _gh(self, *args) -> bool:
        for k in range(3):
            p = subprocess.run(["gh", "release", *args, "--repo", self.repo], capture_output=True, text=True)
            if p.returncode == 0:
                return True
            print(f"    gh release {args[0]} {args[-1] if args else ''}: {p.stderr.strip()[:200]}", flush=True)
            time.sleep(5 * (k + 1))
        return False

    def put(self, path: Path) -> bool:
        return self._gh("upload", self.tag, str(path), "--clobber")

    def delete(self, name: str) -> bool:
        return self._gh("delete-asset", self.tag, name, "--yes")


class LocalStore:
    """A folder standing in for the release (tests; a run without GH_TOKEN writes its assets here)."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

    def get(self, name: str) -> bytes | None:
        p = self.path / name
        return p.read_bytes() if p.exists() else None

    def put(self, path: Path) -> bool:
        shutil.copyfile(path, self.path / Path(path).name)
        return True

    def delete(self, name: str) -> bool:
        (self.path / name).unlink(missing_ok=True)
        return True


def pack(d: Path, dest: Path) -> int:
    """<cik>/ folder -> <cik>.tar.gz (entries under <cik>/); returns its size in bytes."""
    with tarfile.open(dest, "w:gz", compresslevel=6) as t:
        t.add(d, arcname=d.name)
    return dest.stat().st_size


def unpack(blob: bytes, into: Path):
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as t:
        t.extractall(into, filter="data")


# ================================================================ one company
class Budget:
    def __init__(self, minutes: float | None = None, max_new: int | None = None):
        self.deadline = time.time() + (MINUTES if minutes is None else minutes) * 60
        self.max_new, self.fetched = (MAX_NEW if max_new is None else max_new), 0
        self._l = threading.Lock()

    def spent(self) -> bool:
        return time.time() > self.deadline or bool(self.max_new and self.fetched >= self.max_new)

    def take(self) -> bool:
        with self._l:
            if self.spent():
                return False
            self.fetched += 1
            return True


def fetch_filing(cik: int, f: dict) -> tuple[dict | None, str | None]:
    raw = sec_get(ARCHIVE_TXT.format(cik=cik, acc_nodash=f["acc"].replace("-", ""), acc=f["acc"]))
    if raw is None:
        return None, "complete submission file not fetched (404 or repeated errors)"
    return process_submission(raw, f), None


def update_company(c: dict, rows: list[dict], store, entry: dict | None, budget: Budget, changes: list,
                   fetch=fetch_filing, threads: int = THREADS) -> tuple[dict, list[str] | None]:
    """Brings one company's asset up to EDGAR's window. Returns (index entry, saved accessions or None when the
    asset was not replaced)."""
    cik = c["cik"]
    name = f"{cik}.tar.gz"
    d = WORK / str(cik)
    shutil.rmtree(d, ignore_errors=True)
    WORK.mkdir(parents=True, exist_ok=True)
    old = None
    if entry and entry.get("asset"):
        blob = store.get(name)                                      # raises on anything but a 404
        if blob is not None:
            unpack(blob, WORK)
            if (d / "manifest.json").exists():
                old = json.loads((d / "manifest.json").read_text())
    d.mkdir(parents=True, exist_ok=True)
    saved = {e["acc"]: e for e in (old or {}).get("filings", [])}
    todo, keep, drop = plan_fetch(rows, saved)
    for a in drop:
        remove_filing(d, saved[a])
    failures, deferred, new = [], 0, []
    lock = threading.Lock()

    def work(f):
        nonlocal deferred
        if not budget.take():
            with lock:
                deferred += 1
            return
        try:
            res, err = fetch(cik, f)
            if res is not None:
                e = save_filing(d, f, res)
        except Exception as ex:                                     # noqa: BLE001
            res, err = None, f"{type(ex).__name__}: {ex}"[:300]
        with lock:
            if res is None:
                failures.append(dict(acc=f["acc"], form=f["form"], filed=f["date"], error=err))
            else:
                keep[f["acc"]] = e
                new.append(e)

    with ThreadPoolExecutor(max(1, threads)) as ex:
        list(ex.map(work, todo))
    comp = completeness(rows, keep, failures, deferred)
    filings = sorted(keep.values(), key=lambda e: (e["filed"], e["acc"]), reverse=True)
    docs = sum(len(e["files"]) for e in filings)
    base = dict(ticker=c.get("ticker"), name=c.get("name"), mcap=c.get("mcap"), asset=(entry or {}).get("asset"),
                bytes=(entry or {}).get("bytes"), updated=(entry or {}).get("updated"), checked=str(TODAY),
                window_start=window_start(), documents=docs,
                **{k: v for k, v in comp.items() if k != "missing"}, in_universe=True, left=None, error=None,
                failed=failures[:50])
    if not new and not drop:
        shutil.rmtree(d, ignore_errors=True)                        # nothing to replace; the asset (if any) stands
        return base, None
    man = dict(cik=cik, ticker=c.get("ticker"), name=c.get("name"), updated=str(TODAY), window_start=window_start(),
               window_years=YEARS, edgar_filings=comp["edgar_filings"], saved_filings=comp["saved_filings"],
               complete=comp["complete"], documents=docs, failures=failures, deferred=deferred,
               missing=comp["missing"], forms=_forms(filings), filings=filings)
    (d / "manifest.json").write_text(json.dumps(man, indent=1))
    out = WORK / "out"
    out.mkdir(exist_ok=True)
    size = pack(d, out / name)
    ok = store.put(out / name)
    (out / name).unlink(missing_ok=True)
    shutil.rmtree(d, ignore_errors=True)
    if not ok:
        base["error"] = "upload failed"
        return base, None
    if old is not None:
        for e in new:
            changes.append(dict(date=str(TODAY), cik=cik, ticker=c.get("ticker"), type="new_filing", form=e["form"],
                                filed=e["filed"], accession=e["acc"], file=e["files"][0]["file"] if e["files"] else None))
    base.update(asset=name, bytes=size, updated=str(TODAY))
    return base, [e["acc"] for e in filings]


def _forms(filings: list[dict]) -> dict:
    out: dict = {}
    for e in filings:
        out[e["form"]] = out.get(e["form"], 0) + 1
    return dict(sorted(out.items()))


# ================================================================ a run
def load_state(store) -> tuple[dict, dict]:
    idx = store.get("index.json")
    acc = store.get("accessions.json.gz")
    index = json.loads(idx) if idx else {}
    return index.get("companies", {}), json.loads(gzip.decompress(acc)) if acc else {}


def save_state(store, companies: dict, accs: dict, totals: dict):
    WORK.mkdir(parents=True, exist_ok=True)
    p = WORK / "index.json"
    p.write_text(json.dumps(dict(updated=str(TODAY), window_years=YEARS, tag=TAG, repo=REPO,
                                 download=f"https://github.com/{REPO}/releases/download/{TAG}/<cik>.tar.gz",
                                 totals=totals, companies=companies), indent=1, sort_keys=False))
    q = WORK / "accessions.json.gz"
    q.write_bytes(gzip.compress(json.dumps(accs, separators=(",", ":")).encode()))
    store.put(q)
    store.put(p)


def totals_of(companies: dict) -> dict:
    live = [v for v in companies.values() if v.get("in_universe", True)]
    return dict(companies=len(live), complete=sum(1 for v in live if v.get("complete")),
                edgar_filings=sum(v.get("edgar_filings") or 0 for v in live),
                saved_filings=sum(v.get("saved_filings") or 0 for v in live),
                documents=sum(v.get("documents") or 0 for v in live),
                failures=sum(v.get("failures") or 0 for v in live),
                bytes=sum(v.get("bytes") or 0 for v in live))


def default_store():
    if os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"):
        return Release()
    print("library: no GH_TOKEN, assets go to work/library/assets (not published)", flush=True)
    return LocalStore(WORK / "assets")


def run(uni: list[dict], changes: list, load_sub, load_page, full: bool, store=None) -> dict:
    """Updates the library for the universe `uni` ([{cik, ticker, name, mcap}], largest first). load_sub(cik) and
    load_page(name) return submissions JSON (None when unavailable). full=True (the whole universe, not a smoke
    sample) also retires companies out of the universe for GRACE_DAYS. Returns the run's stats for the report."""
    store = store or default_store()
    companies, accs = load_state(store)
    budget, since, t0 = Budget(), window_start(), time.time()
    stats = dict(companies=len(uni), updated=0, unchanged=0, errors=[], new_filings=0, fetched=0)
    for i, c in enumerate(uni, 1):
        key = str(c["cik"])
        try:
            sub = load_sub(c["cik"])
            if sub is None:
                raise RuntimeError("no submissions JSON")
            rows = window_rows(sub, since, load_page)
            entry = companies.get(key)
            if not needs_update(rows, accs.get(key, []), entry):
                comp = completeness(rows, dict.fromkeys(accs.get(key, [])))
                entry.update(ticker=c.get("ticker"), name=c.get("name"), mcap=c.get("mcap"), checked=str(TODAY),
                             in_universe=True, left=None, failures=0, deferred=0, error=None, failed=[],
                             **{k: v for k, v in comp.items() if k not in ("missing", "failures", "deferred")})
                stats["unchanged"] += 1
                continue
            if budget.spent():                                      # out of time: count the gap, open nothing
                comp = completeness(rows, dict.fromkeys(accs.get(key, [])))
                companies[key] = dict(entry or {}, ticker=c.get("ticker"), name=c.get("name"), mcap=c.get("mcap"),
                                      checked=str(TODAY), in_universe=True, left=None, failures=0,
                                      deferred=len(comp["missing"]), edgar_filings=comp["edgar_filings"],
                                      saved_filings=comp["saved_filings"], complete=comp["complete"], error=None)
                continue
            before = budget.fetched
            n_before = len(changes)
            e, saved = update_company(c, rows, store, entry, budget, changes)
            stats["fetched"] += budget.fetched - before
            stats["new_filings"] += len(changes) - n_before
            companies[key] = dict(entry or {}, **e)
            if saved is not None:
                accs[key] = saved
                stats["updated"] += 1
                if stats["updated"] % 25 == 0:
                    save_state(store, companies, accs, totals_of(companies))  # a killed run keeps its uploads
            print(f"  library {c.get('ticker')}: EDGAR {e['edgar_filings']}, saved {e['saved_filings']}, "
                  f"failures {e['failures']}, deferred {e['deferred']}"
                  + (f", {e['bytes'] / 1e6:.1f} MB" if e.get("bytes") else ""), flush=True)
        except Exception as ex:                                     # noqa: BLE001
            msg = f"{type(ex).__name__}: {ex}"[:300]
            stats["errors"].append(f"{c.get('ticker')} ({key}): {msg}")
            companies.setdefault(key, dict(ticker=c.get("ticker"), name=c.get("name"), complete=False))
            companies[key].update(error=msg, checked=str(TODAY), complete=False)
            print(f"  library {c.get('ticker')}: {msg}", flush=True)
        if i % 25 == 0:
            print(f"  library {i}/{len(uni)} ({budget.fetched} filings fetched, {time.time() - t0:.0f}s)", flush=True)
    if full:
        live = {str(c["cik"]) for c in uni}
        for key, v in list(companies.items()):
            if key in live:
                continue
            v["in_universe"] = False
            v["left"] = v.get("left") or str(TODAY)
            if str(TODAY - dt.timedelta(days=GRACE_DAYS)) >= v["left"]:
                if not v.get("asset") or store.delete(v["asset"]):
                    companies.pop(key)
                    accs.pop(key, None)
                    changes.append(dict(date=str(TODAY), cik=int(key), ticker=v.get("ticker"), type="left_library"))
    totals = totals_of(companies)
    save_state(store, companies, accs, totals)
    stats.update(totals=totals, seconds=round(time.time() - t0), deferred=sum(
        companies.get(str(c["cik"]), {}).get("deferred") or 0 for c in uni))
    stats["gaps"] = [dict(ticker=companies[k].get("ticker"), cik=int(k), edgar=companies[k].get("edgar_filings"),
                          saved=companies[k].get("saved_filings"), failures=companies[k].get("failures"),
                          deferred=companies[k].get("deferred"), error=companies[k].get("error"))
                     for k in (str(c["cik"]) for c in uni) if k in companies and not companies[k].get("complete")]
    return stats


def report_lines(stats: dict | None) -> list[str]:
    """The library section of data/v2/report.md: totals, then every company with a gap."""
    if not stats:
        return ["## Filing library", "", "- skipped this run"]
    t = stats["totals"]
    L = ["## Filing library", "",
         f"- release assets: https://github.com/{REPO}/releases/tag/{TAG} (one <cik>.tar.gz per company + index.json)",
         f"- window: filings since {window_start()} ({YEARS:g} years), every form, every document",
         f"- this run: {stats['companies']} companies checked, {stats['updated']} assets replaced, {stats['unchanged']} "
         f"unchanged; {stats['fetched']} filings fetched ({stats['new_filings']} logged as new), "
         f"{stats['deferred']} deferred to the next run; {stats['seconds'] / 60:.0f} min",
         f"- library: {t['companies']} companies, {t['complete']} complete; EDGAR lists {t['edgar_filings']} filings, "
         f"saved {t['saved_filings']} ({t['documents']} documents, {t['bytes'] / 1e9:.2f} GB); failures {t['failures']}",
         "", "### Companies with gaps (EDGAR count != saved)", ""]
    if stats["gaps"]:
        L += ["| ticker | cik | EDGAR | saved | failures | deferred | error |", "|---|---|---|---|---|---|---|"]
        L += [f"| {g['ticker']} | {g['cik']} | {g['edgar']} | {g['saved']} | {g['failures']} | {g['deferred']} | "
              f"{g['error'] or ''} |" for g in stats["gaps"]]
    else:
        L.append("- none")
    if stats["errors"]:
        L += ["", "### Errors", ""] + [f"- {x}" for x in stats["errors"]]
    return L
