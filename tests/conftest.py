"""Make the builder importable from the repo root, and give the tests a
vocabulary for writing synthetic companyfacts documents.

The SEC's companyfacts JSON nests facts as
    facts -> "us-gaap" | "dei" -> <TAG> -> "units" -> <UNIT> -> [ fact, ... ]
where a fact carries val, end, and (for period totals) start, plus the form it
was reported on, the fiscal period, and the filing date. Everything the
normaliser decides — which tag wins, which quarter a value belongs to, whether
a quarter can be derived at all — comes out of those few keys, so the helpers
below build them and nothing else.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))


def fact(val, end, start=None, form="10-K", fp="FY", filed=None, fy=None):
    """One XBRL fact. `filed` defaults to the period end, which is enough for the
    tie-breaks that prefer the latest filing (restatements win)."""
    f = {"val": val, "end": end, "form": form, "fp": fp, "filed": filed or end}
    if start is not None:
        f["start"] = start
    if fy is not None:
        f["fy"] = fy
    return f


def fy_fact(val, fy_end, form="10-K", **kw):
    """A full fiscal year ending on fy_end (365 days back, inside the 340-380 window)."""
    from datetime import date, timedelta

    end = date.fromisoformat(fy_end)
    return fact(val, fy_end, start=(end - timedelta(days=365)).isoformat(), form=form, **kw)


def q_fact(val, q_end, form="10-Q", **kw):
    """A genuine ~3-month fact ending on q_end (91 days back, inside the 80-100 window)."""
    from datetime import date, timedelta

    end = date.fromisoformat(q_end)
    kw.setdefault("fp", "Q1")
    return fact(val, q_end, start=(end - timedelta(days=91)).isoformat(), form=form, **kw)


def ytd_fact(val, fy_start, end, form="10-Q", **kw):
    """A cumulative year-to-date fact: the shape a 10-Q uses for cash-flow lines."""
    kw.setdefault("fp", "Q2")
    return fact(val, end, start=fy_start, form=form, **kw)


def doc(us_gaap=None, dei=None, cik=1234567, name="Test Filer Inc."):
    """A companyfacts document. Each tag maps to {unit: [facts]}."""
    def wrap(d):
        return {tag: {"units": units} for tag, units in (d or {}).items()}

    return {"cik": cik, "entityName": name,
            "facts": {"us-gaap": wrap(us_gaap), "dei": wrap(dei)}}


def usd(*facts):
    return {"USD": list(facts)}


def shares(*facts):
    return {"shares": list(facts)}


@pytest.fixture(scope="session")
def b():
    import build_sec_dataset

    return build_sec_dataset
