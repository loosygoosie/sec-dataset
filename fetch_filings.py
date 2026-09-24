"""Filing library for fmp's deep reads (owner, 24 Sep 2026): every recent filing of every S&P 500-sized company, as
searchable text plus the full XBRL facts, kept on the `filings` branch and overwritten on every run.

Why: the reads and their SEC checks spent most of their time fetching the same filings through one shared SEC rate
limit (20 agents at 1 request / 2 s each). With the library on disk a read greps a section instead of downloading.

What is kept, per company (CIK), in <store>/<cik>/:
  manifest.json            ticker, name, the documents below, the 10-K's section offsets, and a facts summary
  <acc>_<name>.txt.gz      text of: the latest 10-K (and any 10-K/A after it), every 10-Q since that 10-K, the latest
                           DEF 14A proxy, and every 8-K of the last 400 days with its EX-99 exhibits (earnings releases)
  <acc>_xbrl.json.gz       ALL XBRL facts of the latest 10-K and the latest 10-Q, including the dimensioned ones the
                           SEC's companyfacts API drops (share classes, segments):
                           {concept: [[value, unit, start, end, {axis: member}], ...]}
<store>/index.json         {cik: {ticker, name, docs, updated}}

Universe: US companies with a 10-Q, a ticker and >= $1B of assets or revenue whose market value is >= UNIVERSE_MIN
($15B, a cushion under S&P's $22.7B minimum so companies near the line are already on hand), plus every CIK in
data/filings_extra.txt. Market value = max(Yahoo's, latest price x latest shares).

Changes: before overwriting, every new filing and every changed headline fact (revenue, net income, operating cash
flow, capex, debt, equity, shares per class) is appended to data/filings_changes.jsonl on main, which keeps its
history, so "what changed at this company and when" survives the overwrite.

Incremental: a document already in the store (same accession) is not fetched again; documents that left the window
are dropped. FULL=true refetches everything. LIMIT=n restricts to the first n companies (a smoke test).
SEC: header from SEC_USER_AGENT only; ~8 requests a second via build_sec_events.get.
"""
from __future__ import annotations

import datetime as dt
import gzip
import html
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

import build_sec_events as _ev
from build_sec_events import SUBMISSIONS, ARCHIVE_DOC


def get(url, retries=3):
    """build_sec_events.get (rate limit, retries on status codes) plus retries on timeouts/connection errors,
    which it raises; None when the document can't be had, so one bad filing never stops the run."""
    for k in range(retries):
        try:
            return _ev.get(url)
        except Exception as e:                                      # noqa: BLE001
            print(f"    retry {k + 1} {url[-60:]}: {type(e).__name__}", flush=True)
    return None


def exhibits_for(cik, acc):
    try:
        return _ev.exhibits_for(cik, acc)
    except Exception:                                               # noqa: BLE001
        return None

DATA = Path("data")
STORE = Path(os.environ.get("FILINGS_STORE", "filings-store"))
UNIVERSE_MIN = float(os.environ.get("UNIVERSE_MIN", "15e9"))
EIGHT_K_DAYS = 400
FULL = os.environ.get("FULL", "").strip().lower() in ("1", "true", "yes")
LIMIT = int(os.environ.get("LIMIT", "0") or 0)
TODAY = dt.date.today()

# headline facts compared run to run (first tag found wins); per share class via dei
SUMMARY_TAGS = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet",
                "RevenuesNetOfInterestExpense"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
    "long_term_debt": ["LongTermDebt", "LongTermDebtNoncurrent"],
    "debt_current": ["DebtCurrent", "LongTermDebtCurrent"],
    "short_term_borrowings": ["ShortTermBorrowings", "CommercialPaper"],
    "equity": ["StockholdersEquity"],
}


