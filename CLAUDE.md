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
the root IS the repo and `.claude/settings.json` works as it stands. But a remote session clones
this repo and `robinhood-book` as SIBLINGS, so the root is their parent and this file sits one
directory below the level that is ever read. It fired in neither remote session for as long as
they have existed, nothing reported it, and the only reason no harm came of it is that `pytest`
was not installed in that particular container.

If `robinhood-book` is also checked out, prefer its installer — it writes a guard carrying the
evidence from both repos, and is itself tested:

```
python ../robinhood-book/tools/install_guard.py
```

**Proving it worked:** run `pytest --version`. A refusal is the guard working.

## CI verifies. This session does not.

**Never report that anything passes on the strength of a command run in this session.** The only
statement of whether the build works is a green run on GitHub. A sandbox result is a hypothesis.

The stakes here are higher than in the book repo, because **this build overwrites every company
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

`loosygoosie/robinhood-book` scores and values the S&P 500 from these files and acts on the result
through a live brokerage account. A field that silently changes meaning here changes what gets
bought there. (It SCREENED, until 11 Sep 2026 — the screens were deleted and the word is wrong now:
nothing is excluded for being a bad business, only for being unmeasurable.)

**WHAT DECIDES OWNABILITY THERE CHANGED AGAIN ON 14 Sep 2026, and this section said the opposite for
two days.** It read: *two fields here now decide whether a company can be owned at all* —
`deposits` / `total_assets` and `premiums_earned` / `revenue`, which identified banks and insurers so
that they and REITs could be held out of a six-dimension score that cannot read them honestly. That
whole model was DELETED. The thirteen-group taxonomy, the six dimensions, the bar and
`robinhood-book/claude/group-overrides.json` all went, and **nothing over there decides eligibility
today** — a company is simply unmeasured when its figures cannot be read, which is the same idea
without a taxonomy in front of it.

So the pressure on the identification tags is OFF for now, and the reason to fix them is unchanged
and better: `sec-dataset` NOTES 16 records that neither `premiums_earned` nor `loss_reserves`
resolves a tag for Berkshire Hathaway, the largest insurer in the index. **A field that reports
nothing for the biggest filer in its category is a measurement failure whether or not a consumer is
currently reading it**, and the replacement design — a READABILITY gate over seven ten-year measures,
in `robinhood-book/claude/clean-slate.md` — will read exactly these markers when it is built.

What the new consumer reads TODAY, and what this build was changed on 14 Sep 2026 to supply: as
much annual history as companyfacts holds (`ANNUAL_YEARS`), as-filed values for sixteen items across
flows and the balance sheet, `restated` per row, and `total_debt` summed from its components. Those
four are load-bearing now in a way the group markers are not.

**`ANNUAL_YEARS` WAS A CEILING AS WELL AS A FLOOR, and only the floor was ever argued for.** It read
12 — the consumer's ten-year window plus two — and the truncation is `[-ANNUAL_YEARS:]`, so every
build threw away every year past the twelfth. Nothing said so, because the test bound only the lower
side. It cost nothing while the consumer wanted to READ a ten-year measure; it blocks
`robinhood-book` #48 outright once the consumer wants to VALIDATE one, because twelve years of
history admits exactly ONE formation date and leaves about two and a half years of forward returns.
Raised to 25 on 14 Sep 2026 so the SOURCE decides the depth, and `tests/test_normaliser.py` now
fails if the cap ever comes within two years of what the calendar says companyfacts could hold.

**THE BUILD HAS RUN, and this section said it had not for as long as it took to dispatch one.** It
read: *"every company file still carries twelve rows and every figure derived from one is a
twelve-year figure."* True when written, false the moment `sec.yml` finished. The rule behind it is
unchanged and still worth keeping in mind — nothing in a commit reaches `data/` until a build runs —
but the state it described is gone. Build `024d4f7f9`, 14 Sep 2026: median depth **11**, mode **17**
(FY2009-FY2025, the XBRL mandate window exactly), deepest 25, `data/companies` 218 MB to 246 MB.
3,927 of 7,410 filers never came near the old cap at all.

**AND THE CAP STILL BINDS FOR 38 FILERS, which is not what raising it predicted.** That change said
a real filer "reaches back somewhere around 2007". Rows turn up from **1987** — development-stage
companies, which before ASC 915 was withdrawn in 2015 reported cumulative-since-inception amounts
under a context starting at inception, so a 2013 filing carries a "FY1997" period holding four
fields and no revenue. Every filer at the cap is a shell of that kind, so truncating there discards
an artefact rather than history. That is luck, not design, and `XBRL_REACHES_BACK_TO` must NOT be
lowered to 1987 to match the observed minimum — it is what a REAL filer can reach, and its only job
is to keep the anti-ceiling assertion strict.

**WHAT IT COST THE CONSUMER, because a build that changes nothing over there is the claim to
distrust.** `robinhood-book` predicted no figure would move — every measure windows to the last ten
rows — and 731 of its 734 composites moved while membership held exactly. The cause was on its side,
exposed rather than created here: `persistence.effective_tax_rate` read the whole row list, so three
measures documented as ten-year were not. At twelve published years it had been ACCIDENTALLY almost
windowed. Fixed at `4d8d21e` there, with its dataset pin bumped to this build and its coverage
baseline regenerated in the same commit.

**What that system is FOR is written down** in `robinhood-book/VISION.md` — the intents it was
designed to serve, in its owner's words, each marked BUILT, PARTIAL or OPEN. Fields published here
and not yet read there: where a company's money actually goes (`capex`, `buybacks`,
`dividends_paid`, `acquisitions`, `stock_comp` — intent 5, and the candidate for a seventh
dimension), and `data/events_recent.json`, the 90-day filing feed, which is proposed as the pre-buy
event check and has never been read. Worth reading before deciding a field here is unused — it may
be unused only so far.
