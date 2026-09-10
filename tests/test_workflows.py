r"""Guards on the workflow files themselves.

The build's pre-flight gate — the step that proves the builder before it overwrites and prunes
every company file — was silently disabled for sixteen hours by one character. A line in sec.yml
ended `tests/test_sp500.py \\` instead of `\`. Bash reads `\\` as an escaped literal backslash,
not a line continuation, so pytest was handed `\` as a path, exited 4 having run nothing, and
`bash -e` killed the step there. No build ran with it, so nothing ever reported the breakage:
it would have surfaced as a red run on the next Sunday build, three days later.

A YAML linter would not have caught it — the YAML is valid. Only the shell inside it is wrong.
"""
import pathlib
import re

import pytest

WORKFLOWS = sorted((pathlib.Path(__file__).resolve().parent.parent / ".github/workflows").glob("*.yml"))


def test_there_are_workflows_to_check():
    """Without this the two tests below pass vacuously if the glob ever stops matching."""
    assert len(WORKFLOWS) >= 4, [w.name for w in WORKFLOWS]


@pytest.mark.parametrize("wf", WORKFLOWS, ids=lambda w: w.name)
def test_no_line_ends_in_an_escaped_backslash(wf):
    r"""`\\` at end of line ends the command instead of continuing it, and the next line runs as
    its own command. Every real continuation in these files is a single trailing backslash."""
    for n, line in enumerate(wf.read_text().splitlines(), 1):
        stripped = line.rstrip()
        if stripped.endswith("\\") and not stripped.endswith("\\\\"):
            continue                                    # a normal continuation
        assert not stripped.endswith("\\\\"), (
            f"{wf.name}:{n} ends in an escaped backslash, which breaks the command:\n  {stripped}")


@pytest.mark.parametrize("wf", WORKFLOWS, ids=lambda w: w.name)
def test_every_gated_test_file_exists(wf):
    """A gate naming a file that has been renamed away fails the build with 'not found', which
    reads like a broken workflow rather than a stale list. Cheap to pin."""
    root = wf.resolve().parent.parent.parent
    for path in re.findall(r"tests/test_\w+\.py", wf.read_text()):
        assert (root / path).is_file(), f"{wf.name} gates on {path}, which does not exist"
