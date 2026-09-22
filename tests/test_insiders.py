"""The Form 4 insiders feed: index parsing, the ownershipDocument parser, merging and clusters.

No network: every input is a synthetic document shaped like the SEC's Form 4 XML."""
from datetime import date

import build_sec_insiders as bi

IDX = """Form Type   Company Name                                                  CIK         Date Filed  File Name
---------------------------------------------------------------------------------------------------------------------------------------------
4           ACME CORP                                                     1000001     20260921    edgar/data/1000001/0001234567-26-000001.txt
4           Doe Jane                                                      2000002     20260921    edgar/data/2000002/0001234567-26-000001.txt
4/A         ACME CORP                                                     1000001     20260921    edgar/data/1000001/0001234567-26-000009.txt
8-K         ACME CORP                                                     1000001     20260921    edgar/data/1000001/0001234567-26-000002.txt
"""


def doc(trades, owners=(("Doe Jane", "0002000002", "1", "1", "0", "Chief Executive Officer"),)):
    own = "".join(f"""<reportingOwner><reportingOwnerId><rptOwnerCik>{c}</rptOwnerCik><rptOwnerName>{n}</rptOwnerName></reportingOwnerId>
      <reportingOwnerRelationship><isDirector>{d}</isDirector><isOfficer>{o}</isOfficer><isTenPercentOwner>{t}</isTenPercentOwner>
      <officerTitle>{ti}</officerTitle></reportingOwnerRelationship></reportingOwner>""" for n, c, d, o, t, ti in owners)
    rows = "".join(f"""<nonDerivativeTransaction><securityTitle><value>Common Stock</value></securityTitle>
      <transactionDate><value>{dt}</value></transactionDate>
      <transactionCoding><transactionFormType>4</transactionFormType><transactionCode>{code}</transactionCode></transactionCoding>
      <transactionAmounts><transactionShares><value>{sh}</value></transactionShares><transactionPricePerShare><value>{px}</value></transactionPricePerShare>
      <transactionAcquiredDisposedCode><value>{ad}</value></transactionAcquiredDisposedCode></transactionAmounts>
      <postTransactionAmounts><sharesOwnedFollowingTransaction><value>{after}</value></sharesOwnedFollowingTransaction></postTransactionAmounts>
      <ownershipNature><directOrIndirectOwnership><value>D</value></directOrIndirectOwnership></ownershipNature></nonDerivativeTransaction>"""
                   for code, dt, sh, px, ad, after in trades)
    return f"""<SEC-DOCUMENT>header
<XML>
<?xml version="1.0"?>
<ownershipDocument><documentType>4</documentType>
<issuer><issuerCik>0001000001</issuerCik><issuerName>Acme Corp</issuerName><issuerTradingSymbol>acme</issuerTradingSymbol></issuer>
{own}<nonDerivativeTable>{rows}</nonDerivativeTable></ownershipDocument>
</XML></SEC-DOCUMENT>"""


def test_index_keeps_form_4_only_and_dedupes_the_issuer_and_owner_listings():
    got = bi.form4_paths(IDX)
    assert got == {"0001234567-26-000001": "edgar/data/2000002/0001234567-26-000001.txt"}


def test_purchases_and_sales_are_kept_and_grants_dropped():
    issuer, trades = bi.parse_form4(doc([("P", "2026-09-19", "1000", "12.50", "A", "5000"),
                                         ("A", "2026-09-19", "300", "0", "A", "5300"),
                                         ("S", "2026-09-20", "200", "13", "D", "5100")]), "acc-1", "2026-09-21")
    assert issuer == {"cik": 1000001, "name": "Acme Corp", "ticker": "ACME"}
    assert [t["code"] for t in trades] == ["P", "S"]
    p = trades[0]
    assert p["shares"] == 1000 and p["price"] == 12.5 and p["value"] == 12500
    assert p["owned_after"] == 5000 and p["direct"] == "D" and p["date"] == "2026-09-19"
    assert p["roles"] == ["director", "officer"] and p["title"] == "Chief Executive Officer"
    assert p["owner_cik"] == "2000002" and p["row"] == 0 and trades[1]["row"] == 2


def test_true_false_flags_are_read_like_ones_and_zeros():
    _, trades = bi.parse_form4(doc([("P", "2026-09-19", "10", "1", "A", "10")],
                                   owners=(("Fund LP", "0003000003", "false", "false", "true", ""),)), "a", "2026-09-21")
    assert trades[0]["roles"] == ["ten_percent_owner"]


def test_a_filing_without_an_ownership_document_yields_nothing():
    assert bi.parse_form4("<SEC-DOCUMENT>no xml</SEC-DOCUMENT>", "a", "2026-09-21") == ({}, [])


def test_merge_replaces_a_reread_row_and_keeps_the_rest():
    old = [{"accession": "a", "row": 0, "filed": "2026-09-01", "date": "2026-08-30", "shares": 1}]
    new = [{"accession": "a", "row": 0, "filed": "2026-09-01", "date": "2026-08-30", "shares": 2},
           {"accession": "b", "row": 1, "filed": "2026-09-05", "date": "2026-09-04", "shares": 3}]
    got = bi.merge_trades(old, new)
    assert [(t["accession"], t["shares"]) for t in got] == [("b", 3), ("a", 2)]


def test_a_cluster_needs_two_distinct_director_or_officer_buyers():
    base = {"code": "P", "filed": "2026-09-15", "cik": 1, "ticker": "X", "name": "X", "value": 1000.0}
    rows = [{**base, "owner_cik": "10", "roles": ["director"]},
            {**base, "owner_cik": "10", "roles": ["director"]},                       # same person twice
            {**base, "owner_cik": "20", "roles": ["ten_percent_owner"]},              # a fund, not an insider
            {**base, "cik": 2, "owner_cik": "30", "roles": ["officer"]},
            {**base, "cik": 2, "owner_cik": "40", "roles": ["director", "officer"]},
            {**base, "cik": 2, "owner_cik": "50", "roles": ["officer"], "code": "S"},  # a sale
            {**base, "cik": 2, "owner_cik": "60", "roles": ["officer"], "filed": "2026-07-01"}]  # too old
    got = bi.clusters(rows, date(2026, 9, 22))
    assert [(c["cik"], c["buyers"], c["value"]) for c in got] == [(2, 2, 2000.0)]
