"""Known-answer tests (owner, 25 Sep 2026: "nothing gets misdirected or silent bugs happen"): 15 companies whose
filings broke earlier builds (COP, LHX, NTAP, CTAS, ORCL, CAT, BRK-B, HEI, MKL, GE, CNP, JPM, AAPL, RSG, DTE) are
rebuilt offline from saved SEC data (tests/golden/<TICKER>.json.gz) and must give the values in
tests/golden/expected.json, each with its evidence (Robinhood agreement, the filing's own quarters, the 10-K). A code
change that moves one of them fails CI. To change an expected value, fix the evidence first, then regenerate with
tests/golden_harness.py and say why in the commit."""
import json
from pathlib import Path

import pytest

import golden_harness as G  # noqa: E402

EXPECTED = json.loads((Path(__file__).parent / "golden" / "expected.json").read_text())


def close(a, b):
    if a is None or b is None:
        return a is b
    return abs(a - b) <= 0.001 * max(abs(b), 1)


@pytest.mark.parametrize("ticker", sorted(EXPECTED))
def test_golden_company(ticker):
    want, got = EXPECTED[ticker], G.summary(G.build(ticker))
    assert set(got["fy"]) == set(want["fy"]), "fiscal years moved"
    for end, fields in want["fy"].items():
        for f, v in fields.items():
            assert close(got["fy"][end][f], v), f"{ticker} {end} {f}: {got['fy'][end][f]} != {v} ({want['evidence']})"
    for f in ("ttm_revenue", "total_debt", "shares_total"):
        assert close(got[f], want[f]), f"{ticker} {f}: {got[f]} != {want[f]} ({want['evidence']})"
    assert got["flags"] == want["flags"], f"{ticker} flags: {got['flags']} != {want['flags']}"
    assert got["gate"] == want["gate"] and got["reconciles"] == want["reconciles"] == "ok"