# ---------------------------------------------------------------- text
class _Text(HTMLParser):
    """HTML/iXBRL -> readable text: block elements end lines, table cells are joined with ' | ', hidden content
    (the iXBRL header, display:none blocks, scripts, styles) is skipped, tracked by nesting depth."""
    BLOCK = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table", "section"}
    VOID = {"br", "img", "input", "hr", "meta", "link", "col", "area", "base", "wbr", "source"}
    HIDE = {"ix:header", "script", "style", "head", "title"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.depth, self.hide_at = [], 0, None

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t in self.VOID:
            if t == "br" and self.hide_at is None:
                self.out.append("\n")
            return
        self.depth += 1
        if self.hide_at is None and (t in self.HIDE or any(
                k == "style" and "display:none" in (v or "").replace(" ", "").lower() for k, v in attrs)):
            self.hide_at = self.depth
            return
        if self.hide_at is None:
            if t in ("td", "th"):
                self.out.append(" | ")
            elif t in self.BLOCK:
                self.out.append("\n")

    def handle_startendtag(self, tag, attrs):
        if tag.lower() == "br" and self.hide_at is None:
            self.out.append("\n")

    def handle_endtag(self, tag):
        t = tag.lower()
        if t in self.VOID:
            return
        if self.hide_at is not None and self.depth <= self.hide_at:
            self.hide_at = None
        elif self.hide_at is None and t in self.BLOCK:
            self.out.append("\n")
        self.depth = max(0, self.depth - 1)

    def handle_data(self, data):
        if self.hide_at is None:
            self.out.append(data)


def to_text(raw: str) -> str:
    if "<" not in raw[:2000] and "<html" not in raw.lower()[:5000]:
        return raw                                            # already plain text (old .txt filings)
    p = _Text()
    p.feed(raw)
    t = html.unescape("".join(p.out)).replace("\xa0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" ?\| ?(\| ?)+", " | ", t)
    t = re.sub(r"\n\s*\n+", "\n\n", t)
    return "\n".join(line.strip(" |") for line in t.splitlines()).strip()


_ITEM = re.compile(r"(?im)^\s*item\s+(1a|1b|1c|1|2|3|4|5|6|7a|7|8|9a|9b|9c|9|10|11|12|13|14|15|16)\s*[\.\:\-—–]")


def sections(text: str) -> dict:
    """{item: [start, end]} for a 10-K. The table of contents repeats every heading close together, so for each
    item the LAST heading is used, which is the one that starts the section itself."""
    last = {}
    for m in _ITEM.finditer(text):
        last[m.group(1).lower()] = m.start()
    order = sorted(last.items(), key=lambda kv: kv[1])
    out = {}
    for i, (k, s) in enumerate(order):
        e = order[i + 1][1] if i + 1 < len(order) else len(text)
        if e - s > 200:
            out[k] = [s, e]
    return out


# ---------------------------------------------------------------- xbrl
def xbrl_facts(xml_bytes: bytes) -> dict:
    """Every fact in an XBRL instance: {concept (prefix:name): [[value, unit, start, end, {axis: member}], ...]}.
    Numeric values become floats; nil facts are skipped."""
    root = ET.fromstring(xml_bytes)
    X = "{http://www.xbrl.org/2003/instance}"
    ns = {v: k for k, v in re.findall(r'xmlns:([\w\-]+)="([^"]+)"', xml_bytes[:20000].decode("utf-8", "ignore"))}
    ctx = {}
    for c in root.iter(X + "context"):
        per = c.find(X + "period")
        start = per.findtext(X + "startDate") if per is not None else None
        end = (per.findtext(X + "endDate") or per.findtext(X + "instant")) if per is not None else None
        dims = {m.get("dimension"): (m.text or "").strip() for m in c.iter() if m.tag.endswith("explicitMember")}
        ctx[c.get("id")] = (start, end, dims)
    units = {u.get("id"): "/".join(m.text.split(":")[-1] for m in u.iter() if m.tag.endswith("measure") and m.text)
             for u in root.iter(X + "unit")}
    out: dict = {}
    for el in root:
        if not el.tag.startswith("{") or el.get("contextRef") is None:
            continue
        if el.get("{http://www.w3.org/2001/XMLSchema-instance}nil") == "true":
            continue
        uri, name = el.tag[1:].split("}", 1)
        key = f"{ns.get(uri, uri.rsplit('/', 2)[-2] if '/' in uri else uri)}:{name}"
        txt = (el.text or "").strip()
        if not txt:
            continue
        try:
            val = float(txt)
        except ValueError:
            if len(txt) > 500:
                continue                                        # long text blocks: the .txt copy has them
            val = txt
        s, e, d = ctx.get(el.get("contextRef"), (None, None, {}))
        out.setdefault(key, []).append([val, units.get(el.get("unitRef")), s, e, d])
    return out


def summary(facts: dict) -> dict:
    """Headline figures for change detection: latest undimensioned value per SUMMARY_TAGS field, and shares
    outstanding per class from the cover (dei:EntityCommonStockSharesOutstanding)."""
    out = {}
    for field, tags in SUMMARY_TAGS.items():
        for t in tags:
            rows = [r for r in facts.get(f"us-gaap:{t}", []) if not r[4] and isinstance(r[0], float)]
            if rows:
                r = max(rows, key=lambda r: (r[3] or "", -(dt.date.fromisoformat(r[3]) - dt.date.fromisoformat(r[2])).days
                                            if r[2] and r[3] else 0))
                out[field] = [r[0], r[2], r[3]]
                break
    cls = {}
    for r in facts.get("dei:EntityCommonStockSharesOutstanding", []):
        if isinstance(r[0], float):
            cls["|".join(sorted(r[4].values())) or "common"] = r[0]
    if cls:
        out["shares_by_class"] = cls
    return out


# ---------------------------------------------------------------- what to keep
def plan(sub: dict) -> list[dict]:
    """The filings to keep for one company, from its submissions JSON (recent block)."""
    r = sub.get("filings", {}).get("recent", {})
    rows = [dict(form=f, date=d, acc=a, doc=p, report=rd) for f, d, a, p, rd in
            zip(r.get("form", []), r.get("filingDate", []), r.get("accessionNumber", []),
                r.get("primaryDocument", []), r.get("reportDate", []))]
    tenk = [x for x in rows if x["form"] in ("10-K", "10-KT")]
    if not tenk:
        return []
    k = max(tenk, key=lambda x: x["date"])
    keep = [k]
    keep += [x for x in rows if x["form"] in ("10-K/A",) and x["date"] >= k["date"]]
    keep += [x for x in rows if x["form"] in ("10-Q", "10-Q/A") and x["date"] > k["date"]]
    prox = [x for x in rows if x["form"] == "DEF 14A"]
    if prox:
        keep.append(max(prox, key=lambda x: x["date"]))
    since = str(TODAY - dt.timedelta(days=EIGHT_K_DAYS))
    keep += [x for x in rows if x["form"] in ("8-K", "8-K/A") and x["date"] >= since]
    return keep


# ---------------------------------------------------------------- universe
def universe(companies_dir: Path, tickers_path: Path) -> list[dict]:
    import yfinance as yf
    tick = json.loads(tickers_path.read_text())
    by_cik = {}
    for t, v in tick.items():
        by_cik.setdefault(int(v["cik"]), []).append(t)
    cand = []
    for p in companies_dir.glob("*.json"):
        d = json.loads(p.read_text())
        if not d.get("tickers") or not d.get("checks", {}).get("latest_quarter_end"):
            continue
        a = [x for x in d.get("annual", []) if x.get("fiscal_year")]
        if not a:
            continue
        last = max(a, key=lambda x: x["fiscal_year"])
        size = max(last.get("total_assets") or 0, last.get("revenue") or 0)
        if size < 1e9:
            continue
        q = sorted(d.get("quarterly", []), key=lambda x: x.get("period_end", ""))
        sh = next((x.get("shares_outstanding") for x in reversed(q) if x.get("shares_outstanding")), None)
        plain = [t for t in d["tickers"] if "-" not in t and "." not in t] or d["tickers"]
        cand.append(dict(cik=int(d["cik"]), ticker=sorted(plain, key=lambda t: (len(t), t))[0],
                         name=d.get("sec_name"), shares=sh))
    tick_list = [c["ticker"] for c in cand]
    px = {}
    for i in range(0, len(tick_list), 100):
        b = tick_list[i:i + 100]
        try:
            h = yf.download(b, period="5d", progress=False, auto_adjust=False, threads=True)["Close"]
            for t in b:
                if t in h and h[t].notna().any():
                    px[t] = float(h[t].dropna().iloc[-1])
        except Exception as e:                                      # noqa: BLE001
            print(f"price batch {i}: {type(e).__name__}")
    out = []
    for c in cand:
        est = (px.get(c["ticker"]) or 0) * (c["shares"] or 0)
        mc = est
        if est >= 5e9 or c["shares"] is None:
            try:
                mc = max(est, float(yf.Ticker(c["ticker"]).fast_info["market_cap"] or 0))
            except Exception:                                       # noqa: BLE001
                pass
        if mc >= UNIVERSE_MIN:
            out.append(dict(c, mcap=mc))
    extra = DATA / "filings_extra.txt"
    if extra.exists():
        have = {c["cik"] for c in out}
        known = {c["cik"]: c for c in cand}
        for line in extra.read_text().split():
            if line.strip().isdigit() and int(line) not in have:
                out.append(known.get(int(line), dict(cik=int(line), ticker=str(line), name=None)))
    return sorted(out, key=lambda c: -(c.get("mcap") or 0))


# ---------------------------------------------------------------- per company
def fetch_text(cik: int, acc: str, doc: str) -> str | None:
    r = get(ARCHIVE_DOC.format(cik=cik, acc_nodash=acc.replace("-", ""), doc=doc))
    return to_text(r.text) if r is not None else None


def fetch_url_text(url: str) -> str | None:
    r = get(url)
    return to_text(r.text) if r is not None else None


def instance_url(cik: int, acc: str) -> str | None:
    a = acc.replace("-", "")
    r = get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{a}/index.json")
    if r is None:
        return None
    names = [i["name"] for i in r.json().get("directory", {}).get("item", [])]
    inst = [n for n in names if n.endswith("_htm.xml")] or \
           [n for n in names if n.endswith(".xml") and not n.startswith("FilingSummary")
            and not n.endswith(("_cal.xml", "_def.xml", "_lab.xml", "_pre.xml"))]
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{a}/{inst[0]}" if inst else None


def write_gz(path: Path, text: str):
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write(text)


def company(c: dict, changes: list) -> dict | None:
    cik = c["cik"]
    sub_r = get(SUBMISSIONS.format(cik=cik))
    if sub_r is None:
        print(f"  {cik} {c['ticker']}: no submissions"); return None
    keep = plan(sub_r.json())
    d = STORE / str(cik)
    d.mkdir(parents=True, exist_ok=True)
    old = json.loads((d / "manifest.json").read_text()) if (d / "manifest.json").exists() else {}
    old_docs = {x["file"]: x for x in old.get("docs", [])}
    docs, want = [], set()

    def keep_file(name, meta, fetch):
        want.add(name)
        if not FULL and name in old_docs and (d / name).exists():
            docs.append(old_docs[name]); return
        t = fetch()
        if t is None:
            return
        write_gz(d / name, t)
        m = dict(meta, file=name, chars=len(t))
        docs.append(m)
        if name not in old_docs and old:
            changes.append(dict(date=str(TODAY), cik=cik, ticker=c["ticker"], type="new_filing",
                                form=meta["form"], filed=meta["filed"], accession=meta["accession"], file=name))

    tenk_text = None
    for f in keep:
        acc, meta = f["acc"], dict(form=f["form"], filed=f["date"], accession=f["acc"], period=f["report"])
        name = f"{acc}_{re.sub(r'[^A-Za-z0-9]+', '', f['form'])}.txt.gz"
        keep_file(name, dict(meta, doc=f["doc"]), lambda f=f: fetch_text(cik, f["acc"], f["doc"]))
        if f["form"] in ("8-K", "8-K/A"):
            ex_cache = old.get("exhibits", {}).get(acc)
            ex = ex_cache if ex_cache is not None and not FULL else exhibits_for(cik, acc)
            for e in ex or []:
                if not str(e.get("type", "")).startswith("EX-99"):
                    continue
                href = e.get("url") or e.get("href") or ""
                doc = href.rsplit("/", 1)[-1]
                if not doc:
                    continue
                en = f"{acc}_{re.sub(r'[^A-Za-z0-9]+', '', e['type'])}_{re.sub(r'[^A-Za-z0-9.]+', '', doc)}.txt.gz"
                keep_file(en, dict(meta, form=f"{f['form']} {e['type']}", doc=doc),
                          lambda href=href: fetch_url_text(href))
            f["_ex"] = ex
    # XBRL: all facts of the latest 10-K and the latest 10-Q after it
    fsum = {}
    for form in (("10-K", "10-KT"), ("10-Q",)):
        cands = [f for f in keep if f["form"] in form]
        if not cands:
            continue
        f = max(cands, key=lambda x: x["date"])
        name = f"{f['acc']}_xbrl.json.gz"

        def fx(f=f):
            u = instance_url(cik, f["acc"])
            r = get(u) if u else None
            return json.dumps(xbrl_facts(r.content), separators=(",", ":")) if r is not None else None
        keep_file(name, dict(form=f"{f['form']} XBRL", filed=f["date"], accession=f["acc"], period=f["report"]), fx)
        if (d / name).exists():
            try:
                with gzip.open(d / name, "rt") as fh:
                    fsum[form[0]] = summary(json.load(fh))
            except Exception:                                       # noqa: BLE001
                pass
    # 10-K sections
    secs = old.get("tenk_sections", {})
    k = next((f for f in keep if f["form"] in ("10-K", "10-KT")), None)
    if k:
        kn = f"{k['acc']}_{re.sub(r'[^A-Za-z0-9]+', '', k['form'])}.txt.gz"
        if (d / kn).exists() and (FULL or secs.get("file") != kn):
            with gzip.open(d / kn, "rt") as fh:
                secs = dict(file=kn, items=sections(fh.read()))
    # removals + fact changes
    for name in set(old_docs) - want:
        (d / name).unlink(missing_ok=True)
    for form, s in fsum.items():
        prev = old.get("facts_summary", {}).get(form, {})
        for field, v in s.items():
            if field in prev and prev[field] != v:
                changes.append(dict(date=str(TODAY), cik=cik, ticker=c["ticker"], type="fact_change", source=form,
                                    field=field, old=prev[field], new=v))
    man = dict(cik=cik, ticker=c["ticker"], name=c.get("name"), updated=str(TODAY),
               docs=sorted(docs, key=lambda x: (x["filed"], x["file"])), tenk_sections=secs, facts_summary=fsum,
               exhibits={f["acc"]: f.get("_ex") for f in keep if f.get("_ex") is not None})
    (d / "manifest.json").write_text(json.dumps(man, indent=1))
    return man


def main():
    STORE.mkdir(exist_ok=True)
    uni = universe(DATA / "companies", DATA / "tickers.json")
    if LIMIT:
        uni = uni[:LIMIT]
    print(f"universe: {len(uni)} companies >= ${UNIVERSE_MIN / 1e9:.1f}B", flush=True)
    changes, index = [], {}
    for i, c in enumerate(uni, 1):
        try:
            m = company(c, changes)
        except Exception as e:                                      # noqa: BLE001
            print(f"  {c['cik']} {c['ticker']}: {type(e).__name__}: {e}"); m = None
        if m:
            index[str(c["cik"])] = dict(ticker=c["ticker"], name=c.get("name"), docs=len(m["docs"]),
                                        updated=m["updated"], mcap=c.get("mcap"))
        if i % 25 == 0:
            print(f"  {i}/{len(uni)}", flush=True)
    if not LIMIT:                                                   # companies that left the universe
        for p in STORE.iterdir():
            if p.is_dir() and p.name.isdigit() and p.name not in index:
                for f in p.iterdir():
                    f.unlink()
                p.rmdir()
                changes.append(dict(date=str(TODAY), cik=int(p.name), type="left_universe"))
    (STORE / "index.json").write_text(json.dumps(index, indent=1))
    (STORE / "README.md").write_text(
        "Filing library for fmp (fetch_filings.py on main). Overwritten on every run; history of what changed is in "
        "main's data/filings_changes.jsonl.\n")
    with open(DATA / "filings_changes.jsonl", "a") as f:
        for ch in changes:
            f.write(json.dumps(ch) + "\n")
    rep = [f"# Filing library {TODAY}", "", f"- companies: {len(index)}", f"- documents: {sum(v['docs'] for v in index.values())}",
           f"- new filings: {sum(1 for c in changes if c['type'] == 'new_filing')}",
           f"- fact changes: {sum(1 for c in changes if c['type'] == 'fact_change')}"]
    (DATA / "filings_report.md").write_text("\n".join(rep) + "\n")
    print("\n".join(rep))


if __name__ == "__main__":
    sys.exit(main())
