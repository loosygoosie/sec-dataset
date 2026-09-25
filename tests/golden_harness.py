"""Builds a golden company exactly as pipeline_v2.company_record does, from tests/golden/<TICKER>.json.gz (the SEC's
submissions + companyfacts JSON, trimmed to facts ending 2019+, and the XBRL instances of its latest 10-K / 10-Q),
with no network. Used by tests/test_golden.py; also `python tests/golden_harness.py` prints the checked values."""
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pipeline_v2 as V  # noqa: E402

GOLD = Path(__file__).parent / "golden"


def build(ticker: str) -> dict:
    g = json.load(gzip.open(GOLD / f"{ticker}.json.gz", "rt"))
    c, why = V.candidate(g["sub"])
    assert c, why
    c["_two"] = V.latest_two(g["sub"])
    c["size"] = V.size_signals(g["cf"])
    c["gate"] = V.size_gate(c["size"], c["tenks"])
    c["cf_shares"] = V.cf_shares(g["cf"])
    weights, ads = V.load_weights(V.CONF / "share_class_weights.csv"), V.load_ads(V.CONF / "ads_ratio.csv")
    inst = g["instances"]
    cov = c["latest"]
    x = inst.get(cov["accn"]) if cov else None
    c["cover_date"], c["classes"] = V.cover_classes(x) if x else (None, {})
    c["shares_cover"] = sum(c["classes"].values()) if c["classes"] else None
    c["shares_total"] = V.shares_total(c["classes"], c["ticker"], weights, ads)

    class Src:
        def facts(self, cik):
            return g["cf"]
    saved = V.instance
    V.instance = lambda cik, accn: inst.get(accn)
    try:
        return V.company_record(c, Src())
    finally:
        V.instance = saved


def summary(rec: dict) -> dict:
    """The values the golden test pins: the last two fiscal years' revenue / net income / capex, TTM revenue, the
    balance's total debt, cover shares, flags, and the old-shape file's reconcile check."""
    ann = sorted(rec["v2_annual"], key=lambda r: r["end"])[-2:]
    return {"fy": {r["end"]: {f: r.get(f) for f in ("revenue", "net_income", "capex")} for r in ann},
            "ttm_revenue": (rec["ttm"].get("revenue") or {}).get("val"),
            "total_debt": rec["balance"].get("total_debt"), "shares_total": rec["market"]["shares_total"],
            "gate": rec["market"]["size_gate"], "flags": sorted(rec["flags"]), "reconciles": rec["checks"].get("reconciles")}


if __name__ == "__main__":
    for p in sorted(GOLD.glob("*.json.gz")):
        t = p.name.split(".")[0]
        print(t, json.dumps(summary(build(t))))
