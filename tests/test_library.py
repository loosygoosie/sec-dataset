"""library.py: the complete filing library (owner, 25 Sep 2026: every filing of the window, every document in it).

No network: submission files are built here, the SEC fetch and the release are replaced by fakes (a LocalStore
folder stands in for the GitHub release)."""
import binascii
import gzip
import io
import json
import tarfile

import pytest

import library as L

FORM4 = b"""<?xml version="1.0"?><ownershipDocument><documentType>4</documentType>
<reportingOwner><reportingOwnerId><rptOwnerName>Doe Jane</rptOwnerName></reportingOwnerId>
<reportingOwnerRelationship><isDirector>0</isDirector><isOfficer>1</isOfficer><officerTitle>CFO</officerTitle>
</reportingOwnerRelationship></reportingOwner>
<nonDerivativeTable><nonDerivativeTransaction><securityTitle><value>Common Stock</value></securityTitle>
<transactionDate><value>2026-09-01</value></transactionDate><transactionCoding><transactionCode>S</transactionCode>
</transactionCoding><transactionAmounts><transactionShares><value>1000</value></transactionShares>
<transactionPricePerShare><value>250.5</value></transactionPricePerShare>
<transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode></transactionAmounts>
<postTransactionAmounts><sharesOwnedFollowingTransaction><value>5000</value></sharesOwnedFollowingTransaction>
</postTransactionAmounts><ownershipNature><directOrIndirectOwnership><value>D</value></directOrIndirectOwnership>
</ownershipNature></nonDerivativeTransaction></nonDerivativeTable></ownershipDocument>"""

INSTANCE = ('<?xml version="1.0"?><xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" '
            'xmlns:us-gaap="http://fasb.org/us-gaap/2024"><us-gaap:Revenues contextRef="c1">5</us-gaap:Revenues>'
            '</xbrli:xbrl>')


def doc(typ, fn, body):
    return f"<DOCUMENT>\n<TYPE>{typ}\n<SEQUENCE>1\n<FILENAME>{fn}\n<TEXT>\n{body}\n</TEXT>\n</DOCUMENT>\n"


def submission(*docs):
    return ("<SEC-DOCUMENT>0000000000-26-000001.txt : 20260901\n<SEC-HEADER>\nCONFORMED SUBMISSION TYPE: 10-K\n"
            "</SEC-HEADER>\n" + "".join(docs) + "</SEC-DOCUMENT>\n").encode("utf-8")


def uuencode(data: bytes, name: str) -> str:
    lines = [f"begin 644 {name}"]
    lines += [binascii.b2a_uu(data[i:i + 45]).decode().rstrip("\n") for i in range(0, len(data), 45)]
    return "<PDF>\n" + "\n".join(lines + ["`", "end"]) + "\n</PDF>"


