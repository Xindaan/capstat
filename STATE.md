# STATE.md — capstat

Date: 2026-11-05

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
- **PR #56 merged to main 2026-11-04 (2026-10-21 agent work):**
  T-0095..T-0100, T-0102, T-0105, T-0106 done, plus a 2026-11-04 overflow
  fix in the T-0096 helper and the Codex review fixes. T-0097's rounding
  re-routing is switched off by decision (2026-11-04, T-0118: no reference
  case yet). Gates: 959 Python tests, 100 % coverage, mypy, ruff,
  154 vitest, Playwright 63/63.
- **Third review 2026-10-01** (T-0095..T-0115): open are T-0101, T-0103,
  T-0104, T-0107..T-0115; T-0103/T-0104/T-0108 decided 2026-10-07.
- **Release path is hardened but one proof short** (T-0093, T-0047).
- Steering-file commits are `chore` (T-0094); an open release PR is normal.

## Live risks / pitfalls

- **Uncommitted agent work in three worktrees** (`.claude/worktrees/`,
  T-0118). Removing a worktree discards it; decide per worktree first.
- **T-0093 is not field-proven:** confirmed only after a green publish run
  containing `install attempt N failed ... retrying`. T-0047 likewise.
- **T-0081:** a commit body line that starts with `word(` makes release-please
  drop the whole commit from the notes. Reword such lines; PR #56 carries an
  override for the affected `1ca99bf`.
- **T-0078:** core warnings quote 0-based indices, app and CLI count from 1.
- **Dependabot (T-0116):** T-0119 closed the ten alerts of 2026-11-05; #60
  (dev-only minimatch) fixed by an npm override, to be removed once
  typescript-eslint allows minimatch 11 (T-0120). npm audit still flags
  dev-only zod (T-0120). Update PRs #47, #48, #50-#52 open.

## With Andre

- **T-0116** Dependabot: merge or close the open update PRs (#54/#55 are
  superseded by T-0119).
- Optional: prune Discussions categories to Q&A + Announcements (T-0043).
- Confirm or edit the proposed success criterion above (Outcome is yours).

## Next actions

1. **T-0118** -- decide the three dirty worktrees (PR #56 is merged).
2. **T-0081** -- after the merge, check T-0106 is in the release PR's
   changelog; then add the CI parser check (diagnosis done 2026-11-04).
3. **T-0101 / T-0107** -- the next review items (T-0103/T-0104 are decided).

## Dates

none

## Last done

- 2026-11-05: **T-0119** the ten open Dependabot alerts closed (next 16.4.1,
  virtualenv 21.14.13, filelock 4.2.1).
- 2026-11-04: **Agent work of 2026-10-21 integrated** (T-0095..T-0100, T-0102,
  T-0105, T-0106) plus the `is_zero_deviation` overflow fix.
- 2026-11-04: **Done entries before 2026-10-01 archived** to
  `docs/task_done_bis_2026-Q3.md` (verbatim, cmp-checked).
- 2026-10-22: **T-0117** security update of locked dependencies.
- 2026-10-07: **Third review filed as T-0095..T-0115.**
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
