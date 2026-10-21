# STATE.md — capstat

Date: 2026-10-21

## Goal

Reference-validated SPC / capability / MSA library (Python) + FastAPI +
Next.js frontend as a professional MIT open-source project. Released: v0.4.4.
`capstat-core` 0.4.1, 0.4.2 and 0.4.3 are on PyPI, each verified
byte-identical to its tag. **v0.4.4 is tagged and not published** (it carries
only the T-0093 write-up); v0.4.0 is unpublished for the same kind of reason.
Both stay publishable; `publish` is manual and the maintainer's to run.

Success criterion -- Proposal, not yet confirmed by Andre: every number and
verdict the app prints is either right or carries a warning, shown by
reference-data tests (100 % coverage, mutants killed) and a published
byte-verified release.

## Status

- **M1-M6 complete, v0.1.0 released 2026-07-21; repo public** (2026-07-23).
  Local-only by decision (T-0026): `docker compose up`, no public demo.
- **Core, API, web app, MSA, acceptance sampling and CLI are end-to-end;**
  `capstat-core` stays numpy+scipy only, web-free.
- **Gates at b55623a (2026-10-01):** 677 Python tests, 100 % coverage, mypy
  strict, ruff, 79 vitest clean; mutation kill rate 66 %.
- **Third review 2026-10-01 is filed as T-0095..T-0115** (155 findings, 44 of
  55 gated confirmed, none refuted). None of it is fixed; Doing is empty.
- **Release path is hardened but one proof short** (T-0093, T-0047): 0.4.3 was
  the first unattended green publish, yet the install retry has never fired.
- Steering-file commits are `chore` (T-0094); release PR #45 (0.4.5) is the
  open resting state, not a pending release.

## Live risks / pitfalls

- **Silent wrong numbers are open now:** one-column German CSV (T-0095), zero
  spread by float equality (T-0096), non-normal path not unit-invariant
  (T-0097), limits missing on in-control charts (T-0098), "Decide the lot"
  failing on every call (T-0099).
- **T-0093 is not field-proven:** treat it as confirmed only after a green
  publish run containing `install attempt N failed ... retrying`. T-0047
  (`publish.yml` action majors) is open on the same condition.
- **T-0081 will recur:** a breaking commit with a multi-part scope drops out of
  the release notes. Until fixed, use a single-word scope (`feat(core)!:`).
- **T-0078:** core warnings quote 0-based indices, app and CLI count from 1.
- **Dependabot (T-0116, gh 2026-10-21):** 13 open alerts (high:
  next x2, vite, source-map-js) and PRs #47, #48, #50-#53 open, incl. next 16.3.8 (#53).
  The T-0046 "zero alerts" state of 2026-08-16 no longer holds.

## With Andre

- **Decide T-0103** (Cpm: sigma_within or overall; off-midpoint target) and
  **T-0104** (what "in control" / "stable" mean) before any code is written.
- **T-0116** Dependabot: merge or close the open update PRs.
- Optional: prune Discussions categories to Q&A + Announcements (T-0043).
- Confirm or edit the proposed success criterion above (Outcome is yours).

## Next actions

1. **T-0095** -- German one-column CSV read as wrong numbers; red test first.
2. **T-0096..T-0099** -- the remaining silent-wrong-number items, in order.
3. **T-0081** -- diagnose the release-please breaking-commit drop (scratch
   branch, not a real release).

## Dates

none

## Last done

- 2026-10-07: **Third review filed as T-0095..T-0115** (d4ae9b4); T-0094
  result recorded on its own commit (00ed9c8).
- 2026-09-21: **T-0094 -- steering-file commits are `chore`**, ending the
  release-PR loop; proved on `b410bae` (no release PR opened).
- 2026-09-21: **0.4.4 cut and tagged, deliberately not published** (docs-only).
- 2026-09-20: **0.4.3 published, first unattended green run (T-0093);** retry
  never fired, so not field-proven. 0.4.2 and 0.4.1 verified 19/19 identical.
- 2026-09-20: **T-0089/T-0090/T-0092 -- lock checked against the tag; stamp
  goes on the release branch.**
<!-- snapshot-ende -->

## Working method (keeps paying off — do not abandon it under time pressure)

1. **Compute from the definition; never transcribe a constant.** This caught a
   real error *in the published tables* (E2 = 2.660 is wrong; it is 2.6587).
2. **Validate against a source that did not produce the value.**
3. **Prefer identities to quoted numbers.** They hold for every dataset, and
   they disproved a false claim of mine in T-0006.
4. **Explain a discrepancy exactly rather than widening a tolerance.** A loose
   tolerance is where a real bug hides. **Values may carry a tolerance;
   decisions must not** (T-0008: NIST's first CUSUM signal is group 14, and ours
   is asserted to be group 14 exactly).
5. **Suspect your own test, and your own docstring, before the library.** Three
   tests in T-0008 were wrong, not the code. In T-0009 a *docstring claim* was
   wrong — I asserted the full Nelson set is "four times as jumpy"; simulation
   said eight times. Simulate the claim rather than repeating it.
6. **Find the sequence where two sources disagree.** WE rule 4 needs 8 points,
   Nelson rule 2 needs 9. A run of exactly 8 discriminates them — and that is
   what catches an off-by-one, which nothing downstream would reveal.
7. **Say what the numbers cannot say.** Every report carries warnings.

Older status, next actions, open decisions and the full "Last done" list:
`docs/state_archiv_2026-10-21.md` (verbatim) and `TASK.md` `## Done`.
