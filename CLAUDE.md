# How work is done in this repo

Read this before doing anything. It is loaded into every session automatically, which is why the
rule lives here rather than in a document someone has to remember to open.

## Do this first, before anything else

```
mkdir -p ../.claude && cp .claude/settings.json ../.claude/settings.json
```

That arms the hook which refuses to run the suite here. It is idempotent and takes effect
immediately — no restart — and it needs running at the START OF EVERY SESSION, because the
container is ephemeral and nothing else installs it.

**Why the copy.** Claude Code reads project settings from the project root. Run inside this repo
the root IS the repo and `.claude/settings.json` works as it stands. But a remote session can clone
this repo beside another (today `fmp`) as SIBLINGS, so the root is their parent and this file sits
one directory below the level that is ever read. Until the copy existed the guard fired in no remote
session, nothing reported it, and the only reason no harm came of it is that `pytest` was not
installed in that particular container.

**Proving it worked:** run `pytest --version`. A refusal is the guard working.

## CI verifies. This session does not.

**Never report that anything passes on the strength of a command run in this session.** The only
statement of whether the build works is a green run on GitHub. A sandbox result is a hypothesis.

The stakes are high because a live autopilot in `fmp` acts on these files, and because **this build overwrites every company
file and PRUNES any it does not rewrite.** `sec.yml` proves the builder before it touches `data/`,
and on 10 Sep 2026 that gate ran no tests at all for sixteen hours: a line ended
`tests/test_sp500.py \\` instead of `\`, bash read `\\` as an escaped literal backslash rather than
a line continuation, pytest was handed `\` as a path and exited 4 having run nothing, and `bash -e`
killed the step. The YAML was valid throughout. Only the shell inside it was wrong.

Nothing reported it because no build had run since. `tests/test_workflows.py` now fails on any line
ending that way.

## What that means in practice

**Allowed, and necessary — INVESTIGATION.** Reading `data/companies/<cik>.json`, checking which tag
a concept resolved to, comparing a build against an earlier one through `git worktree`. Most real
findings come from this. The answer is evidence about **data**, never a claim that anything passes.

**Allowed — drafting checks under about a minute.** A syntax parse, one fast test file. A spelling
check on the way to a commit, never proof.

**Not allowed — reporting a pass count from this session**, or merging to `main` because something
looked green locally. Push the branch, read the CI run, then merge.

**Not allowed — probing www.sec.gov from here.** The sandbox has no real contact string, and a
placeholder user-agent against sec.gov is exactly what the SEC asks people not to send. Dispatch
the workflow instead, so the real `SEC_USER_AGENT` secret is used.

## The loop

1. Decide the change here.
2. Write it: code, tests, and the reasoning in the commit message.
3. Push to the working branch.
4. **Read the CI run.** If red, fix and push again.
5. Merge to `main` only once CI is green.
6. Dispatch `sec.yml` when the change needs to reach `data/`. Nothing in a commit affects the
   dataset until a build runs.

## Standing constraints

- `SEC_USER_AGENT` is a repo secret. Never hardcode it, never print it, never send it anywhere but
  sec.gov.
- **Never delete files in `data/` by hand.** The build script owns that directory.
- **Do not rename, remove, or change the meaning of any existing key.** Other tasks read these files
  by field name. Adding a field, or a new value for an existing flag, is fine.
- If a test finds a builder bug, **stop and report it** rather than working around it.
- A `checks` flag is a pointer at something worth checking, not proof that a figure is wrong. The
  floor in `top_line_repair` is deliberately a superset: net income above revenue is what a large
  one-off gain looks like, not an impossibility. See that function's docstring.

## Who reads this data

**One reader: the owner's `fmp` repo** — its live "ownership autopilot" in `fmp/owner/`, which buys
and sells real money in a brokerage account without asking on each order. (`robinhood-book`, the
reader this section used to describe, was RETIRED 24 Sep 2026; the old text is in git history.)
What it reads, from a sibling checkout `../sec-dataset`:

- `data/companies/<CIK>.json` — `screen.py` (the quality screen), `mathprice.py` (fair price per
  share: operating cash flow, `capex`, `capitalized_software`, `payments_for_intangibles`,
  `stock_comp`, net income, cash, investments and `total_debt`, `shares_diluted_adj` / `_filled`, and
  the `checks` block) and `backtest_fair.py` (point-in-time: the `*_as_filed` values and their `_filed` dates,
  every annual row and the dead filers). Treat every existing key as read.
- `data/tickers.json` — `watch.py` and `mathprice.py` map tickers to CIKs through it.
- `data/events/<CIK>.json` — `screen.py` (8-K item red flags) and `watch.py` (a new 10-Q/10-K or
  material 8-K since a company was last read triggers a re-read).
- `data/manifest.json`, `data/events_recent.json` and `data/cik_overrides.json` are read by the
  builders here and kept.

**A field that silently changes meaning here changes what fmp's live autopilot buys.** A share
count on the wrong split basis moves a fair price, and the autopilot buys at up to 2x fair price; a
dropped 8-K item code hides a red flag. Adding a field is safe; changing one is not.

**Do not change the data-shaping constants** — `ANNUAL_YEARS` (as much annual history as
companyfacts holds), `PUBLISH_SILENT_YEARS` (dead filers are kept, marked `active: false`, so a
backtest can see the companies that failed), `ACTIVE_SILENT_YEARS`, `SHARE_WINDOW`. `fmp`'s
backtests depend on the long history and on the dead filers; the reasoning is in the comments
beside each constant and in NOTES.md.

**Removed 24 Sep 2026, because only the retired reader or finished research used them:** the
insider Form 4 feed, the S&P 500 10-K text build, the tag-probe tool, the S&P 500 constituent list
(`data/sp500.json`) and the never-pruned `data/events_history/`. NOTES.md (24 Sep 2026) names the
last commit that had each. Do not bring one back without a reader in `fmp` that needs it.
