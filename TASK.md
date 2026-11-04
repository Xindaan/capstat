# TASK.md — capstat

## Doing

<!-- max 3 -->

- (Doing is clear. What is left of the old T-0018 split: T-0036 increment 3, a
  code-letter lookup, only worth revisiting if something real needs it; and
  T-0038, parked. **T-0041 is finished** -- the study file is wired on all three
  hand-entered pages, and `/` is deliberately without one because its input is
  an uploaded CSV. This block said otherwise until 2026-09-02, three weeks after
  the work landed; a stale Doing block is the one that costs a session.)

## Backlog
- **Third review 2026-10-01 (Opus 5.5 orchestrating nine Sonnet reviewers and
  four Opus verification gates; source read plus execution, a live browser
  run, and 589 hand-made mutants including a 65-mutant warning-code sweep).**
  173 raw findings, 155 after merging duplicates. Every finding outside the
  mutation run that a reviewer rated medium or higher (52) went to an
  adversarial gate, plus three lower ones: of those 55, 44 confirmed, 11
  narrowed, none refuted. The 16 medium-or-higher mutation findings carry
  their reproduction by construction (a surviving mutant under a green suite).
  Checked a second time in the orchestrating session -- by execution: CAP-1,
  CAP-3, MSA-2, SAMP-1, SAMP-2, TQ-3 and the T-0095 file; by derivation or code
  reading: CAP-2, CHART-2, CHART-6, MSA-1, SAMP-3. Filed as T-0095..T-0115,
  grouped by error class rather than one ID per finding; the finding IDs
  (CAP-, CHART-, MSA-, SAMP-, API-, WEB-, UX-, ARCH-, TQ-) are the reviewers'
  and are quoted so the evidence can be traced (kept locally, outside git, in
  `tmp/review-2026-10-01/`). Measured at HEAD b55623a: ruff, ruff format, mypy
  --strict, tsc and eslint clean; 677 Python tests at 100 % coverage; 79
  vitest. Mutation kill rate 66 % (71 % without equivalent mutants; the
  agent's two tallies give 509 and 524 mutants for that figure) -- the suite is
  broad, and thinner than the coverage figure suggests.
  **T-0095..T-0100, T-0102, T-0105, T-0106 are done** (see Done).

- T-0118 (2026-11-04) **Finish the integration of the 2026-10-21 agent work.**
  * **Needs the maintainer (Codex review on PR #56, P1):** T-0097's
    calibrated rounding test can switch a rejected sample to the normal path,
    but it has no published reference case (`normality.yaml` says it is
    validated by simulation only). `AGENTS.md` says a method without a
    reference-validated test does not ship. Options: (a) keep the routing and
    record an explicit exception to the rule for simulation-validated
    calibrations; (b) keep only the ValueError for fewer than three distinct
    values and switch the re-routing off until a reference case exists.
  * Codex review fixes on PR #56 (2026-11-04): re-upload crash after a
    subgroup size (workspace `grouping!`), RangeError in `yAxisExtent` and
    `histogram` on ~150k points.
  * Playwright on the integrated branch: 2 of 62 failed,
    `e2e/numbers.spec.ts:164` (T-0100) -- its `/ingest` mock lacked the `rows`
    field T-0102 made required, so `interiorGaps` threw. Mock fixed
    2026-11-04: 62/62. The class remains: mocked *responses* are not checked
    against `openapi.json` (T-0099 checks only request bodies); worth adding.
  * Uncommitted work left in three agent worktrees under `.claude/worktrees/`
    (all from 2026-10-21, not on any branch): `agent-acf0da0dcc7da2790`
    (impl-ingest) 2 files, +528 -- looks like T-0110 (placeholders, a column and
    cell cap, US-thousands lookalikes); `agent-ac3e00f2c11466d26` (impl-web-a)
    11 files, +269 -589, components and e2e specs; `agent-ade2915e78c774d2a`
    (impl-sampling) 4 files, +144 -- `_validation`/`acceptance_sampling`, likely
    SAMP-12. The fourth worktree (impl-nonnormal) is clean and merged. Decide
    per worktree: finish and commit, or drop. Removing a worktree discards
    its uncommitted changes.

- T-0101 **Results stay on screen after their inputs change.** WEB-4 / UX-1 /
  UX-4 on all four pages: editing a spec limit or a reading leaves the old
  verdict standing, unmarked. WEB-27: a response arriving after an edit
  overwrites the invalidation.

- T-0103 **Cpm -- needs a decision.** CAP-2: Cpm uses sigma_within (stated in
  the module docstring, pinned by a test asserting Cpm == Cp on target); on a
  drifting process capstat reports 3.43 where the NIST 6.1.6 estimator with the
  sample sd gives 1.06. NIST uses `s` for every index, so it does not settle
  within vs overall; Minitab files Cpm under overall capability (recalled, not
  checked here). CAP-3: an off-midpoint target goes into the symmetric formula
  -- measured Cpm 3.41 with Cpk 0.70 and 1.65 % beyond USL, where
  min(USL-T, T-LSL)/(3 tau) gives 0.68; a target outside the limits is
  accepted silently.
  **Decided 2026-10-07 (maintainer): sigma_overall.** Cpm moves to the
  performance family; an off-midpoint target uses min(USL-T, T-LSL)/(3 tau);
  a target outside [LSL, USL] is refused. Breaking (`fix(capability)!:`).

- T-0104 **What "in control" and "stable" mean -- needs a decision.**
  CHART-6: the pair verdict is location AND dispersion; the MR chart alone
  signals on 0.92 % of points of a stable process (P(|Z| > 2.606)), so a stable
  series reads "Out of control" 23 % of the time at N = 30 and 63 % at N = 100.
  CHART-9 / WEB-14: the badge ignores the run rules listed under it, and so do
  `stability()` and the CLI exit code. MSA-5: `stability()` -- 23 % false
  alarms on a stable gauge, 49 % detection of a 3-sigma drift, wording "the
  gage drifted" for any signal. CHART-7: one outlier counted as three points.
  One fix covers all of them; count it once.
  **Decided 2026-10-07 (maintainer): the switched-on run rules count.** Badge,
  `stability()` and `--fail-on-signal` include them; the wording names the
  chart that signalled instead of "the gage drifted"; the pair false-alarm
  rate is documented. Breaking.

- T-0107 **The switching-score fallback is not the conservative branch.**
  SAMP-3: with the tighter-AQL question unanswered every accepted lot scores
  +2, but for an Ac >= 2 plan a lot that would fail one step tighter resets the
  score to 0 -- so the fallback reaches reduced inspection earlier than the
  standard, while the docstring, docs and caveat call it the safe direction.
  Mitigated by `reduced_inspection_authorised` defaulting to off. SAMP-14:
  answering the question for an Ac <= 1 plan scores +3. SAMP-5: the
  reduced-not-authorised caveat names a cause that did not apply.

- T-0108 **Gage R&R results the user asked for are not shown.** MSA-1 / WEB-17
  / UX-7: the Tolerance input is sent, %Tolerance is computed and never
  rendered, and the verdict reads %Study Variation only -- a P/T of 31 % can sit
  under a green "good". MSA-3 (narrowed): only the average-and-range method
  flatters coarse-resolution data; ANOVA reacts correctly. MSA-4 (narrowed,
  documented design): linearity judges the slope only; AIAG's intercept and
  confidence-band rule (recalled) is not offered. MSA-6 / WEB-29: "No bias" in
  green for three readings.
  **Decided 2026-10-07 (maintainer), MSA-4:** add the intercept test (SE, t, p)
  and the confidence band to the linearity output; the verdict stays on the
  slope, with a caveat when the offset is significant. Not breaking.

- T-0109 **The web app hides or mangles what the core computed.** WEB-15 /
  UX-2: normality warnings (autocorrelation, tests disagree) never rendered --
  a trending series gets a green "Normal". WEB-16: no process mean, sigmas,
  Cpl/Cpu, Cpm on the capability panel. WEB-6: variance components at mm scale
  print as 0.00000. WEB-13: the print truncates the measurement data. UX-14
  (narrowed): emerald-600 and amber-600 text reach 3.65:1 and 3.20:1 on white
  (AA needs 4.5:1); the acceptance-sampling risk cards say nowhere what amber
  means. WEB-2 (histogram crash above ~120k values) fixed 2026-11-04 on
  PR #56, with the same class in `yAxisExtent`.

- T-0110 **Ingest robustness beyond T-0095.** API-16: locale handling is
  CSV-only and all-or-nothing. API-7: xlsx date and boolean columns arrive as
  measurement columns. API-5: `inf` cells come back as JSON null inside a
  `list[float]`. API-4 (narrowed): a small xlsx with one stray far-right cell
  needs gigabytes of RAM.

- T-0111 **Test-suite strength: what the mutants found.** Kill rate 66 % of
  509 mutants (71 % without equivalents). High: TQ-1 / CHART-10 (R, S and MR
  chart upper limits unpinned -- a x1.4 UCL passes all 677 tests); TQ-3 (the
  interaction-kept branch of Gage R&R: the only test has no operator effect,
  so var_operator is clamped to 0 and p*r -> o*r survives; re-measured here,
  the code itself is correct); TQ-12 (26 of 49 API wiring mutants survive --
  optional request fields can be dropped); TQ-13 (CLI output values largely
  unpinned). Medium: TQ-18 (59 of 65 warning codes, the T-0074 contract, can
  be renamed), TQ-4, TQ-5, TQ-7, TQ-8, TQ-10, TQ-15, TQ-19, TQ-22, TQ-23, TQ-27.

- T-0112 **Caveats the data would justify but nobody raises.** CHART-5: no
  autocorrelation check on I-MR / EWMA / CUSUM, though
  `descriptive.lag1_autocorrelation` exists. CAP-5 (narrowed): the
  short-series caveat fires below 20 while its own text cites AIAG's 25.
  CAP-8: Shapiro-Wilk beyond n = 5000 without a caveat. MSA-7: no small-study
  caution on Gage R&R.

- T-0113 **Release and CI hardening.** ARCH-4: Dependabot covers `uv` and
  Actions, not npm or Docker. ARCH-8: see T-0099. ARCH-14: the published wheel
  and sdist carry no LICENSE file (the copyright line is in METADATA, the
  permission text is not). ARCH-16: pytest does not fail on numpy
  RuntimeWarnings (one test fails with `-W error::RuntimeWarning`, see T-0097).
  ARCH-17 (narrowed) / ARCH-12: `main` is unprotected and `publish` does not
  ask whether CI passed on the tag; in practice every release PR from 0.4.0 to
  0.4.4 had green CI only because of the hand-made `uv.lock` commit -- so
  automating that stamp (T-0082) removes the one CI run on the release tree,
  and the two must be fixed together. OIDC token scoped to the whole job. ARCH-5: the declared numpy/scipy floors are never
  tested (9 test-side failures at the floor). ARCH-10: the release gates have
  no tests. ARCH-2: `apps/web/package-lock.json` still says 0.3.0.

- T-0114 **Documentation drift.** ARCH-6 (README status v0.2.1, `mkdocs serve`
  port), ARCH-7 (uploads over 1 MiB are spooled to disk; README and
  `docs/deployment.md:193` say never),
  ARCH-13 (API reference omits 26 of 87 exports, all of acceptance sampling),
  CHART-8 (run-rule false-alarm cost quoted as flagged-point share, not ARL;
  WE ARL0 measured 91.8), CHART-17 ("reproduced exactly"), CHART-13 (README on
  k-of-m causality), ARCH-15 (AGENTS.md forbids what PLAN.md lists as out of
  scope for v0.1, and acceptance sampling is built).

- T-0115 **For the maintainer, report only: the steering files are mostly
  history.** (ARCH-9.) TASK.md 2462 lines, STATE.md 774 lines against the
  shared convention (STATE: goal, 2-6 status bullets, 1-3 next actions). Open
  work is split between both files. Not acted on -- these files are the
  maintainer's.
  **STATE.md part done 2026-10-21:** rewritten as an 80-line snapshot up to
  `<!-- snapshot-ende -->` (shared rule `~/src/CLAUDE.md` §3/§5, decided by
  the maintainer); old text verbatim in `docs/state_archiv_2026-10-21.md`.
  TASK.md size stays open (portfolio-wide question, not decided yet).

- T-0116 **Dependabot backlog: 13 open alerts, 6 update PRs.** (2026-10-21,
  found while rewriting STATE.md.) `gh` showed 13 open alerts, high ones on
  `next` (x2), `vite` and `source-map-js`, and open PRs #47, #48, #50-#53
  (incl. next 16.3.8, #53). The T-0046 "zero alerts" state of 2026-08-16 no
  longer holds. Done when: the high alerts are closed (merged or dismissed
  with a reason) and the remaining PRs are merged or closed.

- **External review 2026-08-22 (Ox Alpha via OpenRouter, source read only, no
  execution).** Twelve findings; every cited site was re-read here and the four
  algorithmic/IO ones reproduced. One finding was wrong (see T-0062), the rest
  are T-0051..T-0061 below. The review had no access to `TASK.md`, `STATE.md`,
  data directories or build artefacts, so it argued from the code alone -- which
  is exactly why it found T-0051: a decision this file records as settled.
- ~~T-0051 **k-of-m run rules miss completed patterns**~~ -- **done 2026-08-23.**
  `_k_of_m_beyond` (`rules.py:172`) only emitted a violation when the *last
  point of the m-window* was itself beyond the threshold, so a pattern followed
  by quiet points produced no signal. Fixed by dropping that gate: the signal
  belongs on the last *qualifying* point, which `signal_at = max(w)` already
  derived. See `## Done`.
  **The scope is narrower than either the review or this entry first claimed,
  and the correction is the interesting part.** Measured, not argued: on 100,000
  simulated in-control points the fix changes *nothing* -- old and new agree to
  the last violation. An exhaustive differential over every sequence of length
  6 and 7 drawn from {below, inside, beyond} shows why: signals are only ever
  **added, never removed**, and the added signal always sits at point **m-2** --
  point 1 for the 2-of-3 rule, point 3 for the 4-of-5 rule.
  The reason is structural. If the last qualifying index `ik` is at least
  `m-1`, the window starting at `ik-m+1` exists, ends exactly on `ik`, and
  contains the whole pattern -- so the old gate caught it after all. The only
  unreachable case is a pattern completing *before a full window can end on
  it*, i.e. within the first `m-1` points of the series.
  So the real defect is: **a process that is already out of control when the
  chart starts does not signal.** That is a narrow window and a serious one --
  a new process on its first chart is precisely where the first alarm matters.
  It is not "these sequences never trigger", which is how the review put it and
  how this entry originally repeated it.
- ~~T-0052 **The chart panel reported "no violations" after a failed rules
  call**~~ -- **done 2026-08-23**: the rule run now carries its own outcome, and
  an empty violation list can only mean "the rules ran and found nothing". See
  `## Done`.
- ~~T-0053 **`design_single_sampling_plan` claimed no plan exists when one
  does**~~ -- **done 2026-08-23**: the doubling probe is clamped to the ceiling
  instead of being allowed to overshoot it. Also fixed a second, silent failure
  the review did not find -- plans that were valid but larger than necessary.
  See `## Done`.
- ~~T-0054 **The percentile path silently discarded `target`**~~ -- **done
  2026-08-23**: the path now says the target was not used and why. See `## Done`.
- ~~T-0055 **A corrupt study file crashed the page**~~ -- **done 2026-08-23**:
  `inputs` is read field by field against a per-page reader, and a reader is now
  a *required* prop rather than an option. See `## Done`.
- ~~T-0056 **`/ingest` buffered the whole upload before the size guard**~~ --
  **done 2026-08-23**: the body is read a chunk at a time and refused at the
  first chunk that crosses the limit. See `## Done`, and T-0063 for the larger
  hole this uncovered.
- ~~T-0057 **Result-card labels fell below WCAG AA**~~ -- **done 2026-08-23**:
  a measured `--muted` token replaces 51 uses of opacity steps that failed.
  See `## Done`.
- T-0082 **`uv.lock` keeps the old version of the workspace members after a
  release.** release-please stamps `0.3.0` into the two `pyproject.toml` files
  through `extra-files`, but nothing updates `uv.lock`, which records the
  version of each editable workspace member as well. After cutting 0.3.0 the
  lock still said `capstat-api 0.2.1` and `capstat-core 0.2.1`.
  Measured: it does **not** break CI -- `uv sync --frozen` succeeds either way,
  so this is latent rather than red. What it costs is a stray two-line diff on
  everyone's next `uv lock`, which is exactly the sort of thing that gets
  committed by accident inside an unrelated change.
  Corrected by hand for 0.3.0. Acceptance: the next release leaves the lock
  consistent without hand-editing -- either by teaching release-please to update
  `uv.lock` as an extra file, or by a release-time step that runs `uv lock` and
  commits the result.
  **Update 2026-10-01 (third review, ARCH-1):** the extra-files route is
  open after all -- release-please's `toml` extra-file type is path-based
  (`GenericToml` with a jsonpath, no annotation), and the review's gate measured
  it rewriting exactly the two workspace-member version lines (release-please
  17.11.2; not re-checked in the orchestrating session). Fix together with
  T-0113 / ARCH-17: today the hand-made lock commit is the only CI run on the
  release tree, and automating it removes that run.

- T-0081 **release-please drops a commit whose body has a line starting
  with `word(` -- diagnosed 2026-11-04, prevention still open.** The old
  suspect (multi-part scope with `!`) is cleared.
  * Diagnosed offline with release-please 17.11.2's own
    `parseConventionalCommits` (scratch install, no release, no GitHub): the
    0.3.0 commit `e3abe9f` fails at body line 29, `` `Caveat(` would prove
    ...``. The same message with a single scope, or without `!`, is dropped
    too; its header alone parses with the multi-part scope and `!`. Minimal
    cases: a body line beginning `foo(bar`, `` `foo(` ``, `one-two(bar` or
    `P(Hyp(N-1, ...) <= Ac) < 1/N` drops the *whole* commit; `see foo(bar`,
    `foo (bar` and `foo(bar) would` parse. The parser (`@conventional-commits/
    parser` ^0.4.1) reads such a line as the start of a footer token. The
    0.2.1 -> 0.3.0 bump needs no breaking footer to explain it: on 0.x a
    `feat` bumps the minor anyway.
  * Swept every visible commit since v0.3.0: one more is dropped, `1ca99bf`
    (T-0106, line 20 `P(Hyp(...`). Pushed, so not rewritten; PR #56 carries a
    `BEGIN_COMMIT_OVERRIDE` block with all eleven visible headers (checked:
    the parser reads 11 of 11). After the merge, check that T-0106 is in the
    release PR's changelog -- the override path is not yet proven on a merge
    commit.
  * Open (prevention): a CI step on pull requests that runs the same parser
    over each visible commit and fails on a drop; and an `AGENTS.md` line for
    the maintainer to decide ("no body line may begin with an identifier
    directly followed by `(`; indent or reword it").

- T-0078 **Point positions are reported in two conventions.** Found while
  building the CLI, not by the review. The core's warnings quote raw 0-based
  indices -- "the moving range chart is out of control at [29, 30]" -- while
  the web app and the CLI both count points from 1, the way a person reads a
  chart. In the CLI's output both now appear in one block: "out of control at
  point(s): 30, 31" directly above a warning naming [29, 30] for the same two
  points.
  Not fixed here: it is pre-existing, it touches warning text several tests
  assert on, and it is the kind of change that should be one deliberate commit
  rather than a rider on a feature. The honest options are to make the core's
  warnings 1-based (and say so), or to state the convention in each message.
  Acceptance: one convention, or every message that quotes an index says which.
- ~~T-0063 **The compute endpoints accept a body of any size**~~ -- **decided
  and done 2026-09-02.** The maintainer chose a byte limit in middleware (10 MB,
  413, mirroring `/ingest`) over a per-field `max_length`, so the published
  OpenAPI schema is unchanged. See `## Done`.
- ~~T-0058 Verdict thresholds duplicated between core and UI~~ -- **done
  2026-08-23**: the core states the AIAG band as a word; the UI colours by it
  and owns no boundary. Half the finding was wrong -- see `## Done`.
- ~~T-0059 The API error path copied 11 times~~ -- **done 2026-08-23**:
  `callApi` + `<ErrorAlert>`; `describeApiError` is now called from exactly one
  place. See `## Done`.
- ~~T-0060 Charts without an accessible name~~ -- **done 2026-08-23**: all
  three carry `role="img"` and a name built from what they draw. See `## Done`.
- ~~T-0061 "Decide the lot" was a silent no-op~~ -- **done 2026-08-23**: the
  decision judges the plan the report describes, which removes the null case
  rather than disabling the button. See `## Done`.
- T-0062 **Documentation, not a defect -- the one finding the review got wrong.**
  It read `_updated_score` (`sampling_scheme.py:279`) resetting the switching
  score to 0 for an accepted lot without tighter-AQL confirmation as
  non-conformant, expecting `[3, 5]` where capstat gives `[3, 0]`. The code
  matches ISO 2859-1:1999 clause 9.3.3.2 as `LotResult`'s docstring states it:
  Ac >= 2 plans add 3 or **reset**, Ac <= 1 plans add 2 per accepted lot. The
  reset is in the standard.
  What is genuinely imprecise is the generated restatement in
  `docs/validation-sources.md:139` -- "the score adding three or two per
  accepted lot" omits the reset entirely, and reads as if an accepted lot could
  never lower the score. That sentence produced the false finding.
  **Caveat, stated rather than hidden:** no licensed copy of the standard was
  consulted here; the judgement rests on code, docstring and reference YAML
  agreeing with each other. The repo already carries this as an open gap.
  Acceptance: the restatement names the reset condition, and a test pins the
  reset case so the next outside reader does not have to ask.
- ~~T-0050 Next-generated agent files~~ -- **done 2026-08-16**: gitignored,
  and the useful part rewritten into the root `AGENTS.md`. See `## Done`.
- ~~T-0049 e2e flake: the switching-rules request assertion~~ -- **done
  2026-09-02.** It fired again on PR #26, on the first attempt *and* CI's
  retry, which is what forced the issue rather than another re-run.
  The cause was the shape of the wait, not the app. Three tests pushed each
  intercepted body into a local array and then `expect.poll`-ed it. Polling was
  already the *second* attempt -- reading the array once lost about one run in
  three, because the label under test renders from component state and so
  appears before the request necessarily has -- but a poll carries a fixed 5 s
  budget, and under parallel load with a cold `next dev` compile that budget is
  what expired. Twice, in the same shape: T-0038, then this.
  Fixed at the source with `requestDuring` in `e2e/support.ts`, which arms
  `page.waitForRequest` *before* the action and resolves on the request event.
  No fixed budget, no window in which the request can be missed.
  **Applied where one action causes one request** -- the two acceptance-sampling
  tests. Deliberately *not* applied to the run-rule selection in `smoke.spec`:
  that assertion is about where several toggles come to rest, and polling the
  last captured body is the right tool for a settled end state. Using an event
  wait there would race the earlier toggles' requests.
  Verified: 140 runs of the spec (`--repeat-each 10 --workers 4`) green, which
  is the acceptance criterion this task set itself. Negative probe: making the
  panel send every lot as accepted fails the test, so it still asserts the
  payload rather than merely the arrival.
- T-0047 **changed 2026-08-16, but not yet proven.** `publish.yml` now names
  `actions/checkout@v7` and `astral-sh/setup-uv@v7`, matching `ci.yml`, with the
  setup-uv reasoning referenced rather than restated. The risk is low because
  `ci.yml` runs exactly these majors on every push and has been green all day --
  but that is an argument, not evidence for *this* workflow.
  **Stays open until a real release goes through it**, because publish.yml is
  the one workflow whose runs cannot be rehearsed: every execution either
  publishes to PyPI or fails in front of a human. Close this when the next
  release is dispatched successfully (T-0030's flow), not before.
- ~~T-0046 npm advisories have escalated well past what T-0023 left open~~ --
  **done 2026-08-16**, see `## Done`. 16 open alerts to zero.
- ~~T-0045 `publish.yml` builds `main`, not the release tag~~ -- **done
  2026-08-16**, see `## Done`.
- T-0029 Docs stack risk: mkdocs-material warns that MkDocs 2.0 removes the
  plugin system entirely, with "no migration path" and the theming rewritten --
  which would break mkdocstrings and the Material theme together.
  **Corrected 2026-07-21:** this entry claimed "we pin mkdocs 1.x". We did not.
  `pyproject.toml` said `mkdocs>=1.6`, a floor with no ceiling; what actually
  held the version was the committed `uv.lock` plus `uv sync --frozen` in CI.
  Reproducible, but a lock refresh would have crossed the major silently, and
  the break would have landed while working on something unrelated. Now
  `mkdocs>=1.6,<2` -- the intent is in the dependency, not implicit in a lock.
  mkdocs 2.0 is not released yet (PyPI latest: 1.6.1), so nothing is urgent.
  The remaining decision, when 2.0 lands: stay on 1.x deliberately, or move to
  another generator -- to be made after checking whether mkdocstrings and
  Material support 2.x, not before.
  Deliberately *not* done: ceilings on every other dependency. Blanket upper
  bounds block security fixes and pile up upgrade debt; this one is justified by
  a specific, announced removal, not by a general fear of major versions.
- ~~T-0015b Public demo deployment~~ -- dropped. T-0026 decided against public
  hosting (local only). The Docker artifacts stay for self-hosting; there is
  just nothing to deploy.
- ~~T-0030 Decide whether capstat-core goes to PyPI~~ -- **decided and done
  2026-08-16: published as `capstat-core` 0.2.0.** The decision history below is
  kept because it records why, and what I got wrong on the way; the outcome and
  the one trap that nearly fired are in `## Done`.
  Original entry: releases stay GitHub-only until then, and the docs say so
  rather than implying a `pip install` that would fail.
  **2026-07-21, partially set up.** The maintainer created the PyPI account
  (`xindaan`) and added a **pending trusted publisher** by hand: project
  `capstat-core`, owner `Xindaan`, repo `capstat`, workflow `publish.yml`,
  environment `pypi`. Reported done by the maintainer; not independently
  verified from here -- Claude for Chrome could not inject into pypi.org, so
  check the list on https://pypi.org/manage/account/publishing/ before relying
  on it. The first real publish attempt would confirm it either way.
  **A correction worth keeping, because it was my error:** I had advised that
  this "reserves the name without committing". It does not. PyPI's own docs:
  *"A 'pending' publisher does not create a project or reserve a project's name
  until it is actually used to publish"* -- and if someone else registers the
  name first, the pending publisher is invalidated. There is no reserve-without-
  upload mechanism on PyPI at all; a name is yours only once a release exists.
  Both `capstat` and `capstat-core` were still free (HTTP 404) on 2026-07-21.
  What the pending publisher *does* buy: when publishing is decided, the OIDC
  trust path already exists, so no API token is ever created, stored or rotated.
  **Deliberately not done: `publish.yml` itself.** With that workflow in the
  repo and keyed to the release tag, the next release would upload to PyPI
  unasked. The pending publisher alone is inert -- that is the point. Adding
  the workflow is the same decision as publishing, and it is still open.
  Sequencing note: publishing an sdist puts the source on PyPI, which is a
  *larger* step than making the repo public. Settle the visibility question
  first. Also needs a GitHub environment named `pypi` (Settings -> Environments)
  before any publish run works; worth a manual-approval rule when it is created.
  **2026-07-23 -- the sequencing gate is cleared: the repo is public.** So the
  larger-step-first ordering is satisfied, and T-0030 is now genuinely
  decidable rather than blocked.
  **On whether publishing is presumptuous (the maintainer asked).** It is not.
  PyPI has no gatekeeper -- no review, no quality bar; the median package on it
  has zero tests. Publishing is renting shelf space, not claiming importance.
  Measured against what is actually there, capstat-core sits well above the
  floor (517 tests at 100 % coverage, mypy strict, `py.typed`, and reference
  data in-tree with source + certified value + justified tolerance per method).
  The classifiers say `Development Status :: 3 - Alpha` and the README says
  "early development", so nothing over-claims. The real cost is not reputation
  but *commitment*: once someone pins `capstat-core`, a breaking change hurts,
  and the version + name are permanent. So the test is "can I stand behind it",
  not "is it good enough" -- and the answer is yes, because the statistical
  judgements are the maintainer's own field.
  **Recommendation recorded: publish when there is a reason, not for
  completeness.** The most likely reason is writing about capstat publicly
  (LinkedIn), where `pip install capstat-core` for a reader beats "clone and
  install from the checkout". Absent that pull, waiting costs nothing: both
  names were still free (HTTP 404, re-checked 2026-07-23) and the collision risk
  on so specific a term is low. What is NOT a good reason to hold back: that it
  *feels* presumptuous -- that is the same reflex that leaves the quality world
  with only expensive proprietary tools.
  **Mechanics verified 2026-07-23:** `uv build --package capstat-core` produces
  a clean `capstat_core-0.1.0` wheel + sdist; version is release-please-managed
  (0.1.0). Publishing would mean adding `publish.yml` (trusted-publisher OIDC,
  environment `pypi`, no token), then either a manual `workflow_dispatch` run to
  push the existing 0.1.0, or letting the next release-please release trigger
  it. Adding that workflow is still the point of no return, and still the
  maintainer's explicit call.
  **2026-07-23 -- staged, deliberately not fired (maintainer's choice).**
  `publish.yml` now exists but has NO push/release/tag trigger: it is
  `workflow_dispatch` only, so merging it publishes nothing. It uploads over
  trusted publishing (no token) and stops at the `pypi` environment, which was
  created with **Xindaan as a required reviewer** -- so even a manual run halts
  for a human approval before the upload. Two gates (dispatch, then approve)
  stand between here and a permanent 0.1.0 on PyPI. The workflow also verifies
  the built version against `capstat_core.__version__` before uploading, because
  a wrong version is the one mistake trusted publishing cannot catch and PyPI
  uploads cannot be undone. **To actually publish:** Actions tab -> "publish" ->
  Run workflow, then approve the `pypi` deployment. Do it when there is a reason
  (writing about capstat publicly), not for completeness. The pending trusted
  publisher on PyPI is still unverified from here; the first real run confirms
  it (and fails harmlessly, uploading nothing, if it is misconfigured).
- ~~T-0018 Roadmap (explicitly NOT v0.1)~~ -- split 2026-07-21 into T-0035..
  T-0041. It bundled four unrelated themes behind one ID, which made it
  un-schedulable: one of them is a statistical method this library exists to
  provide, two of them would reverse T-0026, and one is a packaging chore.
  Superseded; the individual entries carry the work and the decisions.

- T-0036 Acceptance sampling, part 2: the standard plans (AQL lookup).
  Depends on T-0035. This is deliberately a *separate* task, because it breaks
  the project's core rule and needs the break stated rather than hidden: the
  sample-size code letters and the master table (n, Ac, Re) of ISO 2859-1 are
  committee conventions, not values derivable from a closed definition. They
  must be transcribed. The honest handling is therefore inverted from every
  other reference in this repo -- transcribe with full provenance, then
  *verify each entry against computed OC properties from T-0035* (each
  normal-inspection entry should give Pa at the AQL in the neighbourhood the
  standard designs for), and report entries that do not fit rather than
  quietly accepting them.
  **Licensing: answered 2026-07-21** (research pass during T-0035, sources
  read first-hand where reachable). ISO standards carry the standard ISO
  copyright notice -- no part may be reproduced without written permission --
  so ISO 2859-1's tables cannot go into an MIT repository. MIL-STD-105E is a
  work of the US Government, which 17 U.S.C. section 105(a) excludes from
  copyright, and its Notice 3 (06 Feb 2008) carries DISTRIBUTION STATEMENT A,
  "approved for public release, distribution unlimited". NIST states the
  lineage plainly: Mil. Std. 105D was adopted as ANSI Z1.4 in 1971 and, with
  minor changes, as ISO 2859 in 1974.
  **Worth doing: decided yes, 2026-07-21.** The maintainer confirmed AQL
  sampling is used in their own work, which is the only thing that justified it
  -- the value here is reproducing exactly what a customer or auditor
  *specifies*, not computing a better plan. T-0035 remains the better product
  for anyone free to choose their own risks; this is for the case where you are
  not free.
  **Standard: ISO 2859-1, decided 2026-07-21.** Which changes what can be
  built, and rules out what an earlier draft of this entry recommended. That
  draft said "ship MIL-STD-105E tables and cite ISO in prose"; with ISO as the
  target that is the *worst* of the options, not a workaround. NIST's own
  wording is that Mil. Std. 105D was adopted into ISO 2859 "with minor
  changes" -- so a 105E cell may differ from the ISO cell a specification
  names, while looking conformant. For an auditor that is worse than shipping
  nothing. And ISO's own tables may not be reproduced here at all.
  **So the buildable shape has no master table in it.** Three increments, in
  order, none of which requires copying a table:
  1. *ISO vocabulary and the workflow that needs no table.* **Done
     2026-07-21** (commit b37e987): limiting quality (LQ) is computed at
     Pa = 0.10 from the plan's own OC curve and reported next to the LTPD the
     caller asked for, so a plan that does not protect where you believed it
     did says so. Core, API and page.
  2. *The switching rules.* **Done 2026-07-22, core only.** The full ISO
     scheme: normal <-> tightened, discontinuation, the switching score, and
     reduced inspection. Validated by simulation *and* by reproducing the
     standard's own Annex A worked series completely -- every severity, every
     score, and the switch to reduced at the lot where the score reaches 30.
     **2b done the same day:** a `/compute/acceptance-sampling/switching-rules`
     route and a second panel on the page -- a lot series in, the severity each
     lot was inspected under and the switch it caused out, with the switching
     score shown as absent (not zero) wherever the standard does not keep it.
  3. *Code-letter lookup* -- only if 1 and 2 leave a real gap, and only from a
     source we may reproduce. Currently that means: not from ISO.
  Caveat that has not changed: the licensing reading above came from a research
  pass whose primary sources I did not open myself (the subagents quoted them).
  Before any of this ships publicly, read 17 U.S.C. 105(a) and the ISO
  copyright notice yourself, or have someone who does this for a living do it.
  It is a reading of primary sources, not legal advice.
  **Findings from the switching-rule research passes, worth keeping:**
  *(a) The copies of ISO 2859-1 and ANSI/ASQ Z1.4 reachable online are of
  uncertain provenance* -- the one the agents read carries IHS "Provided by IHS
  under license with ISO / Not for Resale" watermarks on a third-party site.
  The verifying agent flagged it itself. Consequence, and it is now the
  standing rule for this task: **no wording from either standard goes into this
  repository, and neither URL goes on the sources page.** Thresholds are facts
  and are cited by clause, restated in capstat's own words. If the switching
  rules are ever relied on for conformity, check them against a licensed copy.
  *(b) The half that died at the monthly spend limit was re-run on 2026-07-22*
  and settled both open questions. Reduced inspection and the switching score
  are now implemented. The 5-vs-10 disagreement over the discontinuation
  threshold turned out to be an **edition artefact, not a conflict**:
  ANSI/ASQ Z1.4-2003 changed the rule from ten consecutive lots on tightened to
  five lots *not accepted*, so older material states the old figure. ISO 9.4 and
  Z1.4 8.4 agree on the current rule.
  *(c) That research also caught a real bug in capstat.* The first
  implementation counted lots *inspected* under tightened where clause 9.4
  counts lots *not accepted*, cumulatively. Anyone setting the threshold to 5
  believing they had implemented 9.4 would have got a materially different rule.
  Fixed, and pinned by a test that runs forty lots through tightened inspection
  with only four non-accepted among them.

  Split into sub-tasks, in order. Each is a gate for the next:

  - **T-0036a Provenance gate.** Read the two primary sources *first-hand*
    before any table is extracted: MIL-STD-105E Notice 3 (the cancellation
    notice carrying DISTRIBUTION STATEMENT A) and 17 U.S.C. 105(a). The
    licensing note above rests on subagent reports with quotes, which is
    second-hand and explicitly not good enough for the step that puts a
    standard's tables into an MIT repository. Record what was read, and where,
    in the reference YAML.
  - **T-0036b Obtain and extract.** Get the authoritative MIL-STD-105E text and
    extract Table I (sample size code letters: lot size x inspection level) and
    Tables II-A / II-B / II-C (normal / tightened / reduced: code letter x AQL
    -> n, Ac, Re) *mechanically*, by parsing the document -- not by hand. Hand
    typing ~16 code letters x ~26 AQL columns x 3 tables is where transcription
    errors come from; deterministic extraction plus the verification below is
    strictly safer. Arrow cells ("use the first plan below/above the arrow")
    must be represented as arrows, not silently resolved, because resolving one
    changes the sample size.
  - **T-0036c Verify every entry against T-0035.** For each normal-inspection
    cell compute Pa at its AQL from the core's own OC function and record it.
    Do not assert a fixed threshold: the standard does not hold Pa at the AQL
    constant, and pretending otherwise would manufacture failures. Assert the
    properties that are actually true -- Pa at the AQL rises with the sample
    size code letter for a fixed AQL, every cell's Ac is below its n, Re = Ac+1
    -- and *publish the computed Pa per cell* so the spread is visible rather
    than assumed. Any cell that cannot be reconciled gets named in the YAML,
    the way the four NIST table errors were.
  - **T-0036d The switching rules.** ISO 2859-1 and 105E are *schemes*, not
    plans: the protection comes from switching between normal, tightened and
    reduced inspection, and from discontinuation. A lookup that stops at the
    normal table gives users less than the standard promises while looking like
    compliance. This is the part with real substance -- and it is state over a
    sequence of lots, so it needs a deliberate answer to "where does that state
    live" given T-0026 and T-0040 (probably: the caller passes the history in,
    the library holds nothing).
  - **T-0036e Surface it.** Code letter + AQL lookup over the API and on the
    existing `/acceptance-sampling` page, next to the computed plan rather than
    instead of it, so the two can be compared -- which is the most useful thing
    this feature can do: show what the standard's plan actually costs you in
    risk against the plan your own numbers would have chosen.

  Standing constraint: ISO 2859-1's tables must not be copied. Cite it in prose
  for terminology and correspondence, ship 105E, and do not claim the two are
  identical -- "with minor changes" is the published wording.

- T-0038 [DEFERRED 2026-07-21, by decision] Server-side PDF endpoint. Neutral
  on principle -- it conflicts with no decision -- but it is the weakest of the
  four T-0018 themes: the print route already produces a vector PDF from the
  browser (T-0014), so this buys automation, not capability, in exchange for a
  heavy dependency (WeasyPrint or a headless browser) in an API that is
  currently small and pure. If it is ever wanted, the shape to build is a local
  CLI export rather than a service endpoint, given T-0026. Left open rather
  than closed, because the reason to defer is cost, not principle.

- ~~T-0041~~ **done 2026-07-22.** Save and reload a study as a JSON file:
  the format (`apps/web/lib/study-file.ts`, versioned, page-keyed, inputs only),
  the Save/Load controls, and all three hand-entered pages wired --
  `/acceptance-sampling`, `/gage-rr` and `/msa`.
  **`/` is deliberately not wired**, and that is the answer rather than an
  omission: its input is an uploaded CSV, so re-uploading the file is simpler
  than restoring it from JSON, and a study file holding thousands of
  measurements would be a copy of data the user already has.
  The open design question is **answered, by looking**: there is no shared
  document shape to find. The panels have nothing in common but strings (LSL/USL
  here, a 3-D grid there, number lists elsewhere), so the document carries a
  version, a page name, and a payload keyed per page. A single flat schema would
  have been invented rather than derived.
  `/` is the one page that may never need it: its input is an uploaded CSV, and
  re-uploading the file is easier than restoring it from JSON.
  Original scope note below, kept because the reasoning still holds.

- T-0041 (original) Save and reload a study as a JSON file. The carve-out kept when
  T-0040 was declined, and deliberately *not* persistence: a file the user
  owns, on their own disk, written and read by the browser -- no server, no
  database, no schema migration, nothing held between requests. Reverses
  nothing in T-0026.
  Scope when it is picked up: one versioned document per analysis page holding
  the inputs (the data, the spec limits, the chosen options), never the
  computed results -- results are recomputed from the validated core on load,
  so a stale file can never present numbers this version did not produce.
  A `schema_version` field from the first commit, and a load path that refuses
  an unknown version with a readable message rather than guessing.
  Open question for whoever takes it: whether the Gage R&R grid and the three
  MSA studies share one document shape or get their own. Answer it by looking
  at what the pages actually hold, not by designing upfront.
- T-0026 [DECIDED 2026-07-20: no public hosting; local only.] The maintainer
  would sooner run capstat locally than send measurement data to a third party,
  which is the right instinct for a tool people feed real production data into.
  So there is no public demo and no hosted API. `docker compose up` is the
  supported way to run it, and it needs no account, no cloud, and no data ever
  leaving the machine. Left in the docs for anyone who *does* want to host it:
  the measurement (~152 MB deps, ~1 s cold import) and why that points at a
  container host over serverless. But we are not doing it.
  A quieter consequence, worth stating: the web app is fully static (all three
  routes prerender), so if a public demo is ever wanted it needs only a static
  host (GitHub Pages, free) for the app plus a compute host for the API -- the
  `output: "standalone"` Docker setup is for self-hosting, not that.

## Done

Older Done entries (before 2026-10-01): `docs/task_done_bis_2026-Q3.md`.

- T-0095, T-0096, T-0097, T-0098, T-0099, T-0100, T-0102, T-0105, T-0106
  (implemented 2026-10-21 by parallel agents, integrated into
  `fix/review-2026-10-01` on 2026-11-04) **The silent-wrong-number items of
  the third review are fixed.** Each commit message carries the measurement
  before -> after, the red tests and the negative probe; this entry only
  indexes them.
  * T-0095 (`d90a896`): one-column German CSV, trailing delimiters and
    header-less files read correctly; the indistinguishable header-less
    `9,71` shape is refused with a named reason (API-1, API-6, TQ-14, TQ-17).
  * T-0096 (`6b1b135`): "zero spread" decided against the data's scale
    (`_validation.is_zero_spread`, threshold 2**-43 of max|x|).
    **Follow-up 2026-11-04 (`fix(core)`, compare a root spread without
    squaring it):** five callers squared a root before the helper took the
    root again; a Python float above ~1e154 raises `OverflowError`, which a
    Box-Cox fit with a large lambda reaches from ordinary readings --
    `capstat capability` on 30 rounded diameters crashed after the T-0095
    merge exposed the path. New `is_zero_deviation`; one regression case per
    caller, each caller reverted alone turns exactly its case red.
  * T-0097 (`08341aa`): percentile fit on the standardised sample (unit
    invariant: 0 of 320 rescalings move Ppk), fully specified
    Anderson-Darling score, gauge-rounded normal data recognised by a
    parametric bootstrap, fewer than three distinct readings refused, a
    degenerate Box-Cox lambda refused with its true reason. Checked in the
    integrating session: the loc/scale back-mapping and the AD formula
    (NIST 1.3.5.14); the bootstrap calibration was not re-derived there.
  * T-0098 (`0a7dbbf`): the axis always contains UCL/LCL; limit values
    printed. T-0099 (`c782be7`): "Decide the lot" sends a valid plan, every
    mocked e2e request body is validated against `openapi.json`.
    T-0100 (`da16ede`): hand-entered numbers read the same in every locale.
  * T-0102 (`708b52d`): subgroups are cut by file row, so a blank cell
    shifts nothing (API and CLI).
  * T-0105 (`6734545`): non-finite and out-of-range parameters refused by
    `check_scalar`; API 422 instead of a 500. Left open: NaN in `rules.py`
    via the library, Box-Cox's caller-supplied lambda, SAMP-12.
  * T-0106 (`1ca99bf`): exact Type A AOQ
    `(D/N)((N-n)/N) P(Hyp(N-1, D-1, n) <= Ac)` and an exhaustive Type A AOQL
    with the exact stopping bound F(D) < 1/N. Re-derived in the integrating
    session: the identity `(D-x) h(x;N,D,n) = D (N-n)/N h(x;N-1,D-1,n)`, the
    hand case (10, 5, 0, D 1) = 0.05 and the bound.
  * Gates on the integrated branch (2026-11-04): 957 Python tests, coverage
    100 %, ruff, ruff format, mypy --strict, `export_openapi --check`; web:
    tsc, eslint, 152 vitest, Playwright 62/62 (after the T-0118 mock fix).

- T-0117 (2026-10-22) **Security update of locked dependencies (patch check
  2026-10-22); no code change.** Raised each flagged package to the smallest
  fixed release in its line.
  * `apps/web`: next 16.3.5 -> 16.3.8 and eslint-config-next 16.3.5 -> 16.3.8
    (GHSA-vcvr-r3jv-pc5j CRITICAL RCE in next/og, GHSA-cjq9-62q9-8jv4 HIGH SSRF,
    plus 5 MODERATE/LOW); vitest/@vitest/mocker 4.1.11 -> 4.1.12; vite 8.3.0 ->
    8.3.5 (fix 8.3.3, npm resolves the range to the latest patch;
    GHSA-587h-7wmj-h5pm); sharp 0.35.4 -> 0.35.5 (GHSA-wq5f-xc86-pv6w);
    source-map-js 1.2.1 -> 1.2.2 (GHSA-68fv-2mgg-jv7q); brace-expansion
    1.1.18/2.1.4/5.0.9 -> 1.1.21/2.1.7/5.0.12 (GHSA-6j4f-fj2g-mc7p,
    GHSA-qhr7-859c-m2p7, GHSA-q2hr-2g5m-vwhr).
  * `uv.lock`: certifi 2026.6.17 -> 2026.10.19 (GHSA-6q48-6c7w-9gw2 CRITICAL),
    urllib3 2.7.0 -> 2.8.0 (GHSA-8988-9cw3-xx77, GHSA-vxq7-64xx-v4gw),
    virtualenv 21.6.1 -> 21.14.9 (8 HIGH advisories, e.g. GHSA-c978-59m8-c77v);
    pulled in by virtualenv: packaging 26.2 -> 26.3, python-discovery 1.4.4 ->
    1.6.4.
  * Measured with an OSV batch query per lockfile: package-lock.json 27 hits
    (1 CRITICAL, 11 HIGH) -> 1; uv.lock 23 hits (1 CRITICAL, 10 HIGH) -> 0. Left
    open: braces 3.0.3 HIGH (GHSA-vfj7-8cjw-p6xm), no fixed release exists.
  * Tests on the old and the new lock: pytest 677 passed -> 677 passed; vitest
    79 -> 79; `next build`, `tsc --noEmit`, eslint green on both; ruff, ruff
    format, mypy and `uv pip check` green after. Playwright not run.
  * Note: `npm install vitest@^4.1.12` crashes in npm 10.9.9 (arborist
    `#loadPeerSet`: "Cannot read properties of null (reading 'edgesOut')");
    the vitest bump was done with npm 11.6.2, then re-normalized with npm
    10.9.9 (`npm install` restored the `@emnapi/*` entries npm 11 had dropped;
    `npm ci` clean).