def tiny_pdf(text: str) -> bytes:
    """A one-page PDF whose page says `text` (Helvetica), with a correct xref table."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> "
            b"/Contents 4 0 R >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offs = bytearray(b"%PDF-1.4\n"), []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    x = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offs)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, x)
    return bytes(out)


F10K = dict(acc="0000000000-26-000001", form="10-K", date="2026-09-01", report="2026-06-30")


# ---------------------------------------------------------------- the splitter
def test_split_submission_yields_every_document_in_order():
    raw = submission(doc("10-K", "a-10k.htm", "<html><p>Annual report</p></html>"),
                     doc("EX-21.1", "ex21.htm", "<p>Subsidiaries</p>"),
                     doc("GRAPHIC", "logo.jpg", "begin 644 logo.jpg\n`\nend"))
    got = L.split_submission(raw)
    assert [(t, f) for t, f, _ in got] == [("10-K", "a-10k.htm"), ("EX-21.1", "ex21.htm"), ("GRAPHIC", "logo.jpg")]
    assert "Annual report" in got[0][2]


def test_process_keeps_every_text_document_and_the_instance_and_skips_the_rest():
    raw = submission(doc("10-K", "a-10k.htm", "<html><p>Annual report</p></html>"),
                     doc("EX-21.1", "ex21.htm", "<p>Subsidiaries: Foo LLC</p>"),
                     doc("EX-99.1", "ex99.txt", "plain text exhibit"),
                     doc("GRAPHIC", "logo.jpg", "begin 644 logo.jpg\n`\nend"),
                     doc("XML", "R1.htm", "<p>rendered table</p>"),
                     doc("XML", "FilingSummary.xml", "<xml/>"),
                     doc("EX-101.SCH", "a-20260630.xsd", "<schema/>"),
                     doc("EXCEL", "Financial_Report.xlsx", "begin 644 x\n`\nend"),
                     doc("XML", "a-10k_htm.xml", f"<XML>\n{INSTANCE}\n</XML>"))
    res = L.process_submission(raw, F10K)
    names = [n for n, *_ in res["docs"]]
    assert names == ["0000000000-26-000001_2026-09-01_10K.txt.gz",
                     "0000000000-26-000001_2026-09-01_10K_EX211.txt.gz",
                     "0000000000-26-000001_2026-09-01_10K_EX991.txt.gz"]
    assert res["docs"][1][3] == "Subsidiaries: Foo LLC"
    assert res["xbrl"].startswith(b"<?xml") and b"us-gaap:Revenues" in res["xbrl"]
    assert not res["errors"]


def test_instance_is_kept_only_for_periodic_reports():
    raw = submission(doc("8-K", "a-8k.htm", "<p>Item 2.02</p>"), doc("XML", "a-8k_htm.xml", f"<XML>{INSTANCE}</XML>"))
    res = L.process_submission(raw, dict(F10K, form="8-K"))
    assert res["xbrl"] is None and len(res["docs"]) == 1


def test_a_filing_without_text_is_held_with_a_note():
    raw = submission(doc("GRAPHIC", "chart.jpg", "begin 644 chart.jpg\n`\nend"))
    res = L.process_submission(raw, dict(F10K, form="SD"))
    assert res["note"] == "no text documents"
    assert "GRAPHIC chart.jpg" in res["docs"][0][3]


# ---------------------------------------------------------------- uudecode + PDF
def test_uudecode_round_trips_and_ignores_the_pdf_wrapper():
    data = bytes(range(256)) * 3
    assert L.uudecode(uuencode(data, "x.pdf")) == data


def test_uudecode_survives_trailing_garbage_on_a_line():
    enc = binascii.b2a_uu(b"hello world").decode().rstrip("\n") + "   junk"
    assert L.uudecode(f"begin 644 a\n{enc}\n`\nend") == b"hello world"


def test_pdf_in_a_submission_becomes_text():
    pytest.importorskip("pypdf")
    raw = submission(doc("CORRESP", "letter.htm", "<p>Cover letter</p>"),
                     doc("CORRESP", "letter.pdf", uuencode(tiny_pdf("Hello library"), "letter.pdf")))
    res = L.process_submission(raw, dict(F10K, form="CORRESP"))
    assert len(res["docs"]) == 2
    assert "Hello library" in res["docs"][1][3]


# ---------------------------------------------------------------- insider forms
def test_form4_becomes_one_line_per_transaction_and_keeps_its_xml():
    raw = submission(doc("4", "wk-form4_1.xml", "<XML>\n" + FORM4.decode() + "\n</XML>"),
                     doc("EX-24", "poa.txt", "Power of attorney"))
    f = dict(acc="0000000000-26-000009", form="4", date="2026-09-03", report="")
    res = L.process_submission(raw, f)
    assert res["docs"][0][3] == ("0000000000-26-000009 4 filed 2026-09-03 | Doe Jane (Officer, CFO) | "
                                 "S 2026-09-01 D 1000 @ 250.5 -> 5000 D | Common Stock")
    assert res["raw"].startswith(b"<?xml") and b"ownershipDocument" in res["raw"]
    assert res["docs"][1][3] == "Power of attorney"


def test_save_filing_writes_text_xbrl_and_raw(tmp_path):
    raw = submission(doc("4", "f4.xml", "<XML>" + FORM4.decode() + "</XML>"))
    f = dict(acc="0000000000-26-000009", form="4", date="2026-09-03", report="")
    e = L.save_filing(tmp_path, f, L.process_submission(raw, f))
    assert e["raw"] == "forms/0000000000-26-000009.xml.gz"
    assert gzip.decompress((tmp_path / e["raw"]).read_bytes()).startswith(b"<?xml")
    with gzip.open(tmp_path / e["files"][0]["file"], "rt") as fh:
        assert "Doe Jane" in fh.read()


# ---------------------------------------------------------------- EDGAR's list, completeness, only-new
def sub_json(rows, files=()):
    return {"filings": {"recent": {"form": [r[0] for r in rows], "filingDate": [r[1] for r in rows],
                                   "accessionNumber": [r[2] for r in rows], "reportDate": [""] * len(rows)},
                        "files": list(files)}}


def test_window_rows_merges_older_pages_only_when_they_reach_the_window():
    sub = sub_json([("4", "2026-09-01", "a1"), ("10-Q", "2026-08-01", "a2")],
                   files=[{"name": "p1.json", "filingFrom": "2023-01-01", "filingTo": "2025-12-31"},
                          {"name": "p2.json", "filingFrom": "2010-01-01", "filingTo": "2022-12-31"}])
    pages = {"p1.json": sub_json([("425", "2025-01-02", "b1"), ("ARS", "2023-06-01", "b2"),
                                  ("10-Q", "2026-08-01", "a2")])["filings"]["recent"]}
    asked = []

    def load(name):
        asked.append(name)
        return pages.get(name)
    rows = L.window_rows(sub, "2023-09-25", load)
    assert asked == ["p1.json"]                                     # p2 ends before the window: not fetched
    assert [r["acc"] for r in rows] == ["a1", "a2", "b1"]           # b2 is before the window; a2 once


def test_window_rows_refuses_an_unreadable_page():
    sub = sub_json([("4", "2026-09-01", "a1")], files=[{"name": "p1.json", "filingTo": "2025-12-31"}])
    with pytest.raises(RuntimeError):
        L.window_rows(sub, "2023-09-25", lambda n: None)


def test_completeness_counts_edgar_against_saved():
    rows = [dict(acc=a) for a in ("a1", "a2", "a3")]
    c = L.completeness(rows, {"a1": {}, "a3": {}, "zz": {}}, failures=[{"acc": "a2"}])
    assert (c["edgar_filings"], c["saved_filings"], c["missing"], c["failures"], c["complete"]) == \
        (3, 2, ["a2"], 1, False)
    assert L.completeness(rows, dict.fromkeys(["a1", "a2", "a3"]))["complete"]


def test_plan_fetch_takes_only_new_accessions_and_drops_the_expired():
    rows = [dict(acc="new"), dict(acc="old1")]
    todo, keep, drop = L.plan_fetch(rows, {"old1": {"acc": "old1"}, "expired": {"acc": "expired"}})
    assert [r["acc"] for r in todo] == ["new"]
    assert list(keep) == ["old1"] and drop == ["expired"]
    assert not L.needs_update(rows, {"new", "old1"}, {"asset": "x"})
    assert L.needs_update(rows, {"old1"}, {"asset": "x"})
    assert L.needs_update(rows, {"new", "old1"}, None)


# ---------------------------------------------------------------- a run, twice, against a local "release"
def fake_fetch(calls):
    def fetch(cik, f):
        calls.append(f["acc"])
        if f["acc"].endswith("bad"):
            return None, "complete submission file not fetched"
        raw = submission(doc(f["form"], "main.htm", f"<p>{f['form']} {f['acc']}</p>"))
        return L.process_submission(raw, f), None
    return fetch


def asset_manifest(store, cik):
    with tarfile.open(fileobj=io.BytesIO(store.get(f"{cik}.tar.gz")), mode="r:gz") as t:
        return json.load(t.extractfile(f"{cik}/manifest.json")), t.getnames()


def test_run_fetches_everything_once_then_only_the_new(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "WORK", tmp_path / "work")
    store = L.LocalStore(tmp_path / "release")
    calls = []
    monkeypatch.setattr(L, "fetch_filing", fake_fetch(calls))
    monkeypatch.setattr(L, "window_start", lambda *a, **k: "2023-09-25")
    today = [("4", "2026-09-01", "0001-26-3"), ("425", "2026-05-01", "0001-26-2"), ("ARS", "2024-03-01", "0001-24-1"),
             ("10-K", "2023-01-01", "0001-23-0")]                                     # the last is outside the window
    subs = {7: sub_json(today)}
    uni = [dict(cik=7, ticker="CTAS", name="Cintas", mcap=8e10)]
    changes = []
    stats = L.run(uni, changes, subs.get, lambda n: None, full=True, store=store)
    assert sorted(calls) == ["0001-24-1", "0001-26-2", "0001-26-3"]
    man, names = asset_manifest(store, 7)
    assert (man["edgar_filings"], man["saved_filings"], man["complete"]) == (3, 3, True)
    assert man["forms"] == {"4": 1, "425": 1, "ARS": 1}
    assert "7/manifest.json" in names and "7/0001-26-2_2026-05-01_425.txt.gz" in names
    assert stats["totals"]["complete"] == 1 and not stats["gaps"]
    assert changes == []                                            # a company's first fill is not "new filings"
    idx = json.loads(store.get("index.json"))
    assert idx["companies"]["7"]["asset"] == "7.tar.gz"

    # next night: one new filing, one that failed, and the oldest leaves the window
    calls.clear()
    monkeypatch.setattr(L, "window_start", lambda *a, **k: "2024-06-01")
    subs[7] = sub_json([("8-K", "2026-09-20", "0001-26-4"), ("4", "2026-09-19", "0001-26-bad")] + today)
    stats = L.run(uni, changes, subs.get, lambda n: None, full=True, store=store)
    assert sorted(calls) == ["0001-26-4", "0001-26-bad"]            # only what is not saved yet
    man, names = asset_manifest(store, 7)
    assert [f["acc"] for f in man["filings"]] == ["0001-26-4", "0001-26-3", "0001-26-2"]
    assert (man["edgar_filings"], man["saved_filings"], man["complete"]) == (4, 3, False)
    assert man["failures"][0]["acc"] == "0001-26-bad"
    assert not any("0001-24-1" in n for n in names)                  # left the window, dropped
    assert [c["accession"] for c in changes] == ["0001-26-4"]
    assert stats["gaps"][0]["ticker"] == "CTAS" and stats["gaps"][0]["failures"] == 1
    assert any("CTAS" in line for line in L.report_lines(stats))

    # a third night with nothing new opens nothing but retries the failure only
    calls.clear()
    L.run(uni, changes, subs.get, lambda n: None, full=True, store=store)
    assert calls == ["0001-26-bad"]


def test_unchanged_company_is_not_downloaded_or_replaced(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "WORK", tmp_path / "work")
    monkeypatch.setattr(L, "window_start", lambda *a, **k: "2023-09-25")
    calls = []
    monkeypatch.setattr(L, "fetch_filing", fake_fetch(calls))
    store = L.LocalStore(tmp_path / "release")
    subs = {7: sub_json([("10-Q", "2026-08-01", "0001-26-1")])}
    uni = [dict(cik=7, ticker="X", name="X", mcap=1)]
    L.run(uni, [], subs.get, lambda n: None, full=True, store=store)

    class Watch(L.LocalStore):
        def get(self, name):
            assert name != "7.tar.gz", "an unchanged company's asset was downloaded"
            return super().get(name)

        def put(self, path):
            assert not str(path).endswith("7.tar.gz"), "an unchanged company's asset was replaced"
            return super().put(path)
    stats = L.run(uni, [], subs.get, lambda n: None, full=True, store=Watch(tmp_path / "release"))
    assert stats["unchanged"] == 1 and stats["updated"] == 0


def test_budget_defers_and_the_gap_shows(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "WORK", tmp_path / "work")
    monkeypatch.setattr(L, "window_start", lambda *a, **k: "2023-09-25")
    monkeypatch.setattr(L, "MAX_NEW", 1)
    calls = []
    monkeypatch.setattr(L, "fetch_filing", fake_fetch(calls))
    store = L.LocalStore(tmp_path / "release")
    subs = {7: sub_json([("10-Q", "2026-08-01", "0001-26-1"), ("10-Q", "2026-05-01", "0001-26-0")])}
    stats = L.run([dict(cik=7, ticker="X", name="X", mcap=1)], [], subs.get, lambda n: None, full=False, store=store)
    assert len(calls) == 1
    assert stats["gaps"][0]["deferred"] == 1 and stats["gaps"][0]["saved"] == 1
