"""CLAUDE.md must exist and must still carry the rules that keep this build safe.

Claude Code loads CLAUDE.md into every session automatically, which is the only reason a rule there
is hard to forget. A test that merely checked the file existed would be satisfied by an empty one,
so these check the clauses that actually change behaviour — each one attached to something that
went wrong on 10 Sep 2026.
"""
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLAUDE = ROOT / "CLAUDE.md"


def test_claude_md_exists():
    assert CLAUDE.is_file(), "CLAUDE.md is gone — it is the only file every session loads. Restore it."


@pytest.mark.parametrize("clause,why", [
    ("CI verifies", "the rule itself"),
    ("PRUNES", "that a build deletes company files it does not rewrite — why the gate matters"),
    ("sec.gov", "that this sandbox must not probe the SEC with a placeholder user-agent"),
    ("Never delete files in `data/`", "the build script owns that directory"),
    ("change the meaning of any existing key", "other tasks read these files by field name"),
    ("stop and report it", "a builder bug is reported, never worked around"),
])
def test_the_rules_still_say_what_they_have_to(clause, why):
    assert clause in CLAUDE.read_text(), f"CLAUDE.md no longer states: {why}"


def test_the_gate_failure_is_recorded_with_the_rule():
    """Sixteen hours with a pre-flight gate that ran zero tests is the evidence for the rule. Keep
    them together, or the rule reads as bureaucracy rather than as a scar."""
    text = CLAUDE.read_text()
    assert "test_sp500.py" in text, "the concrete instance is gone"
    assert "exited 4" in text or "exit 4" in text, "the failure mode is gone"


def test_it_names_the_consumer_of_this_data():
    """A dataset with no stated consumer invites a 'harmless' field rename."""
    assert "robinhood-book" in CLAUDE.read_text()
