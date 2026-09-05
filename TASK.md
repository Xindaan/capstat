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

- T-0080 (2026-09-02) **Dependency sweep: five bumps, one verified combination.**
  Dependabot's five open PRs (#18-#22) all dated 2026-08-18 and all touched
  `uv.lock`, two of them `apps/api/pyproject.toml` -- which had since changed.
  * **Done as one branch against current `main` rather than five merges.** Each
    PR's green tick belonged to a base roughly twenty commits old, and merging
    them one at a time would have invalidated the next one's lock without ever
    testing the combination. What actually matters is that the five work
    *together* with the current code, and that is what the gates now say.
  * mypy 2.3.1, pandas 3.0.5, uvicorn 0.52.4, types-pyyaml 20260815,
    httpx2 2.12.0. mypy was the one worth watching -- a new release meeting a
    week of fresh code -- and it is clean.
  * The declared floors were raised as dependabot proposed. Checked first that
    none of it touches `packages/capstat-core`: the published package still
    declares only `numpy>=1.26` and `scipy>=1.11`, so nobody installing
    `capstat-core` is constrained by any of this. Fighting the default
    versioning strategy would only have re-opened the same PRs weekly.
  * Noted while resolving it, and *not* a defect: `watchdog` left the
    environment because uvicorn's `standard` extra now uses `watchfiles`.
    `--reload` still works.

- **The three deferred features were built 2026-09-02**, in the order the
  warning-codes decision implied (T-0075, T-0076, T-0077). New follow-up:
  T-0078 below.

- T-0075 (2026-09-02) **The subgrouped analyses are reachable from the app.**
  * `capability()` has taken subgroups since T-0005 and `xbar_r_chart` has
    existed since T-0007. Neither was reachable: the page only ever sent a flat
    column, so **every Cp/Cpk the app has ever shown rested on a moving-range
    sigma** -- the fallback the library warns about on every such report. Built,
    tested, reference-validated, and invisible.
  * A subgroup size on the workspace groups consecutive rows in file order.
    That is the ordinary SPC arrangement *and* the assumption the result rests
    on, so the panel states it rather than implying it.
  * **Leftovers are reported, not dropped.** 30 measurements in subgroups of 4
    leave two out, and a study quietly computed on 28 of 30 is a different
    study with nothing on screen to say so.
  * Which chart pair follows from the size rather than being a second choice,
    and the pair names itself from what the core returned -- so the heading
    cannot announce a chart the panel is not showing.
  * The decision path stays individuals-only and the panel says why:
    `analyze_capability` needs a flat sample because Box-Cox and the percentile
    fit both work on one.
  * Two e2e fixtures were quietly wrong -- "Individuals" where the core writes
    "individuals". That never mattered while the titles were hardcoded, and
    broke the moment they came from the data.

- T-0076 (2026-09-02) **Phase II: judging new data against a known baseline.**
  * The charts only ever computed Phase I limits, and the docstring said so
    rather than offering the alternative.
  * **The cost of that default is worse than the textbook statement**, and the
    test measures it rather than repeating it. On 25 subgroups with a sustained
    shift over the last five, the Phase I centre moves from 9.98 to 11.18 --
    which does not merely soften the signal on the shifted subgroups but flags
    **seven stable ones** for sitting too far below a centre the shift invented.
    The chart misattributes the fault. My first draft of that test asserted
    Phase I would flag *fewer* points; it flags more, and the measurement
    corrected the claim.
  * `center=` and `sigma=` from a stable period hold the limits: exactly the
    five shifted subgroups signal.
  * **The Phase II arithmetic is the Phase I arithmetic.** Rbar and sbar are now
    recovered from sigma rather than the other way round, making it one code
    path -- and giving the reduction identity the tests assert for all three
    pairs: handed what it would have estimated, a Phase II chart reproduces the
    Phase I limits to 1e-12. All 566 core tests passed unchanged through that
    refactor, which is what says the arithmetic did not move.
  * Both halves or neither: a known centre with a sigma estimated from the data
    under test is neither phase. Refused in the core, 422 over HTTP, and the
    panel keeps the chart Phase I and says why.
  * The Phase I trial-limit caveat no longer fires where it is untrue; a
    different one takes its place.

- T-0077 (2026-09-02) **A local CLI.** `capstat columns | capability | chart`.
  * T-0026 decided capstat runs on your own machine. The web app honours that
    but wants two processes and a browser; this is the same analysis with
    neither.
  * **It lives in `capstat-api`, not a package of its own.** It needs exactly
    what that package already owns -- the tabular parsing -- and a CLI with its
    own CSV reader would be a second answer to "what does this file contain".
    The two would disagree about a decimal comma sooner or later. The parsing
    moved out of the router into `capstat_api/tabular.py`; one implementation,
    two callers, and a test asserts the CLI reads a cp1252 semicolon file with
    a decimal comma exactly as `/ingest` does.
  * **The agreement is the test that matters:** on the demo file the CLI
    reproduces the figures the README quotes and the screenshots show --
    percentile path, Pp 1.3792, Ppk 0.9418, and no Cp/Cpk. A second surface
    onto one library is only worth having if it cannot disagree with the first.
  * Exit codes distinguish a refusal from a crash: 2 for bad input, with the
    core's own message reaching the terminal verbatim as the HTTP layer passes
    it through as a 422. `--fail-on-signal` gives 3, and it is **opt-in** --
    turning "out of control" into a non-zero exit unasked would make every
    scripted run a pass/fail test, which is not what a control chart is for.
  * Extracting the parsing also fixed a small wrong in the router: an
    unsupported extension is a 415, not the 422 the shared catch-all would now
    have given it.

- **The three open decisions were taken 2026-09-02** (see the decision
  templates in the session that produced them). Body limit: middleware, not
  schema. Capability colouring: a stated requirement, not a fixed 1.33. Feature
  order: warning codes first, then the rest. T-0063, T-0073, T-0074 below.

- T-0063 (2026-09-02) **The compute body is capped at 10 MB.**
  * Measured before choosing: 2,000,000 floats are 13.15 MB on the wire and
    cost about 214 MB resident once parsed -- roughly 16x amplification, per
    concurrent request. Not a CPU problem; the same request computes in 0.43 s.
    The failure mode was an out-of-memory kill, which nobody reads.
  * **Decision: a byte limit in middleware, not `max_length` per field.** The
    resource at risk is memory, memory is bytes, and an element count is only a
    proxy for it. It also leaves `openapi.json` untouched -- verified by the
    drift check passing with no regeneration.
  * The price, stated rather than hidden: the limit is invisible in the
    contract, so a client learns it by receiving a 413. That was the strongest
    argument for the other option and it is recorded in the README.
  * 10 MB mirrors `/ingest` deliberately: a 10 MB CSV with one numeric column
    yields a compute body of about 7 MB, so a smaller ceiling would accept a
    file and then refuse to compute it.
  * Raw ASGI rather than `BaseHTTPMiddleware`, because the decision has to be
    made *while* the body arrives -- Starlette's HTTP middleware hands over a
    request whose body is already assembled, which is the moment the memory has
    been spent. Chunks are counted as they arrive, since a chunked request
    sends no `Content-Length` and a lying one is the case worth defending
    against.
  * **The ordering guard has its own test**, and it is the only one that fails
    when the order is swapped: the limit sits *inside* CORS, so a browser can
    read the 413 instead of an opaque CORS failure.

- T-0073 (2026-09-02) **Cp/Cpk are judged against a stated requirement.**
  * The page coloured green at 1.33 and amber at 1.00 -- thresholds the core
    contains nowhere and declines to assert, because what counts as capable is
    a customer's specification. The app was stating a verdict the library
    refuses to.
  * **Decision: the requirement becomes an input** (default 1.33), rather than
    removing the colouring or moving the threshold into the core.
  * The discriminating case, now an e2e test: a Cpk of exactly 1.33 meets a
    1.33 requirement and falls short of 1.67. The old threshold called it green
    for both, so a customer asking for 1.67 read a clean bill of health off a
    process that misses their specification.
  * 1.00 stays in code: it is not a convention but the point where the spread
    exactly fills the tolerance, and below it no requirement can make a process
    capable.
  * An unreadable or empty requirement colours *nothing* rather than falling
    back to 1.33 -- a default substituted there would reinstate the assumption
    the field exists to remove.
  * The report names the threshold it judged by, for the same reason the
    control chart names its rule set: a colour means nothing without the number
    behind it, least of all in a printed PDF.

- T-0074 (2026-09-02) **Every warning carries a code.** The largest change of
  the three, and the one chosen deliberately *first* because every page built
  later would be another place reacting to English prose.
  * `Caveat` is a **`str` subclass**, which is the decision the rest follows
    from. A warning still *is* its sentence, so all ~50 existing assertions,
    every `"text" in warning`, and every join kept working unchanged: the 537
    core tests passed on the first run after the conversion. A plain dataclass
    would have meant rewriting the tests that guard the statistics in the same
    change that touches the statistics.
  * 57 construction sites across 12 core modules, plus 7 in the ingest router
    so the contract is coded end to end rather than half of it. The rewrite was
    done through the **AST**, not by paren-counting: several warnings are
    multi-line f-strings containing brackets, which is exactly where a textual
    rewrite goes wrong silently.
  * Over HTTP a warning is now `{"code", "message"}` -- a **breaking contract
    change**, and the one thing the decision explicitly bought.
  * The guard is execution-based: a battery of 24 entry points asserts every
    warning is a coded `Caveat` with a well-formed, namespaced code. A grep for
    `Caveat(` would have proved only that somebody typed it.
  * Codes are deliberately **not** unique per message: `_clamp` emits
    `gage-rr.negative-variance` once per component, naming the component in the
    sentence. That is one kind of finding reported four times.
  * TypeScript found all nine render sites, and `data-code` now carries the
    code into the DOM -- with an e2e test proving it survives from the core to
    the page. Six e2e tests went red because their *mocks* still returned the
    old shape; that is the correct signal, and the fixtures were updated rather
    than the assertion loosened.

- **Second external review 2026-09-02 (Claude Fable 5.1, source read plus
  execution).** Its own summary: the statistics are sound -- the formulas for
  ANOVA Gage R&R, average-and-range, Anderson-Darling, the chart constants,
  capability, the OC curves and the switching rules were re-derived and nothing
  was wrong. The findings sit a layer above: where warnings are merged, where
  the UI holds input, and where the steering files disagree with the code.
  Filed as T-0064..T-0072. One finding (T-0071) was refuted by measurement and
  is recorded as refuted rather than quietly dropped. 609 Python tests at 100 %
  coverage, 65 vitest, 34 Playwright.

- T-0064 (2026-09-02) **The Box-Cox path was dropping the inner report's
  warnings.** The one finding that touched the project's central claim.
  * `analyze_capability` passed `transformed.warnings` straight through, and
    those were the two sentences Box-Cox writes about the *scale*. Everything
    the inner `CapabilityReport` said about the *data* -- the instability
    warning, the time-order caveat on the moving-range sigma, the missing-Cpm
    note -- was computed and then discarded.
  * Measured on a drifting lognormal series: path `box-cox`, sigma ratio 1.31,
    Cpk 1.60 against Ppk 1.22, and the analysis showed **one** warning where the
    report had made four. A user reading the app saw the flattering number with
    nothing to say the process was unstable -- exactly the failure capstat
    exists to prevent.
  * Fixed in `box_cox_capability`, so a direct caller benefits too, with
    de-duplication so nothing is said twice. Negative probe: removing the merge
    fails the new test on the stability sentence.
  * Isomorphism check across every aggregator: `capability`, `gage_rr`,
    `evaluate_plan`, `inspect_lot` and `apply_switching_rules` each build a
    single list and lose nothing; `stability` keeps two lists and the UI renders
    both. Box-Cox was the only one that aggregated and dropped.

- T-0065 (2026-09-02) **A two-digit study dimension ate the Gage R&R grid.**
  * Every keystroke in Parts / Operators / Trials resized the grid, clamping
    whatever stood in the box up to the minimum. Selecting "5" and typing "10"
    went through "1", which clamped to 2 and truncated the grid to two parts;
    the second digit then made it 20. Reproduced in a real browser before the
    fix: the field read 20, the grid had 20 rows, and part 3's measurements were
    gone. No undo, and the page ships pre-filled with the AIAG example.
  * The draft is now local text and the resize happens once, on blur or Enter.
    An out-of-range value is refused rather than clamped, so nothing is ever
    resized to a number nobody asked for.
  * **New constraint, stated rather than slipped in:** a dimension is capped at
    30. Three fields multiply, and an unbounded one turns a fat-fingered "1000"
    into a million inputs. Thirty is well above any real study (AIAG's example
    is 10 x 3 x 3).
  * The range hint lives inside the `<label>`, which would have joined the
    field's accessible name the moment it appeared -- caught by the e2e test,
    fixed with an explicit `aria-label`, the same guard the other panels use.
  * e2e test with a negative probe: against the old component it fails with the
    field reading 20.

- T-0066 (2026-09-02) **A rejected lot could claim acceptance at a tighter AQL.**
  `LotResult(accepted=False, accepted_at_tighter_aql=True)` is contradictory --
  a tighter AQL is the harder test -- but nothing checked it, and
  `_updated_score` asks the tighter-AQL question first. Three rejected lots
  scored 3 then 6: the switching score climbing on the evidence that should
  reset it. Validated in `__post_init__`; the router maps it to a 422 like every
  other domain error, and both non-contradictory combinations stay legal. The
  web page never sent it, so this was an API-client defect only.

- T-0067 (2026-09-02) **Ingestion failed silently on a German Excel CSV.**
  * A semicolon-separated file parsed as one text column and came back as "No
    numeric columns found"; a decimal comma turned the measurement column into
    text, which was then reported as an *ignored non-numeric column*. Telling a
    user their measurements are not numbers is the worst available answer, and
    both are what Excel writes in a German locale.
  * Now detected and **named in the response**: the separator, a cp1252
    encoding, a UTF-8 BOM, and a decimal comma converted per column. Detection
    without disclosure would have been the same class of bug one level down.
  * The separator is found by asking which candidate splits every sampled line
    into the same number of fields, using the csv module's quote-aware reader --
    deliberately not `csv.Sniffer`, which guesses from character frequency and
    is unreliable on short files. It gets the genuinely ambiguous case right:
    `"9,71",1` is comma-separated *and* comma-decimal.
  * The decimal repair fires only on a column that is entirely European
    decimals. A label column holding one numeric-looking entry stays a label --
    pinned by a test, because inventing measurements out of text is worse than
    ignoring the column.
  * Also: a multi-sheet workbook now says which sheet was read. Only the first
    ever was, and nothing said so.

- T-0068 (2026-09-02) **The pooled sigma's ceiling named the wrong quantity.**
  `_sigma_within` applies c4 at the pooled degrees of freedom, so c4's own guard
  surfaced as "subgroup size must be <= 100000, got 100003" for a study of
  subgroups of three -- a quantity the caller never supplied. It now reports the
  degrees of freedom and names the two within-methods that apply their
  correction at the subgroup size instead; the test checks that advice works.

- T-0069 (2026-09-02) **The zone-symmetry check tolerated real asymmetry.**
  `np.isclose` carries a default absolute tolerance of 1e-8, which is larger
  than an entire chart measured in nanometres or ppm: limits at -1e-9 and +3e-9
  are three times as far above the centre line as below, and the check called
  them symmetric. The run rules would then have derived sigma zones from a
  dispersion chart's limits. `atol=0.0` -- the relative tolerance is what the
  comparison always meant, and it still absorbs the last-ulp difference between
  `center + spread` and `center - spread`.

- T-0070 (2026-09-02) **Two unevaluated assumptions stayed silent.**
  * Below eight observations the normality assessment is skipped entirely and
    `normality` is None, while every index in the report goes on assuming a
    normal process. Silence read as "nothing to report"; nothing had been
    checked. The report now says which it is.
  * The short-series warning was gated on `n > 1`, so it never fired for
    individuals -- the case with no subgroup structure, where the estimates are
    *least* well determined. `i_mr_chart` warned about the same fifteen points
    all along; two reports on one series should not disagree about whether it is
    long enough.

- T-0071 (2026-09-02) **Refuted: the capability page's remount key.**
  Reported as a probable defect -- the key was column name + length + first
  value + last value, and two columns can share all four. **It does not
  reproduce**, and the measurement is the point: an e2e test that uploads a
  deliberately colliding second file passes against the old key too, because
  `UploadPanel` clears its selection before every request, so `column` passes
  through null and both panels unmount regardless of the key.
  The counter that replaced the fingerprint is kept as a simplification, not a
  fix: it makes the reset a property of the component rather than a consequence
  of how another one sequences its state. The test is kept because it pins that
  load-bearing behaviour, which nothing else did. Both the code comment and the
  test say all of this, so the next reader is not told a bug was fixed here.

- T-0072 (2026-09-02) **The docs and steering files had drifted from the code.**
  Nothing here changes behaviour; all of it changes what a reader is told.
  * `README.md`: status said v0.2.0 (shipped: 0.2.1); a paragraph said the run
    rules "are not in yet" three paragraphs above the section documenting them;
    the architecture block still marked `apps/web/` and `docs/` as `[later]`.
  * `capstat_core/__init__.py` said "Available today: descriptive, robust and
    normality" -- a bootstrap sentence outlived by ten modules.
    `control_charts.py` announced the run rules as arriving "in T-0009".
  * `PLAN.md` showed a subpackage layout (`capability/`, `control_charts/`,
    `msa/`, `distributions/`) that was never built. Replaced with the real flat
    one, and the deviation recorded with its reason rather than silently
    overwritten.
  * `TASK.md`: the Doing block claimed `/gage-rr` and `/msa` were not wired to
    the study file, three weeks after T-0041 wired them. The T-0063 /
    T-0058..T-0061 block appeared **twice**, byte-identical, and T-0062 appeared
    in both a short and a long form; one copy of each kept.
  * `STATE.md`: dated 2026-08-23, still said "Nothing is committed" of work that
    was merged that day in a44e184, and gave the goal as "released as v0.1.0".
  * `docs/validation.md` claimed 100 % coverage, which had drifted to 99.85 %.
    Restored to a measured 100 % instead of weakening the claim: the two
    uncovered lines got real tests, and the one genuinely unreachable defensive
    branch (`gage_rr.py`, a nan guard the upstream clamping makes impossible) is
    marked and now named in the docs.
  * **One review finding was itself wrong and is withdrawn:** the OpenAPI drift
    check is described accurately in both `README.md` and `AGENTS.md`. The
    semantic comparison is the schema check; the `git diff --exit-code` that
    AGENTS.md mentions is the TS-client check, which really does work that way.

- T-0062 (2026-08-23) **The switching-score restatement now names the reset.**
  The one finding the external review got wrong, and the sentence that caused
  it. 529 core tests.
  * The code was right: ISO 2859-1:1999 clause 9.3.3.2 keeps the score two ways
    -- for Ac >= 2 an accepted lot adds three *only* if it would still have been
    accepted one AQL step tighter and **resets to zero otherwise**; for Ac <= 1
    an accepted lot adds two. `LotResult`'s docstring said exactly that, and the
    reset case was already pinned by a test (`[3, 0, 3]`).
  * What was wrong was the restatement in the reference YAML, which said the
    score adds "three or two per accepted lot" and stopped -- readable as "an
    accepted lot can never lower the score". The review read it, compared it
    with the code, and reported the code. A restatement that omits a branch is
    not a shorter truth; it is a different claim.
  * **The prose is now the artefact under test.** A test asserts the note names
    the reset and both Ac branches, and re-checks that the behaviour it
    describes is the behaviour that runs. Source-text assertions are usually
    weak evidence -- here the text *is* the deliverable.
  * The review also claimed the existing test "pins the questionable behaviour
    and must be deliberately changed". It does not: it pins the standard.
  * Caveat unchanged and still worth stating: no licensed copy of ISO 2859-1
    was consulted. The judgement rests on code, docstring, reference YAML and
    the Annex A cross-check agreeing. The repo already carries that as an open
    gap and this does not close it.

- T-0061 (2026-08-23) **Deciding a lot judges the plan on screen.** The button
  was enabled on the defectives field alone while `decide()` read a plan rebuilt
  from the live inputs, so clearing "Sample size n" after judging left an
  enabled button that did nothing: no request, no message, no reason.
  32 e2e tests.
  * **Fixed the other way round from the review's suggestion, and better for
    it.** It proposed `disabled={!planValid || defectives == null}` plus a hint.
    But the block sits inside the report and is labelled "Decide a lot" -- *the*
    lot, the one the surrounding numbers describe. So the decision now takes
    `report.plan`, which is well-defined whenever the button is rendered. That
    removes the null case instead of guarding it, and it fixes a second
    inconsistency the review did not raise: editing n to a *different valid*
    value used to decide against the new plan while the report still described
    the old one.
  * The test asserts what reached the API, not just that something appeared --
    an assertion on the visible "Accept" alone passes with the bug present.
    (Confirmed the hard way: the first version of the test routed a URL that
    does not exist, recorded nothing, and still went green on the visible text.)

- T-0060 (2026-08-23) **The charts say what they show.** `control-chart.tsx`,
  `capability-histogram.tsx` and `oc-curve-chart.tsx` each returned a bare
  `<div>`; a screen reader got nothing for the central claim of every page.
  32 e2e tests.
  * Each now carries `role="img"` and a name built from the same props it draws,
    so the sentence cannot describe a different picture than the one rendered:
    "Individuals chart, 30 points, out of control at points 3, 6"; the histogram
    names its limits and target; the OC curve quotes the acceptance probability
    *read off the plotted curve* at both quality levels rather than recomputed.
  * `role="img"` deliberately stops a reader walking into the SVG, which is
    coordinates and no information.
  * Isomorphism: those three are the only graphics in the app -- no other
    `<svg>`, `<canvas>` or ref-mounted container exists, and the
    switching-scheme "marks" that looked like a fourth is a text parser.

- T-0059 (2026-08-23) **One API error path instead of eleven.** The same
  try/catch, the same fallback wording and the same red `role="alert"` box stood
  in nine components, already drifting. 65 vitest + 32 e2e.
  * `callApi(request, fallback, unreachable?)` reduces openapi-fetch's three
    outcomes to two, and `<ErrorAlert message>` is the one red box. After it:
    `role="alert"` markup exists in exactly one file and `describeApiError` is
    called from exactly one place. The only try/catch left in a component wraps
    `file.text()` -- a local file read, not a request, and rightly not shared.
  * **Not the `useApiCall` hook the review proposed, on purpose.** The panels'
    status unions genuinely differ -- one carries a result, one a report *and* a
    curve, the control chart keeps a second state for its rule run -- so a hook
    owning the state would force nine components into one mould for the sake of
    a shared try/catch, and would have to be threaded through T-0052's work.
    This shares the part that is actually identical.
  * The drifted wording turned out to be *right* where it drifted: the upload
    panel is a user's first contact with the API, so "is it running on the
    configured URL?" belongs there. It is now an argument rather than a reason
    to own a private copy of the whole path.
  * **Two faults fell out of the conversion.** In `upload-panel` the `try` also
    wrapped the code *after* success, so a fault in `looksLikeRowIndex` would
    have reported the API as unreachable. And the control chart's remaining
    `.catch` said "could not reach the API" for a case that can only be a state
    fault -- `callApi` is total. Both now say something true.
  * `callApi` also treats a 2xx with no body as a failure. That is the T-0052
    rule in one place instead of nine.

- T-0058 (2026-08-23) **The AIAG verdict is stated once, by the core.**
  `_verdict_warnings` held the 10/30 bands and ndc < 5, `grrTone` held 10/30
  again, and the ndc card held its own `< 5` -- so a threshold changed in one
  place would leave the card coloured by another, contradicting the warning
  printed beside it. 529 core + 63 API + 32 e2e.
  * The core exposes `GRR_GOOD_AT_OR_BELOW`, `GRR_MARGINAL_AT_OR_BELOW`,
    `NDC_MINIMUM`, and `GageRRReport.verdict` / `.ndc_adequate`. The warnings
    are appended after construction so they read the report's own %Study
    Variation and ndc instead of recomputing both -- two implementations of one
    number, which was the review's other half and correct.
  * `verdict` is `None` when there is nothing to judge (a gage with no variance
    of its own). That is not "good", and the old ndc colouring fell through to
    green there -- a clean bill of health for a study that established nothing.
  * The discriminating e2e serves a response whose percentage says "good" and
    whose verdict says "unacceptable"; the card must be red. A panel still
    owning the thresholds paints it green, and that test fails.
  * Verified as a single source rather than argued: changing only
    `GRR_MARGINAL_AT_OR_BELOW` to 25 moves the verdict *and* the warning text
    ("> 25%") together, and the UI follows because it colours by the word.
  * **Half the finding was wrong, and acting on it would have made things
    worse.** The review paired this with `indexTone`'s 1.00/1.33 in
    `capability-dashboard.tsx` as the same duplication. It is not: the core
    contains no capability-index threshold anywhere, deliberately -- what counts
    as a capable process is a customer's specification, not a library's opinion.
    "De-duplicating" it would have meant *inventing* a judgement capstat refuses
    to make. Left alone; see the open question below.
  * Isomorphism over the sibling tone functions: `severityTone` already colours
    by the core's own words and is the model this moves towards; `riskTone`
    compares an achieved risk against *the user's own requested* risk, so it is
    not a threshold at all; `indexTone` is the one above. No fourth case.
  * **Open, and a decision rather than a task:** should the capability page
    colour by 1.00/1.33 at all? Today the UI asserts a verdict the library
    declines to assert. Either the thresholds become configurable input (a spec
    limit is customer-specific), or the colouring goes, or capstat states the
    convention explicitly and owns it. Recorded here rather than settled.

- T-0057 (2026-08-23) **Muted text is a measured token now, not an opacity
  guess.** `text-foreground/40` resolved to #a2a2a2 on white -- 2.55:1, against
  the 4.5:1 WCAG 2.1 AA asks for small text -- and it was carrying the *names of
  the numbers* ("Producer risk", "ndc"), not decoration. 59 vitest + 26 e2e.
  * `--muted` is defined per theme with the ratio in the comment: #6b6b6b light
    (5.33:1), #8a8a8a dark (5.73:1), #595959 print (7.00:1). A named token
    rather than an alpha because a token can be *measured*: `lib/contrast.test.ts`
    reads the values out of `globals.css` and does the WCAG arithmetic, so a
    future colour edit is checked rather than trusted.
  * 51 occurrences replaced across ten components. The boundary was computed,
    not eyeballed, and it is not where intuition puts it: /40, /45 and /50 fail,
    /60 (4.67:1) and /70 pass -- and /50 *passes in dark and fails in light*, so
    "it looks fine" was never evidence. That table is pinned by a test.
  * A guard test walks the `.tsx` sources and fails on any `text-foreground/N`
    below 60, because fixing 51 sites is worth little if the 52nd can be added
    unnoticed.
  * **Verified in the browser, not only in the source.** The first build showed
    no `.text-muted` rule at all and a surviving `.text-foreground\/40` -- which
    would have meant 51 labels silently inheriting full foreground while every
    test stayed green. It was a stale `.next` cache; a clean rebuild emits
    `.text-muted{color:var(--muted)}` and all three token values. Then measured
    live on `/acceptance-sampling`: 15 elements, computed colour
    rgb(107,107,107) on rgb(255,255,255) = **5.33:1**, and rgb(138,138,138) on
    rgb(10,10,10) = **5.73:1** in dark. Source-level tests could not have caught
    a token that never reached the page.
  * One knock-on: naming the old class in a doc comment made Tailwind scan it
    and emit the very utility the guard forbids. The comment now spells it out
    in words.

- T-0056 (2026-08-23) **An oversized upload is refused before it is resident.**
  `/ingest` read the whole body with `await file.read()` and compared the length
  afterwards, so the guard delivered the right status code and none of the
  protection its comment promised. 63 API tests, mypy strict clean.
  * The body is now read in 1 MiB chunks and refused at the first chunk crossing
    `MAX_BYTES`, so at most one chunk past the limit is ever held. Starlette
    spools the part to disk beyond 1 MiB (`spool_max_size = 1048576`, verified
    on the installed 1.3.1), so what the old code did was pull a disk-backed
    body into a single Python `bytes` -- which is the cost worth stopping.
  * `Content-Length` is deliberately *not* the mechanism: a chunked upload sends
    none, and a lying one is the case worth defending against. It could only be
    an early exit on top of the chunking, never a replacement.
  * The test measures what was actually read rather than the status code, via a
    recording stand-in for `UploadFile` -- the status code was always right, so
    asserting on it proves nothing about the fix. Negative probes: restoring the
    whole-body read fails it, and dropping the final partial chunk (the classic
    chunking off-by-one) fails six tests including a new one that reads a body
    at the limit with a chunk size chosen not to divide it.
  * **Isomorphism check found something bigger: see T-0063.** The compute
    endpoints have no size limit at all -- a 9.5 MB body of 2,000,000 floats
    returns 200. Filed rather than fixed here, because the cap is a contract
    decision.

- T-0055 (2026-08-23) **A hand-edited study file can no longer crash the page it
  is loaded into.** `parseStudyFile` checked that `inputs` was an object and
  then cast it unchecked, so `{"grid": 1}` reached `grid.map` and took the page
  down with an unhandled TypeError. 59 vitest + 26 e2e, tsc and eslint clean.
  * Each page now supplies a reader that rebuilds `inputs` field by field --
    which is what the module already did for the document's *outer* fields and
    documents as its rule; the inner object was simply exempt.
  * **Refuse, do not half-restore.** A wrong-typed field stops the load with the
    field named; the alternative (substituting a default) would put a value on
    screen that nothing distinguishes from a loaded one. Absent fields stay
    tolerated -- the MSA page relies on that to read studies written before one
    of its sections existed -- so the rule is: missing is fine, present and
    wrong is not.
  * Fault paths are composed on the way *out*: each reader that descends
    re-throws with its own key in front, so a bad cell reports "grid.0.0.1" and
    the reader that wrote it never had to know where it sits. Pinned by a test.
  * **`readInputs` is a required prop on `StudyFileControls`, not an option.**
    That is the part that makes it stick: a fourth page cannot mount the
    controls without a reader, because it will not compile.
  * Isomorphism: the other casts in the web app are `e.target.value as
    GageRRMethod` and `as SamplingModel` on `<select>`s whose options the
    component itself renders (the value cannot be anything else), `file as
    unknown as string` in the API client (an openapi-fetch multipart typing
    workaround, not a shape assumption), and `value as T` inside `readChoice`
    immediately after checking membership. None is a trust boundary carrying
    user-editable data. The study file was the only one.

- T-0054 (2026-08-23) **A target given to the percentile path is reported rather
  than swallowed.** The normal and Box-Cox paths feed `target` into Cpm; the
  percentile path dropped it with no mention in `rationale` or `warnings`.
  524 core tests, mypy strict clean.
  * The warning names the number and the reason: Cpm needs a short-term sigma,
    which the percentile method does not have. Not computing it is a fine
    answer; not saying so is not. The warning reaches the browser -- the API
    schema passes `warnings` through and the dashboard renders them.
  * A second test pins that the *other* two paths gain no such warning, since
    they use the target and a warning there would be noise.
  * Isomorphism: `alpha` is the only other caller input crossing this dispatch,
    and it is consumed on all three paths -- it decides the routing via
    `assess_normality`. Where it does less (no confidence intervals on the
    percentile path) the result type says so by having no such fields.
    `target` was the only input that could vanish without a trace.

- T-0053 (2026-08-23) **The sampling-plan search no longer mistakes its own
  overshoot for an impossible design.** `design_single_sampling_plan` bracketed
  the smallest `n` by doubling; when the probe stepped past `max_sample_size`
  (implicitly the lot size) the whole acceptance number was abandoned, and with
  it every higher one. 522 core + 61 API tests, mypy strict clean.
  * **A probe that oversteps a ceiling says nothing about whether the answer
    fits under it.** That is the whole defect in one sentence. The doubling is
    now clamped to the ceiling, and only a genuine miss at the clamped value
    retires an acceptance number.
  * **The review found the loud half; sweeping the fix found the quiet half.**
    Over a 245-case grid of (AQL, LTPD, lot size): 11 cases went from
    `ValueError` to a valid plan, and **5 more had been returning a plan that
    was valid but too large** -- 2 % against 10 % in a lot of 80 gave n=78,
    Ac=4 where n=65, Ac=3 suffices. The function's contract says *smallest*.
    Inspecting thirteen extra items per lot with nothing in the output to say
    so is the worse of the two failures, and it is the one nobody reported.
  * All 16 changed results were checked against an exhaustive scan of
    (Ac, n) -- every one is both feasible and minimal, no mismatches.
  * The two pinned infeasible cases were re-derived by brute force before
    touching the search, to be sure they pinned a real limit and not this bug.
    They do: 1 % vs 3 % in a lot of 200, and 1 % vs 1.01 % at 1 % risks, have no
    plan under their stated bounds.
  * Isomorphism: one sibling search, `quality_at_acceptance`, bisects on `p`
    over a fixed [0, 1] bracket with the degenerate case handled before the
    loop. It has no growth probe and no ceiling to overshoot, so it cannot carry
    this defect. No other bracketing search exists in the core.

- T-0052 (2026-08-23) **The control-chart panel no longer reports a clean
  process it never checked.** A failed `/rules/nelson` call landed as
  `res.data ?? []`, and the panel printed "No Nelson run-rule violations
  (rules 1-4)". 24 e2e + 47 vitest tests, tsc and eslint clean.
  * The rule run now carries its own status (`done` / `error`) beside the chart
    it belongs to, so an empty list can only ever mean "the rules ran and found
    nothing". On failure the panel says the rules could not be applied and
    passes the API's own `detail` through.
  * **A second, quieter instance of the same thing turned up while fixing it:**
    the panel also claimed "no violations" *while a run was still in flight* --
    on first render and after every change to the rule selection. The stored
    result is now keyed by chart *and* rule selection, both by reference, so an
    unfinished run reads as "applying…" rather than as a verdict. The existing
    selection test documented this in passing ("the label is rendered from the
    checkbox state, not from the response") without treating it as a fault.
  * Isomorphism: one other place coerces a failure into a benign value --
    the rules *catalogue* fetch, where a failure leaves the descriptions empty
    and rule labels fall back to the rule number. That one is sound and stays:
    it degrades a *label*, not a *verdict*; the violations themselves are still
    whatever the API returned. No other component prints a negative finding
    from an unverified empty result -- the `warnings.length > 0` blocks
    elsewhere all hide a section rather than assert that nothing was found.

- T-0051 (2026-08-23) **The k-of-m run rules no longer swallow a pattern that
  completes at the start of a series.** From an external review (Ox Alpha,
  2026-08-22) that read the source and nothing else -- and found a decision this
  file recorded as settled. `_k_of_m_beyond` gated on the last point of the
  m-window qualifying; the signal belongs on the last *qualifying* point.
  520 core + 61 API tests, mypy strict clean.
  * **The gate was redundant everywhere except at the start of the series, and
    measuring that mattered more than fixing it.** Old and new agree exactly on
    100,000 simulated in-control points -- not approximately, exactly. An
    exhaustive differential over all 3^6 + 3^7 sequences of {below, inside,
    beyond} shows signals are only ever added, never removed, and always at
    point m-2 (point 1 for 2-of-3, point 3 for 4-of-5). Whenever the last
    qualifying index reaches m-1, the window ending on it exists and the old
    code caught the pattern anyway.
  * So the defect is exactly: **a process already out of control when the chart
    starts does not signal.** Narrow, and worth fixing -- a new process on its
    first chart is where the first alarm earns its keep. The review stated this
    as "sequences like [2.5, 2.5, 0.1, ...] never trigger", which is true of
    that sequence and overstates the class.
  * **Deduplication had to come with it.** Without the gate, three consecutive
    points beyond 2 sigma complete in two overlapping windows that both resolve
    to the same signal point. Windows are now keyed by their signal point,
    earliest kept -- it carries the fullest run. The all-points rules
    (`_runs_on_one_side`, `_monotone_runs`, `_alternating_runs`, Nelson 7 and 8)
    need no such thing: there the qualifying set *is* the window, so "last
    qualifying" and "window end" coincide by construction. That is also the
    isomorphism check -- five sibling loops, none of them able to carry this
    defect, and their overlapping windows produce genuinely distinct signal
    points rather than duplicates.
  * The false-alarm reference case (`rules.yaml`, `false-alarm-rates`) is
    unmoved: Nelson 0.0216, Western Electric 0.0164, both inside the pinned
    figures. The `eight-versus-nine-on-one-side` case is untouched by
    construction -- it exercises a run rule, not a k-of-m one.

- T-0050 (2026-08-16) **The Next-generated agent files are gitignored, and the
  part of them worth keeping was rewritten in our own words.** Next 16.3 writes
  `apps/web/AGENTS.md` and `apps/web/CLAUDE.md` from `next dev` when it detects
  an AI coding agent (`determineAgent()`, `dist/telemetry/agent-name.js`), and
  Playwright's `webServer` runs `next dev` -- so any agent session running the
  e2e suite recreates them.
  **Why not commit them.** They appear only in agent sessions, never in CI and
  never for a contributor working without one, so tracking them would make the
  file set depend on who was typing. Their text points at
  `node_modules/next/dist/docs/`, which is meaningless when read on GitHub. And
  the block is rewritten by upsert on Next upgrades, but only if someone happens
  to run `next dev` with an agent attached -- so a committed copy would drift
  silently. Against all that, the root `CLAUDE.md` calls `AGENTS.md` "the single
  source for project conventions", and a second, tool-authored one sits badly
  beside that claim.
  **Why not just ignore them either.** The advice itself is correct: Next 16 does
  diverge from training data, and `AGENTS.md` said nothing about it. So the
  substance now lives in the root `AGENTS.md` under Hard rules, in our wording,
  pointing at the same docs directory and naming the gitignored files so nobody
  has to re-derive where they came from.
  **The instruction inside the file was not the reason for either decision.** It
  says committing it "keeps the tree clean" -- an argument from the tool for its
  own inclusion, which `.gitignore` satisfies just as well without taking foreign
  text into the repo. Whether the content belongs here was decided on its merits.
  Isomorphy check on the class -- tools writing unowned files into the tree: the
  only `AGENTS.md`/`CLAUDE.md` pairs in the repo are the root one (maintained)
  and this one (now ignored); nothing else is untracked. The generated
  `lib/api-client/schema.d.ts` is the deliberate opposite case -- tracked *and*
  guarded by `npm run check:api`, because there the artifact is a contract.

- T-0048 (2026-08-16) **The dependency backlog cleared: nine open PRs merged,
  release 0.2.1 cut.** #14 fastapi, #13 ruff, #12 pre-commit, #10 uvicorn, #8
  mkdocstrings, #7 setup-buildx, #5 build-push, #6 release-please-action, and the
  release PR #16 last, so it carried everything. `v0.2.1` is tagged; nothing was
  published to PyPI (publish.yml is dispatch-only, and 0.2.1 contains no library
  code).
  **I broke `main` in the middle of this, and the cause is worth keeping.**
  Merging #13 (ruff 0.15.21 -> 0.16.0) turned CI red. 0.16 began formatting
  Python code blocks *inside Markdown*, and three documents disagreed with it --
  README.md, docs/getting-started.md, docs/methods/acceptance-sampling.md. Not
  one Python file was affected.
  The failure was avoidable and I had already avoided it once that hour: on #6 I
  checked whether the green run still described the current `main` and found the
  checks were four weeks old. On #13 I did not check. The tick was real; what it
  had been green against was not this tree. **A Dependabot PR's checks age
  exactly like a release PR's** -- the memory `release-pr-checks-are-held` says
  so for release PRs, and I failed to generalise it.
  **The fix was not to accept the reformatting.** Those snippets align trailing
  comments into columns so a reader can scan value against explanation, and 0.16
  collapses that to one space; worse, it reads a wrapped comment as a new
  statement, turning a continuation line into an unrelated top-level comment. So
  `[tool.ruff.format] exclude = ["*.md"]` -- format-scoped, not a blanket
  `extend-exclude`, so linting still covers those blocks. Prose is written for
  people; the formatter does not own it.
  **#10 was innocent, and only a re-run established that.** Its rebased run
  failed one Playwright spec, which looks damning for a uvicorn bump. It was the
  same ruff step for the first failure, and after the fix a single flaky
  assertion for the second -- green on re-run. Merging on the red tick would have
  been right by accident; rejecting the PR would have been wrong. Neither
  reading was available without re-running it. Flake filed as **T-0049**.
  Also of note: the release PR's checks were held at `action_required` for the
  fourth time today. That trap is now routine to handle and cost nothing.

- T-0046 (2026-08-16) **16 open Dependabot alerts to zero, and `npm audit` clean
  with it.** All of them were in `apps/web`; `capstat-core` was never affected,
  since it depends on numpy and scipy alone.
  **Dependabot PR #15 did the bulk: 16 down to 2.** It closed `next` (9),
  `postcss` (4) and `sharp` (1) at once, because `next` 16.3.1 carries fixes for
  four high advisories (a DoS in Server Actions, a middleware/proxy bypass, and
  two SSRFs) plus five moderate ones.
  **Its description was wrong about the one thing that mattered.** The body
  promised `next 16.2.10 -> 16.2.11`, a patch; the diff set **16.3.1**, a minor.
  Read the diff, not the summary -- the whole reason T-0046 said "re-measure
  rather than trust the PR description". The minor turned out to be safe, but
  that was established by running the suite, not by reading.
  **The remaining two needed work Dependabot had not offered.** Both were
  transitive: `nanoid` 3.3.16 (runtime, via postcss, pulled in twice -- through
  Tailwind and through Next) and `js-yaml` 4.3.0 (dev, via eslint and
  openapi-typescript). An override already existed for js-yaml at `^4.3.0`, which
  permits 4.3.1 -- only the lockfile had never moved. Now `^4.3.1`, plus a new
  `nanoid` override at `^3.3.18`.
  **`npm audit` and Dependabot did not agree**, which is worth remembering:
  after those two were fixed, Dependabot showed zero while `npm audit` still
  reported a high-severity `brace-expansion` DoS across eight paths, every one of
  them dev-only. `npm audit fix` (no `--force`, so semver-compatible only)
  cleared it in 8 packages. Checking one source and declaring victory would have
  left it standing.
  **Also fixed, unprompted by any alert:** `eslint-config-next` was still pinned
  to `16.2.10` while `next` had moved to `16.3.1`. Dependabot bumped one and not
  the other, which means linting against a different Next than the build uses.
  Verified: lint, `format:check`, 47 vitest, the OpenAPI drift check, `next
  build`, and 23 Playwright specs -- all green, and `npm audit` reports 0.

- T-0045 (2026-08-16) **`publish.yml` publishes a tag, not a branch.** Written
  the same day the gap nearly cost a permanent mislabelled release (see T-0030).
  `workflow_dispatch` now takes a required `tag` input, checkout uses
  `ref: ${{ inputs.tag }}`, and the verify step compares the built version
  against the **tag name with `v` stripped**.
  **Two independent defences, and the first one is the real fix.** Checking out
  the tag makes the drift structurally impossible: the version can no longer come
  from a different commit than the code. The comparison is the second line, for a
  tag that was set inconsistently in the first place. The old step had neither --
  it read `dist/` and `capstat_core.__version__`, both out of the same tree, so
  it agreed with itself while being wrong for the release being cut.
  **The tag input goes through `env:`, not into the script body.** A
  `workflow_dispatch` input interpolated directly into `run:` is executed as
  shell; `env: TAG: ${{ inputs.tag }}` is not. Same reason the input is required
  with no default: a typo must fail the checkout rather than quietly fall back
  to something publishable.
  Verified by extracting the comparison and running it against four cases, since
  the workflow itself cannot be exercised without publishing: the 2026-08-16
  situation (`v0.1.0` vs package 0.2.0) exits 1; a correct release passes; an old
  tag with its own old code passes, which is right, because checking out the tag
  is what makes that combination consistent; a mistyped tag exits 1.
  Not touched deliberately: `publish.yml` still pins `actions/checkout@v4` and
  `astral-sh/setup-uv@v6` while `ci.yml` runs `@v7` on both, the latter with a
  comment explaining why it stops there. Bumping them is right, but this is the
  one workflow that cannot be tested before it matters, so it wants its own
  change rather than a drive-by inside a correctness fix. Filed as T-0047.

- T-0030 (2026-08-16) **capstat-core 0.2.0 is on PyPI.** Triggered by PyPI
  mailing that the pending trusted publisher would expire in 5 days if unused --
  which is a deadline to publish *something*, not a licence to publish anything.
  `pip install capstat-core` now works; the OIDC trust path held, so no API
  token was ever created, stored or rotated.
  **The trap, one step from firing.** The instruction was "publish now". Had I
  done that, PyPI would hold a permanent artifact called **0.1.0 containing the
  code of 0.2.0**: the tag `v0.1.0` pointed at `9e2d97f`, `main` stood 20 commits
  further along, 6 of them touching `capstat-core` and 5 of those `feat:`.
  `publish.yml` runs `actions/checkout@v4` with no `ref`, so it builds `main`,
  while the version string comes from `pyproject.toml`, which only moves when
  release-please releases. The mismatch would have been uncorrectable: a yanked
  version can never be re-uploaded.
  **The workflow's own guard does not catch this**, despite its comment naming a
  wrong version as "the one mistake trusted publishing cannot catch". It compares
  `dist/` against `capstat_core.__version__` -- both said 0.1.0, so the check
  passes while being wrong. It verifies *consistency*, not *correctness*. The fix
  was already sitting there: release-please PR #4, open and mergeable, bumping to
  0.2.0 exactly as ten `feat:` commits require.
  **Both traps from the release-flow memory fired again, as documented.**
  `gh pr checks 4` reported "no checks reported" -- not missing CI but a run held
  at `action_required`, needing `gh api -X POST .../approve`. And before merging,
  the run's `head_sha` was compared against the live PR head (`c20a34c` both):
  release-please rebuilds the PR whenever `main` moves, so a green tick can
  belong to a superseded head. Neither cost anything this time *because* they
  were written down last release.
  **Verified after the fact, not assumed:** PyPI's JSON API reports 0.2.0, MIT,
  `>=3.11`, dependencies exactly `numpy>=1.26` + `scipy>=1.11` (the core's
  web-freedom survives into the published artifact), and `0.2.0` as the only
  release -- 0.1.0 was never burned. Then a real install from the network into a
  clean venv, an import, and a computation: `Pa(0.1) = 0.81` for n=2, c=0, which
  is `(1-0.1)^2` by hand, plus lot decisions accepting 0 and rejecting 1
  defective. The 13 acceptance-sampling symbols are present, which is what proves
  the artifact carries 0.2.0's code rather than 0.1.0's.
  **Also fixed, same error class as T-0042** (documentation asserting a state
  that does not exist): the README said "capstat is not on PyPI", offered only a
  from-source install, and opened Usage with "Available today: descriptive
  statistics and robust estimators" -- an M1 sentence still standing above nine
  sections that run through to acceptance sampling.
  Follow-up filed as T-0045: `publish.yml` should build the release tag, not
  `main`. Today they coincide; the gap reopens the moment `main` moves ahead.

- T-0043 (2026-07-23) **Discussions enabled; the issue template's question link
  works again.** `.github/ISSUE_TEMPLATE/config.yml` had offered "Question or
  discussion" pointing at `/discussions`, which returned 404 -- invisible while
  the repo was private, the first thing a visitor met after the public flip.
  Decided in favour of enabling (not of dropping the link), because
  `blank_issues_enabled: false` means the three issue templates are the only way
  in, and none of them fits a plain usage question: without a question channel,
  visitors would have been pushed to file understanding questions as bug reports.
  Verified: `hasDiscussionsEnabled: true`, `/discussions` -> HTTP 200.
  **Open follow-up:** GitHub created six default categories (Announcements,
  General, Ideas, Polls, Q&A, Show and tell). "Ideas" duplicates the existing
  `feature_request.yml` template, and Polls/Show and tell presuppose a community
  that does not exist yet. Pruning to Q&A + Announcements would keep one funnel
  per purpose; left as the maintainer's call.
- T-0044 (2026-07-23) **SECURITY.md's preferred reporting channel now exists.**
  The file named GitHub private vulnerability reporting as the *preferred* way to
  report a flaw, but the feature was disabled on the repo -- harmless while the
  repo was private, a dead end for a responsible reporter once it went public.
  Enabled via `gh api -X PUT repos/Xindaan/capstat/private-vulnerability-reporting`;
  verified `enabled: true`. No document was weakened: the promise was the right
  one, the repo simply had not been configured to keep it. Found by auditing what
  the public flip exposed, not by anyone hitting it.
- T-0042 (2026-07-23) **Prettier, a gate the control files had been claiming
  for months without it existing.** Found by auditing the repo against the
  original kickoff brief, which listed Prettier twice: frontend tooling and
  pre-commit. Neither was there -- no config, no dependency, no script, no
  hook. `npm run lint` was bare eslint, so TS/TSX formatting was checked
  nowhere. Meanwhile `AGENTS.md` listed prettier under "Quality gates (CI must
  stay green)" and `PLAN.md` under both the frontend stack and the pre-commit
  hooks. The formatting that did exist came from the maintainer's editor
  running Prettier with defaults -- which is why only 6 files needed rewriting,
  and also why STATE.md has an entry about "Prettier kept reformatting the fix
  away". An unversioned tool was silently shaping the tree.
  Now real: `apps/web/.prettierrc.json` (Prettier 3 defaults pinned
  explicitly, so a future major cannot silently reformat the tree),
  `.prettierignore`, `format` / `format:check` scripts, a CI step in the web
  job, and prettier + eslint pre-commit hooks. 578 Python tests, 47 vitest,
  eslint and both drift gates green.
  Three things worth keeping:
  **(1) The generated TS client had to be excluded, or the fix would have
  broken a different gate.** `lib/api-client/schema.d.ts` is emitted by
  openapi-typescript and guarded by `npm run check:api`, which regenerates it
  and runs `git diff --exit-code`. Prettier's first pass flagged it. Had it
  been reformatted, the committed file would no longer match a fresh
  generation and the drift check would fail on every run -- a formatting
  change silently disabling a contract gate. Verified both directions: without
  `--ignore-path` the file is flagged, with it the check passes.
  **(2) `printWidth` stays at Prettier's 80, not ruff's 88.** 88 would have
  matched the Python side and reformatted 20+ files; 80 matches what is
  already on disk and touched 6. Cross-language symmetry is not worth that
  much churn in a diff nobody can review line by line.
  **(3) The pre-commit hooks needed two different workarounds, both load-
  bearing.** pre-commit runs from the repo root, where Prettier would not find
  `apps/web/.prettierignore` -- hence the explicit `--ignore-path`, without
  which the hook reintroduces problem (1) on every commit. eslint's flat
  config is discovered from the working directory rather than from the linted
  file, so its hook has to `cd` into `apps/web`, which makes the repo-relative
  filenames pre-commit passes useless -- hence `pass_filenames: false` and
  linting the whole app. Both are commented in place; they look like
  overcomplication otherwise.
  **Isomorphy check** (the class: control files asserting a gate that does not
  exist). Every other gate claimed in AGENTS.md and PLAN.md was verified
  against the actual config, and the coverage gate additionally by running a
  deliberate partial suite to confirm it fails rather than merely being
  configured (`FAIL Required test coverage of 95.0% not reached`). ruff
  lint+format, mypy --strict, coverage >= 95, tsc via `next build`, vitest,
  Playwright and the two drift gates are all genuinely enforced. Prettier was
  the only false claim.
  Also fixed in passing: `CONTRIBUTING.md` "Before you push" listed only the
  Python gates, so a web-only contributor was told to run none of the gates
  their change would actually hit.

- T-0037 (2026-07-21) **Acceptance sampling reaches the app.** Four routes --
  `/compute/acceptance-sampling/{evaluate,design,oc-curve,inspect}`, one per
  core entry point -- plus an `/acceptance-sampling` page that designs a plan
  from two risk points, draws the OC curve with both quality levels on it, and
  decides a lot from an observed defect count. 547 Python tests (491 core + 56
  API), **100 % coverage on both packages**, 37 vitest, 14 Playwright specs, and
  both drift gates green.
  Three things worth keeping:
  **(1) An inconsistency in my own T-0035 code, found by comparing against the
  neighbours rather than by a test.** `OCCurve` exposed numpy arrays where every
  other public core dataclass exposes `tuple[float, ...]` -- a frozen dataclass
  holding a mutable array is frozen in name only, and the API would have had to
  know about numpy to serialise it. Changed in the core, not patched in the
  schema.
  **(2) The OC chart's markline labels rendered rotated 90 degrees and clipped.**
  A markLine label inherits its line's direction; these lines are vertical,
  unlike every markline in the control chart, so `position: "insideEndTop"`
  turned "AQL" on its side. Found by looking at the page in a browser against
  the real API -- no test would have said a word.
  **(3) The screenshot script silently skipped its own chart wait.** `shoot()`
  guarded the wait with `if (await panel.locator("svg").count())`, evaluated once
  and immediately -- but ECharts is imported lazily, so at that moment the count
  is zero and the poll never runs. It photographed an empty chart box. `shoot()`
  now takes `chart: true` and waits for the element to attach; the three
  chart-bearing captures pass it. The existing figures were correct only by
  luck of timing.
  One e2e flake seen once (`smoke.spec.ts` run-rules, during the first run after
  adding the route, when Next was compiling it under parallel load); not
  reproducible in two subsequent full runs, and CI retries once.

- T-0039 + T-0040 (2026-07-21) **Declined, by decision, with the reason
  recorded.** Multi-user auth and persistence/database were two of the four
  themes bundled in the old T-0018. Both are closed *unbuilt*, because both
  would reverse T-0026: capstat runs on the maintainer's own machine and holds
  no data between requests, so there are no accounts to separate and nothing
  to protect that the filesystem does not already protect. Adding auth would
  first require adding the thing auth protects -- a server holding other
  people's measurement data. Statelessness here is a stated property of the
  product, not an unfinished edge, and the README says so.
  What survived: the narrow carve-out, now **T-0041** -- saving a study as a
  JSON file the user owns. That is a file format, not persistence.

- T-0035 (2026-07-21) **Acceptance sampling in the core.**
  `capstat_core.acceptance_sampling`: single sampling plans by attributes as a
  computed object -- the OC curve under three models (binomial / hypergeometric
  / Poisson, the last offered explicitly and never applied silently), AOQ, the
  AOQL *found by searching the curve* rather than read off a grid, ATI, the
  producer's and consumer's risks, the inverse OC (limiting and indifference
  quality), the lot decision, and two-point plan design. 44 tests, core at
  **100 % coverage, 491 core + 48 API green**, ruff and mypy --strict clean.
  **Validation turned up four inconsistencies in the NIST handbook's own
  tables**, all reproduced and explained instead of tolerated: its AOQ column
  is computed with the `Pa*p` approximation the same page contradicts one
  paragraph above; its p=0.03 row comes instead from the page's prose example
  (a different formula again); its first AOQ entry prints 0.0010 where the
  formula gives 0.0100, the digits transposed, a factor-of-ten error; and its
  ATI column is truncated, not rounded. The AOQ and ATI columns are now
  asserted **without any tolerance on the published digits** -- `round(Pa*p, 4)`
  reproduces ten of twelve rows exactly, and each ATI entry must equal `floor`
  or `round` of ours. That is a stronger claim than any tolerance would be.
  Three independent implementations were found that print eight significant
  digits where the handbook prints three -- the R packages *AcceptanceSampling*
  and *AccSamplingDesign*, and Minitab's worked example -- and capstat
  reproduces every digit of all of them, including both designed plans
  (n=80/c=7 and n=144/c=4, asserted exactly, because a plan is a decision) and
  Minitab's AOQL of 2.603 % *at* 4.3 % defective, which is the only independent
  check found on the maximisation rather than on the AOQ formula.
  **Two bugs of my own, both found by tests that failed for the right reason:**
  the design search built candidate plans with `n` larger than the lot and died
  inside the constructor with a message about an internal probe ("lot_size
  (200) must be at least sample_size (256)") -- the sample size is now capped at
  the lot up front, since you cannot inspect more items than exist; and the
  Type A path silently accepted quality levels a finite lot cannot express (a
  lot of 50 cannot be 1 % defective), which made the producer's condition
  vacuous and the resulting plan meaningless. It now refuses to design against
  such a level and reports the realised one when merely evaluating.
  **One gap, named rather than hidden:** no published Type A worked example
  with an acceptance number above zero exists in the sources found -- every one
  was c=0, which collapses the sum to a single term. That path is validated
  against scipy plus a hand-written combinatorial enumeration, and the
  reference file says so.

- T-0024 (2026-07-21) **Run-rule selection.** The control-chart panel applied
  Nelson rules 1-4 with no way to change them. Now all eight are checkboxes,
  defaulting to 1-4, with the descriptions *fetched* from `/rules/catalogue`
  rather than copied into the front end -- a second copy of the wording would
  be free to drift from the rules actually applied.
  Three things the feature had to get right, none of them the checkbox:
  * **The report names the set it used.** "No violations" is not a statement
    about a process unless you know what was looked for. A gapped selection is
    listed (`1, 3`), never collapsed into a range that would claim rules were
    applied that were not. Pinned by `lib/rules.test.ts`.
  * **Selecting beyond the default says what it costs**: T-0009 measured the
    full set signalling ~8x as often as rule 1 alone on in-control data.
  * **Violations are stored with the chart they were computed from.** Without
    that tie, switching column would briefly paint the previous column's flags
    onto the new chart -- points marked out of control that are not.
  The chart fetch and the rules fetch are separate effects, so changing the
  selection does not recompute the control limits.
  Verified against the real API in-browser (label, catalogue wording, the
  gapped case) as well as by an e2e test that asserts the selection actually
  reaches the API -- a panel that rendered a selection it did not apply would
  be the whole failure mode.

- T-0022 (2026-07-21) **starlette TestClient deprecation resolved**, not
  deferred: `httpx2>=2.7` is published, TestClient prefers it when importable,
  and adding it to the dev group silenced the warning. The suite is now
  **warning-free** (496 tests, 0 warnings); previously every run carried one.
  Both httpx and httpx2 are listed while the transition is in flight.

- T-0021 (2026-07-21) **scipy 1.19 readiness -- and a correction to this task's
  own plan.** The entry said to pin Stephens' critical values into the reference
  YAML "instead of reading them from scipy". That would have been wrong: the
  test's value is that it compares *our* table against scipy's independently
  stored one, so pinning scipy's numbers into our YAML turns a cross-check into
  a self-comparison. Done instead:
  * A new test holds the alpha = 0.05 value to the **NIST handbook** (0.752),
    an outside source that survives scipy dropping the attributes.
  * The scipy cross-check keeps running while it can and `pytest.skip`s with a
    reason when the attributes vanish -- it stops corroborating rather than
    failing or silently degrading.
  * The module-wide warning filter is gone, narrowed to the one test that needs
    it. Removing it revealed the warning comes from the `stats.anderson()`
    *call*, not from touching a deprecated attribute -- so the statistic-only
    cross-check now passes `method="interpolate"`, which is warning-free and
    1.19-proof. Isomorphie-Check: one remaining site, correctly scoped.

- T-0023 (2026-07-21) **npm audit: 2 high fixed, 2 moderate deliberately not.**
  The entry described 2 moderate advisories; there were 4 by now, two of them
  high (js-yaml quadratic-CPU via `@redocly/openapi-core`, a dev-only path).
  js-yaml 4.3.0 fixes it and satisfies redocly's `^4.1.0`, so an `overrides`
  entry clears both -- verified by regenerating the TS client, which came out
  byte-identical.
  The postcss pair stays: `next` pins postcss to the *exact* version 8.4.31, so
  an override would deviate from what Next bundles and tests, and next 16.2.10
  is already the newest release. The advisory is an XSS in CSS stringify output
  on a build-time path over our own CSS. Revisit when Next bumps its floor;
  `npm audit fix --force` would downgrade next to 9.3.3 and must not be run.

- T-0031 (2026-07-21) **README screenshots** -- four figures (capability,
  I-MR control chart, Gage R&R, the row-index warning), plus the status block
  corrected to v0.1.0 and "no hosted demo" reframed as the deliberate choice it
  is rather than a gap.
  The objection this task carried -- binaries that go stale whenever the UI
  moves -- was answered by making the capture a script instead of handwork:
  `npm run screenshots` (`apps/web/screenshots/capture.spec.ts` +
  `playwright.screenshots.config.ts`). It runs the **real** API, not the mocked
  stack the e2e suite uses, so every number in the README was computed by the
  validated core from `examples/shaft-diameter.csv`. A project claiming
  reference-validated results must not illustrate itself with invented ones.
  Kept out of CI: it needs Python + the app, and the figures change only when
  the UI does. The main playwright config's `testDir: ./e2e` already excludes
  it -- verified, `npm run test:e2e` still collects exactly 8 tests.
  Three bugs found while writing it, two mine and one the app's:
  1. `boundingBox()` is viewport-relative, a `fullPage` clip is
     document-relative -- so the crop slid down the page once anything had
     scrolled. Now read via `getBoundingClientRect() + scrollX/Y`.
  2. Waiting for the first `svg path` to be *visible* never succeeds: ECharts'
     first child is an invisible clip path. Poll the path *count* instead.
  3. Real app bug: the capability histogram's y-axis name ("density") was
     clipped by the top of the canvas -- `grid.top` 24 left no room for a name
     ECharts draws *above* the grid. Now 36. Only visible once something
     photographed it.

- T-0017b (2026-07-21) **v0.1.0 released.** PR #3 squash-merged; release-please
  cut tag `v0.1.0` and the GitHub release. Versions verified at 0.1.0 across all
  six files beforehand; post-merge CI green on all six jobs, including the drift
  check T-0034 had just fixed — the precise failure it was written for.
  Two things learned about release PRs, both worth repeating next time:
  1. Workflows on a GITHUB_TOKEN-created PR are queued as `action_required`,
     awaiting manual approval. `gh pr checks` reports *nothing* while a run is
     held, which is indistinguishable from a repo with no CI. Approve with
     `gh api -X POST repos/Xindaan/capstat/actions/runs/<id>/approve`.
  2. release-please rebuilds the PR whenever `main` moves, so a green run can
     belong to a superseded head. Compare the run's sha against
     `gh pr view <n> --json headRefOid` before trusting it. This happened here:
     the first green tick was for `3fbaa54d`, the head was already `22c2f444`.

- T-0034 (2026-07-21) The OpenAPI drift check no longer fails on formatting it
  does not own. release-please stamps `$.info.version` into `openapi.json` and
  rewrites the file with JavaScript's JSON writer, which cannot tell `5.0` from
  `5` -- so the 0.1.0 release commit differed from a fresh render in exactly
  three whitespace-equivalent numbers and would have turned `main` red on an
  artefact nobody had touched. `--check` now compares the *parsed* documents,
  which is what it was always meant to assert: that the committed contract
  describes the same API as the code. Byte differences are reported, not failed.
  Proven by checking out the release branch into a worktree, running the check
  (exit 1), patching the exporter in, and running it again (exit 0) -- the first
  measurement was confounded by the version field and had to be redone properly.
  Then confirmed on the real thing: the release PR's own CI, once approved, went
  green on all six jobs.
  Guard kept sharp by a test that mutates a value rather than its formatting.
  Isomorphie-Check: `apps/web/package.json` goes through the same JSON updater
  but is under no byte-comparison, so `openapi.json` was the only instance.

- T-0032 (2026-07-21) "Allow GitHub Actions to create and approve pull requests"
  enabled by the maintainer; re-running the workflow opened PR #3 immediately.
  It was a permission decision, not a config bug -- the switch lets *any*
  workflow in the repo open PRs, which is why it was not mine to make.

- T-0033 (2026-07-21) The upload panel no longer auto-selects a row index. It
  landed on `part` = 1..60 in the demo CSV and computed Pp 0.006 -- capability of
  the *part numbers* against a diameter spec. Nothing objected, because
  consecutive integers are perfectly good numeric data; that is precisely the
  failure mode this project exists to prevent.
  * `looksLikeRowIndex()` in `lib/stats.ts`: consecutive integers stepping by one
    from 0 or 1, at least three of them. Deliberately strict -- the two mistakes
    are not symmetric. Missing an index is the status quo; wrongly flagging a
    real measurement would teach people to ignore the warning.
  * Auto-select takes the first column that does *not* look like an index, and
    falls back to the first column when every one of them does.
  * Selecting it manually is still allowed -- but the summary then says so in
    amber, naming the arithmetic ("these values run 1, 2, 3 ...").
  * Isomorphy check: `columns[0]`/`columns.find` appears only in
    `upload-panel.tsx`; `/gage-rr` and `/msa` take typed grids, not column
    picking, so there is no second site to fix.
  * 6 unit tests (31 vitest total) + an e2e test covering both halves: the index
    is not preselected, and picking it raises the warning.

- T-0028 (2026-07-20) An index with no value now says *why*, instead of showing
  a bare dash. Prompted by the maintainer asking "did I enter LSL/USL wrong?"
  within a minute of loading the demo CSV -- he had not; on the percentile path
  Cp and Cpk simply do not exist. Two absences that looked identical are now
  distinguished in the card itself:
  * **"not defined on the percentile path"** -- the percentile method reads
    percentiles off the overall fitted distribution and has no within/between
    split, so Cp/Cpk are not merely unknown, they are undefined.
  * **"needs both spec limits"** -- Cp and Pp need two limits; Cpk and Ppk are
    defined by one. A one-sided spec empties different cards for a different
    reason, and now says so.
  The amber warning below already explained the first case, but three blocks
  below the cards is too far away to answer the question the cards raise.
  Verified in-browser on the real demo CSV (both cases), and pinned by an e2e
  test so the explanations cannot decay back into dashes.
- T-0017a (2026-07-20) M6d release automation. release-please configured for the
  repo, plus the README/docs honesty pass that came with it.
  * **One version for the whole repo.** Core, API and web are built and released
    together; independent version numbers would imply a freedom that does not
    exist. The manifest holds it; `extra-files` writes it into both pyprojects,
    both `__version__` constants, `apps/web/package.json`, and
    `apps/api/openapi.json`.
  * That last one is the non-obvious part: the API's version is *part of its
    published schema*, and the schema is drift-checked against the code. A
    release that bumped the version without rewriting `openapi.json` would fail
    the next CI run. Verified the jsonpath (`$.info.version`) resolves by
    reading the file rather than assuming the usual OpenAPI key order -- the
    exporter sorts keys, so `info` sits near the end.
  * CONTRIBUTING now spells out that the commit type decides the version bump,
    not just the changelog section: a commit typed wrongly releases wrongly.
  * **Found while writing the release docs**: `docs/getting-started.md` told
    readers to `pip install capstat-core`. That package is on no index -- the
    instruction would simply fail. Corrected to install from the checkout, with
    the PyPI question filed as T-0030. The README's status block was also stale
    ("the API and web app follow" -- they were finished days ago).
  * Deliberately *not* done: merging the release PR (T-0017b -- a public
    release is your call) and README screenshots (T-0031).
  * **The first run: I misdiagnosed it, then checked and corrected myself
    (2026-07-20).** I claimed the config left both versions at 0.0.0 and rewrote
    the extra-files updaters to "fix" it. Then I inspected the release branch
    release-please had actually pushed -- and every version *was* bumped
    correctly (both pyprojects, package.json, openapi.json, to 1.0.0, via the
    `x-release-please-version` annotations). The config was never broken. I
    reverted the false-premise change and kept the proven config. Lesson logged:
    the release branch is the ground truth; a "No entries modified" line in the
    log was noise from a redundant updater pass, not a failure. The *real* first-
    run finding is one thing, not two: (b) Actions may not open pull requests by
    default, so the run built the branch and then failed at the PR step. Filed
    as T-0032 -- that switch lets every workflow in the repo open PRs, which is
    the maintainer's call, not mine.
  * Separately real: the default first release is **1.0.0**, but the stated goal
    is **0.1.0**. Pinned with a `Release-As: 0.1.0` footer, verified against the
    rebuilt release branch.
- T-0015a (2026-07-16) M6b deployment artifacts: Dockerfiles for both apps,
  docker-compose, Vercel config, and a deployment page in the docs.
  * **API image**: multi-stage, uv-based, dependencies in their own layer so
    editing a statistic does not re-resolve scipy. Runs as a non-root user --
    it parses untrusted uploads through pandas/openpyxl. Honours `$PORT`, which
    is what container hosts inject. Built from the repo root, because
    capstat-api depends on capstat-core as a workspace member.
  * **Web image**: Next `output: "standalone"`, so the image ships only the
    node_modules the build actually reached. Vercel ignores this and builds its
    own way, so setting it costs nothing there.
  * The health check lives in `apps/api/healthcheck.py` rather than an inline
    `python -c`: the nested quoting that needs is exactly the sort of thing that
    breaks silently and then reports "unhealthy" for the wrong reason.
  * **Could not verify locally -- the Docker daemon was not running.** Rather
    than claim the images build, CI gained an `images` job that builds both on
    every commit (build only, nothing pushed), so a deployment artifact cannot
    rot unnoticed until deploy day. What *was* verifiable locally: the uv flags
    exist, and `next build` really emits `.next/standalone/server.js`, which the
    web Dockerfile depends on.
  * Measurement for T-0026 recorded in docs/deployment.md: ~152 MB of runtime
    dependencies and ~1 s of cold import, hence the recommendation to put the
    API on a container host rather than serverless.
- T-0016 (2026-07-16) M6c docs site: mkdocs-material + mkdocstrings, in a
  separate `docs` dependency group so test CI does not drag mkdocs in.
  * Pages: Home (what makes it different), Getting started (install, first
    study, run the API/app), Methods (capability, control charts, measurement
    systems -- the *reasoning* per method, with formulas and citations),
    Validation (the five rules and the errors they caught), API reference
    (mkdocstrings from the docstrings).
  * **`docs/validation-sources.md` is generated** from the reference YAMLs by
    `scripts/gen_sources_page.py`, with a `--check` drift mode in CI -- the same
    rule the library applies to constants: do not transcribe what you can
    derive. A hand-written source list would drift the first time a reference
    was added and the page forgotten. Drift detection verified by tampering with
    the file and confirming a non-zero exit.
  * CI gained a `docs` job: sources-page drift + `mkdocs build --strict` (strict
    turns broken links and missing nav targets into failures).
  * Verified mkdocstrings actually rendered rather than silently no-op'ing: the
    built page carries real docstring prose and parameter tables, not just nav.
  * Noted for later: mkdocs-material prints a warning that MkDocs 2.0 will
    remove the plugin system with no migration path. Not actionable now (we pin
    1.x), but it makes the docs stack a future liability -- see T-0029.
- T-0027 (2026-07-16) **Bug: a degenerate Box-Cox crashed the capability path.**
  Found by generating a realistic demo CSV (a capable-but-drifting process,
  spec 9.70/10.30) and running it through the app before shipping it: the
  decision path routed to Box-Cox, the fitted lambda came out at -46, and at
  that lambda `x**lambda` underflows across the whole range -- so *both* spec
  limits mapped to the same float (0.0217086) and the inner `capability()` call
  raised `lsl (0.0217...) must be strictly below usl (0.0217...)`. A user who
  typed 9.70 and 10.30 got a 422 about 0.0217. This is the note left open in
  T-0011 sub-increment 5; now with a repro from ordinary data.
  * `box_cox_capability` now detects the collapse and raises an error naming the
    limits the *caller* passed, not their transformed ghosts.
  * `analyze_capability` catches it and routes to the percentile method -- the
    fallback it already had for "Box-Cox didn't work", which simply was never
    reached because Box-Cox raised first. Percentile does not transform the
    limits, so it handles this fine (lognorm, Ppk 0.942).
  * Tests: the collapse (forced lambda, deterministic) and the fallback
    (seeded drift data, with a precondition asserting it really is the new
    branch and not the older "failed to achieve normality" one).
  * Also caught while verifying: `uvicorn --reload` watches `apps/api` only, so
    the running server kept serving the old core. Verify through the live
    server, not just the unit test.
- T-0014 (2026-07-16) M6a printable report. **Scope changed on purpose**: the
  task said "report *route*", but a separate route would mean plumbing each
  page's analysis state somewhere a second route could read it -- for three
  different surfaces (`/`, `/gage-rr`, `/msa`), that is a store refactor bought
  for nothing. Instead the analysis pages print *themselves*: a `@media print`
  stylesheet drops the nav, the buttons and the dropzone, flattens the inputs so
  their values read as text (the study's parameters belong in the report), keeps
  colour (a red limit is meaning, not decoration), and avoids page breaks inside
  charts, tables and cards. A "Print / save as PDF" button on each page hands it
  to the browser. One stylesheet, all three surfaces, no new state.
  * ECharts now renders **SVG instead of canvas** (`lib/echarts.ts`), so charts
    come out vector in the PDF rather than a screen-resolution bitmap. Our
    series are small, so SVG costs nothing.
  * Verified automatically, not by eyeballing a dialog: a Playwright test
    emulates print media and asserts the controls are gone while the headings,
    verdicts and chart SVGs remain.
  * Server-side PDF stays out of scope (it would put a headless browser in the
    API image for what every browser already does). Still a roadmap item.
  * Snag worth remembering: the e2e assertions counted `canvas`; with SVG they
    had to be scoped to the panels, because Next's dev overlay ships SVGs of its
    own and inflated the count.
- T-0019 (2026-07-16) Demo hosting decided: **Vercel** for the Next.js app.
  The API's host is a separate open question -- see T-0026.
- T-0025 (2026-07-16) MSA API + UI: `/compute/{bias,linearity,stability}` with
  faithful serialisation (derived verdicts included; an identical-reading bias
  study's infinite t serialises as null, the interval-based verdict survives;
  stability nests the existing ChartPair schema), and a `/msa` page with the
  three studies, each pre-filled with a worked example. Stability reuses the
  `ControlChart` component built for the control-chart panel. 45 API tests, 25
  vitest, 5 Playwright. Verified in-browser: the linearity panel renders the
  AIAG slope -0.132 / intercept 1.408 and the published per-part biases live.
  **M5 is now complete end-to-end.**
- T-0013 (2026-07-16) M5b measurement-system studies in `capstat-core` -- the
  three that ask whether a gage is *right*, not just consistent.
  * **Bias** (`bias`): one-sample t-test of repeated readings against a known
    reference. Bias, repeatability, t/p, a confidence interval, and a CI-based
    verdict that stays meaningful when every reading is identical (the
    t-statistic is not). Validated against scipy's `ttest_1samp` and both AIAG
    worked examples (hardness = no bias, colorimeter = biased).
  * **Linearity** (`linearity`): least-squares regression of per-reading bias on
    the reference across masters spanning the range; slope/intercept, R^2, the
    slope's t-test, %linearity = |slope| x 100, absolute linearity when a
    process variation is given. Validated against the AIAG example (slope
    -0.132, intercept 1.408, per-part biases) and scipy's `linregress`.
  * **Stability** (`stability`): a deliberately thin MSA-framed wrapper over the
    validated I-MR / Xbar-R charts -- a control chart on a master part, with the
    out-of-control points read as gage drift.
  445 core tests, 100% coverage, mypy strict + ruff clean. Core-only; the API +
  UI wiring is T-0025.
- T-0012b web+API (2026-07-15) Gage R&R wired out of the core: `/compute/gage-rr`
  (both methods, faithful `GageRRReportOut` with the derived %/ndc read via
  from_attributes; a nan-guard so degenerate input serialises as null, not a
  500) and a `/gage-rr` web page -- data-entry grid (parts x operators x trials,
  pre-filled with the AIAG example), method toggle, variance/%/ndc report with
  verdict warnings, nav link. 38 API tests; 2 Playwright smoke tests. Verified
  in-browser on both methods (ANOVA 33% / ndc 4, avg-range 34% / ndc 3).
- T-0012 (2026-07-15) M5a Gage R&R (measurement-system analysis) in
  `capstat-core`, both AIAG methods.
  * **ANOVA** (`gage_rr`): crossed two-way random-effects model; variance
    components with the interaction-drop rule (pool when the F-test's p > 0.25)
    and negative-variance clamping; %Contribution, %Study Variation, ndc
    (1.41 * PV/GRR), optional precision-to-tolerance, AIAG verdict warnings.
  * **Average-and-range** (`gage_rr_range`): EV = Rbar/d2(r),
    AV = sqrt((Xdiff/d2*(o,1))^2 - EV^2/(pr)), PV = Rp/d2*(p,1); shares the same
    `GageRRReport`. New `d2_star(n, g) = sqrt(d2^2 + d3^2/g)` in constants.py,
    computed from the existing d2/d3 (not transcribed) and validated against
    Duncan's published table -- it is exactly what the AIAG K2/K3 constants
    encode.
  * Validation: the ANOVA path against the SPC-for-Excel AIAG worked example
    (independently recomputed in plain numpy first); the average-and-range path
    against the published AIAG 10-part summary and an independent oracle on the
    5-part data; the two methods cross-checked to agree on the same data
    (33% vs 34% GRR). 412 core tests, 100% coverage, mypy strict + ruff clean.
  * Also hardened a pre-existing d3 timing test that flakes under coverage
    instrumentation (sub-second wall-clock assert): the tight bound now applies
    only when no line tracer is active; under coverage a generous ceiling still
    catches the order-of-magnitude scipy regression it guards against.
  * Core-only: no Gage R&R API endpoint or UI yet (a later increment).
- T-0011 (2026-07-15) M4 Next.js app -- all six sub-increments: typed TS client
  (openapi-typescript, drift-checked); Next 16 / React 19 / Tailwind v4 scaffold;
  upload flow (`/ingest` + CORS); capability dashboard (decision-path analyze +
  ECharts histogram); I-MR control charts with a Nelson run-rule overlay (shared
  `useEchart` hook); and a test safety net (vitest for the pure numerics +
  Playwright smoke, both in CI). The app now covers upload -> capability ->
  control charts, typed against the API and tested. Detail in the commits
  (ec3e1ac, 23b40d5, 7c8bdd3, ed2fe9a).
- T-0020 (2026-07-15) CI actions bumped off the deprecated Node.js 20 runtime:
  `actions/checkout@v4->v7`, `astral-sh/setup-uv@v6->v7`,
  `actions/setup-node@v4->v7`. Verified none of the breaking changes touch
  inputs we use (checkout takes none; setup-node's v5 auto-cache is additive to
  our explicit `cache: npm`; setup-uv dropped only `server-url` / the old custom
  manifest). setup-uv stopped at v7 on purpose: v8 removed the moving major tag,
  so `@v8` does not resolve -- only full versions do. CI green, warnings gone.
- T-0010 (2026-07-15) M3 FastAPI service. New workspace member `apps/api`
  (`capstat_api`): stateless compute endpoints over every core entry point,
  `/ingest` for CSV/XLSX, `/health`, `/rules/catalogue`. OpenAPI schema
  committed at `apps/api/openapi.json` with a drift check in CI + pre-commit.
  412 tests, 100 % coverage on both packages, mypy strict clean.
  * **The core stays web-free.** fastapi/pandas/openpyxl live only in
    `apps/api`; `capstat-core` is still numpy+scipy (PLAN.md non-negotiable).
    Enforced by construction -- the api package depends on the core, never the
    reverse.
  * **Faithful serialisation was the whole job.** Response models are Pydantic
    mirrors built with `model_validate(core_obj)` under `from_attributes=True`,
    so the core's `warnings` tuples survive as JSON arrays AND the derived
    `@property` values (`in_control`, `stability_ratio`) are read by attribute
    -- `dataclasses.asdict` would have silently dropped them. Every compute
    test asserts equality with the core's own output, not just a 200.
  * **`None` is preserved, never coerced to 0.** A one-sided spec leaves
    `cp`/`cpl` undefined; the schema carries `null`. Pinned by a test.
  * **Non-finite floats become `null`.** A zero-variance sample yields `nan`
    skewness; JSON has no `NaN`, so a `SafeFloat` validator maps non-finite to
    `null` on the (few) fields that can be non-finite. Pinned by a test.
  * **The 8-vs-9 rule discriminant carries through HTTP.** The rules endpoints
    rebuild a minimal `ControlChart` (points + limits); a run of exactly eight
    fires Western Electric rule 4 and not Nelson rule 2 -- the same off-by-one
    guard as T-0009, now at the API boundary.
  * **Ingestion says what it dropped.** Non-numeric columns are named as
    ignored; missing cells are dropped per column and counted. A silent drop
    would misstate the sample size.
  * `capability` accepts 1D (individuals) or 2D (subgroups) so within-subgroup
    Cp is reachable over HTTP, not just Ppk.
  * **TS client split out by decision (2026-07-15):** M3 ships the committed
    `openapi.json` + a Python drift check; the `openapi-typescript` generation
    moves to T-0011 where the Node toolchain arrives anyway. Recorded so the
    acceptance criterion is not silently dropped.
  * **My own test was wrong, not the code (again).** A dropped-missing test
    used a wholly blank CSV line; pandas skips blank lines by default, so no
    missing value ever existed. The gap had to sit beside a populated column.
- T-0009 (2026-07-14) M2c Nelson + Western Electric run rules.
  `capstat_core.rules`: `nelson_rules`, `western_electric_rules` ->
  `tuple[RuleViolation, ...]`; `NELSON_RULES` / `WESTERN_ELECTRIC_RULES`
  catalogues. 382 tests, 100 % coverage. **Week 2's chart work is complete.**
  * **No breaking change after all.** STATE.md had flagged this task as needing
    `ControlChart.violations` to grow into a rule-aware type. The better design
    avoids it: rules are a *lens applied to* a chart, deriving their sigma zones
    from the chart's own limits. So `violations` keeps meaning "beyond the
    limits" (which IS Nelson rule 1), nothing is double-reported, and the
    published dataclass is untouched.
  * **The discriminating test:** Western Electric rule 4 needs EIGHT consecutive
    points on one side, Nelson rule 2 needs NINE. The standards genuinely
    disagree, and a run of exactly eight must fire one and not the other. Every
    rule is a count, so an off-by-one would produce a chart that looks entirely
    plausible and is permanently wrong -- this asymmetry is what catches it.
    Each rule is additionally tested twice: with its pattern, and one point short.
  * A web-search summary consulted while writing this stated Nelson rule 2 as
    "nine consecutive points on the same side WITHIN one standard error" -- it had
    fused rule 2 with rule 7. Definitions were taken from the rule tables instead.
  * **My own docstring claim was wrong and the simulation caught it.** I wrote
    that all eight Nelson rules make a chart "roughly four times as jumpy, about
    1 in 90". Measured: 1 in 44 -- **eight times** as jumpy as the limit test
    alone (1 in 351; theory 1 in 370). Western Electric: 1 in 61. Corrected in
    the docstring, README and reference YAML, and pinned by a test.
  * Zone rules need a symmetric chart. An R/s/moving-range chart's limits are
    D3*Rbar and D4*Rbar -- not equidistant from Rbar -- so the functions refuse
    it with an explanation rather than computing arithmetic without meaning.
  * A rule fires on the point that *completes* its pattern. **The second half of
    this note used to read "and the k-of-m rules require that final point to
    qualify" -- meaning the last point of the m-window -- and that was wrong;
    corrected 2026-08-23 under T-0051.** The two are different things: the
    pattern completes at the last *qualifying* point, which `signal_at = max(w)`
    already gives. Demanding that the window's final point qualify as well
    silently suppressed any pattern completing inside the first m-1 points.
    The stale case the wording was defending against -- [3.1, 2.5, 0.2] must not
    flag the harmless point 2 -- never needed that gate: `max(w)` reports point
    1 there regardless. A justification that names the right goal and implements
    a different one is worse than none, because it stops the next reader
    looking.
- T-0008 (2026-07-14) M2b EWMA + CUSUM. `capstat_core.time_weighted`:
  `ewma_chart` -> `EwmaChart`, `cusum_chart` -> `CusumChart`.
  355 tests, 100 % coverage. Both NIST worked examples reproduced.
  * **Real published reference values at last** (NIST 6.3.2.3 CUSUM, 6.3.2.4
    EWMA), so this milestone rests on quoted numbers, not only identities.
  * EWMA reproduces NIST to 4.8e-3 (inside their 2-decimal printing); limits to
    1e-4. CUSUM only to 2.8e-2 -- and that is *explained, not tolerated*: NIST
    prints its inputs to 2 decimals and a CUSUM is a CUMULATIVE sum, so input
    rounding accumulates rather than averaging out. A systematic +0.005 on every
    input moves the final S_hi by 0.040, so our 0.0275 sits comfortably inside
    what their rounding can produce. A dedicated test proves the tolerance is
    explained by rounding and has no room to hide a defect.
  * **The values carry a tolerance; the DECISION carries none.** NIST's first
    signal is group 14, and ours must be group 14 exactly -- asserted separately
    with no tolerance at all.
  * **Design: sigma defaults to the moving range, not the overall sd.** A
    sustained shift inflates the overall sd, which widens the limits, which hides
    the shift -- the chart then reports all is well. Measured over 200 runs with
    a 2-sigma shift: moving-range sigma = 1.002 (true 1.0) while the overall sd
    is inflated to 1.406.
  * **EWMA limits are time-varying by default.** NIST (and many textbooks) apply
    the steady-state width to every point, which makes the first limit 40 % too
    wide -- a shift present at the start can slip under it. `time_varying_limits
    =False` reproduces the published example.
  * Claims verified rather than quoted: Shewhart ARL1 = 43.9 for a 1-sigma shift
    (analytic), CUSUM ARL1 = 10.5 and ARL0 = 457 (simulated). lambda=1 reduces
    EWMA exactly to a Shewhart individuals chart -- the sanity check on the
    recursion.
  * Three of my own tests were wrong, not the library: (a) I asserted a stable
    EWMA series is always in control -- but with ARL0 ~500, **34.7 %** of
    200-point series contain a false alarm, so the *rate* is what must be tested;
    (b) I bounded the CUSUM detection delay at 15 when its p95 is 16; (c) I used
    random symmetric jitter to justify the CUSUM tolerance, but random errors
    partially cancel in a cumulative sum -- the systematic worst case is the
    correct (and looser) argument.
- T-0007 (2026-07-14) M2a Control-chart constants + Shewhart charts.
  `capstat_core.constants` extended with d3, A2, A3, B3, B4, D3, D4, E2 (all
  computed from definitions, none transcribed). `capstat_core.control_charts`:
  `xbar_r_chart`, `xbar_s_chart`, `i_mr_chart` -> `ChartPair`.
  317 tests, 100 % coverage.
  * d3 (sd of the range) needs the joint density of the sample minimum and
    maximum: f(x,y) = n(n-1) phi(x) phi(y) [Phi(y)-Phi(x)]^(n-2), integrated as
    a double integral for E[W^2], then d3 = sqrt(E[W^2] - d2^2). Internal check:
    the SAME joint density integrated against (y-x) reproduces d2, which comes
    from a completely different single integral.
  * **The published tables are wrong about E2.** They print 2.660; the exact
    value is 2.6587. They evaluated 3/d2 with d2 already rounded to 1.128 and
    propagated the error. Computing from the definition avoids importing it.
    Pinned by a test that asserts the gap exceeds the table's own rounding.
  * The published tables also disagree with each other: NIST prints D4(3)=2.575,
    the ASTM-derived table 2.574. We compute 2.5746, which rounds to NIST's.
    Tolerance is 1e-3 absolute -- set by the sources' precision, not ours (~1e-8).
  * Naming hazard kept deliberately: d3 (sd of the range) vs D3 (R chart lower
    limit factor) differ only in case. Every textbook does this; renaming would
    make the code harder to check against its sources. Flagged loudly instead.
  * **Design: the dispersion chart is judged first.** The X-bar limits are
    computed FROM Rbar/sbar, so an out-of-control dispersion chart makes them
    meaningless. `ChartPair.in_control` is the AND of both charts, and the pair
    warns explicitly when dispersion is the one signalling. A location chart can
    read "all in control" on a process that plainly is not.
  * D3/B3 are zero for small n because the unclamped value is negative -- so the
    chart cannot detect an *improvement* in spread. Warned about, not hidden.
  * Isomorphy check on the E2 error class ("a rounded published value used as an
    input to a computation"): the only hardcoded float in the whole library is
    MAD_NORMAL_CONSISTENCY, and it is validated against scipy at full precision.
    Every chart factor derives from the exact d2/d3/c4. No propagation anywhere.
- T-0006 (2026-07-14) M1d Non-normal path. `capstat_core.nonnormal`:
  `box_cox_capability`, `percentile_capability` (ISO 22514), `fit_distribution`,
  and `analyze_capability` -> `CapabilityAnalysis`, which runs the documented
  decision path (normal -> Box-Cox -> percentile) and records *why*.
  277 tests, 100 % coverage. Week 1 (Tier-1 statistics) is complete.
  * The limits are transformed with the same lambda as the data. A test pins the
    magnitude of the bug being prevented (forgetting them shifts Ppk by > 1.0),
    not merely its absence.
  * Box-Cox is strictly increasing for **every** lambda (derivative
    x**(lambda-1) > 0 for x > 0), so LSL stays the lower limit. Verified for
    lambda in {-2, -0.5, 0, 0.5, 1, 3} -- the negative cases are the ones where
    intuition says it should flip.
  * capstat refuses to shift non-positive data to make Box-Cox applicable: the
    offset changes the indices and must be the user's recorded decision.
  * **A reference claim of mine was wrong and the tests caught it.** I asserted
    that Box-Cox and the percentile method must agree on lognormal data. They
    must not: Box-Cox is linear on the log scale, ISO is nonlinear on the
    original scale ((e^U - 1)/(e^3s - 1)). They coincide ONLY at the just-capable
    point (U = 3s, both = 1) and diverge sharply elsewhere -- measured Ppu 1.61
    vs 2.44 on identical data. The YAML, the module docstring and the README now
    say so; the tests pin both the agreement and the divergence.
  * The fitted-normal percentile index differs from the classic one by exactly
    sqrt(n/(n-1)) * (6/5.999954): the MLE sigma (denominator n) times ISO's
    rounded percentile span. Predicted exactly and pinned at rel=1e-12, because
    it is exact algebra -- a loose tolerance there would be an admission we did
    not understand the gap, and could hide a real bug.
  * `DistributionFit.fit_score` is an AD statistic via the probability integral
    transform. It carries NO p-value: the parameters were estimated from the same
    data, so any p-value would be anticonservative by an unknown amount. It ranks
    candidates; it does not certify one.
  * Isomorphy: the `float ** float -> Any` typeshed wrinkle (first hit in T-0003
    at `m2**1.5`) recurred here at `x**lmbda`. Fixed the same way (`math.pow`).
- T-0005 (2026-07-14) M1c Capability indices. `capstat_core.capability`
  (`capability` -> `CapabilityReport` with Cp/Cpl/Cpu/Cpk/Cpm and
  Pp/Ppl/Ppu/Ppk) and `capstat_core.constants` (`d2`, `c4`). 234 tests,
  100 % coverage.
  * **Plan delta:** d2/c4 were pulled forward from T-0007. Cp/Cpk require a
    within-subgroup sigma (Rbar/d2 or sbar/c4); without them there is no
    short-term sigma, only a number mislabelled Cpk. T-0007's scope shrinks
    accordingly (see Next).
  * Constants are **computed from their definitions**, not transcribed:
    d2 = E[range of n standard normals] by quadrature, c4 = the closed-form
    gamma ratio via lgamma. A copied table can hide a typo that the test never
    catches, because the test was written by copying the same table. Validated
    three ways: the published d2 table; NIST's A2 table via A2 = 3/(d2*sqrt(n))
    (a source that never states d2); and Monte-Carlo E[range].
  * The within/overall split is enforced, not documented-and-ignored. On a
    drifting process the tests confirm Cpk > Ppk, and the report warns when
    sigma_overall/sigma_within > 1.25.
  * `cpm` is `None` without an explicit target -- no silent midpoint assumption,
    which is wrong for an asymmetric tolerance.
  * The NIST worked example estimates sigma with the sample s, so it maps onto
    capstat's **Pp/Ppk**, not Cp/Cpk. That mapping is pinned by a test.
  * Bug found: `@cache` on a public function erases its type signature (mypy
    sees `_lru_cache_wrapper.__call__(*args: Hashable)`), so `d2(5.0)` type-
    checked clean -- for us and for any user. Fixed by wrapping a private
    cached impl behind a typed public function; a load-bearing `type: ignore`
    in the tests now guards the regression. Isomorphy check: these were the only
    two cache decorators in the package.
  * Measured, not assumed: the `assess_normality` fail-closed AND-rule rejects
    7.6 % of genuinely normal samples (vs 5.8 % / 4.8 % for the individual tests
    at alpha=0.05). Documented in the docstring and pinned by a calibration test.
- T-0004 (2026-07-14) M1b Normality tests. `capstat_core.normality`:
  `anderson_darling` (own implementation, with the p-value scipy does not
  provide), `shapiro_wilk` (delegates to scipy's AS R94), and
  `assess_normality` -> `NormalityAssessment` with an explicit verdict,
  recommendation, and warnings. 193 tests, 100 % coverage.
  Validation rests on four independent legs, because the AD p-value is the one
  piece capstat owns outright and a mis-transcribed coefficient there would be
  invisible:
  * AD statistic cross-checked against `scipy.stats.anderson` on 8 NIST
    datasets (rel 1e-10; Mavro's tiny sd of 4.3e-04 amplifies rounding to
    ~2e-12, hence not machine epsilon).
  * AD p-value formula transcribed verbatim from CRAN `nortest` 1.0-4
    (D'Agostino & Stephens 1986), NOT from memory.
  * Round-trip: feeding Stephens' *independently published* critical values
    into that formula returns the nominal alphas to within 2 %. Two sources
    that never touched each other agree.
  * Shapiro-Wilk validated against a published R `shapiro.test` result
    (W = 0.7888, p = 0.006704) -- testing scipy against scipy would be circular.
  Design decisions worth keeping:
  * `assess_normality` fails closed: `normal` is the AND of both tests, and a
    disagreement is surfaced as a warning rather than silently resolved.
  * It warns on material autocorrelation (|r1| > 0.2). Both tests assume
    independence; NIST Mavro has r1 = 0.94, so its p-values are meaningless.
    A tool reporting only the p-value there would be actively misleading.
  * It warns on low power (n < 20) and on large n, where a practically
    irrelevant deviation becomes "significant".
  * AD requires n >= 8 (the p-value approximation is undefined below), matching
    R's `nortest::ad.test` guard.
  * The branches of the p-value approximation are genuinely discontinuous (up
    to 3.3e-03 at A*^2 = 0.34); that is the published fit, not our error, and
    is pinned by a test at 5e-3.
- T-0003 (2026-07-14) M1a Descriptive statistics + robust variants.
  `capstat_core.descriptive` (mean, variance, std_dev, skewness, kurtosis,
  lag1_autocorrelation, `describe` -> immutable `DescriptiveSummary`) and
  `capstat_core.robust` (median, mad, iqr, trimmed_mean, winsorized_mean).
  Validated against all 9 NIST StRD Univariate datasets (archived verbatim
  in-tree with their certified-value headers); robust estimators validated by
  hand-computed values + scipy cross-check. 152 tests, 100 % coverage.
  Findings worth keeping:
  * The one-pass variance returns a *negative* variance (-0.032) on NumAcc4.
    All centered moments therefore use a two-pass algorithm, pinned by a
    regression test plus a shift-stability test across the whole family.
  * The residual 5.6e-09 error on NumAcc4 is a float64 *input representation*
    floor, not an algorithmic one (proven in exact rational arithmetic); the
    loosened tolerance there is justified in the reference YAML.
  * Bug found and fixed in the T-0002 config: `mypy python_version = "3.11"`
    breaks against numpy >= 2.5 stubs (PEP 695) and was masking two real
    strict-mode errors. mypy now infers the version from the interpreter.
- T-0002 (2026-07-14) M0 Repo bootstrap: git init; MIT LICENSE (© André
  Leopold); root README with CI/license/python badges; CONTRIBUTING,
  CODE_OF_CONDUCT, SECURITY; `.github/` (CI workflow, dependabot, issue/PR
  templates); uv workspace with `capstat-core` (numpy+scipy, hatchling,
  py.typed); shared ruff/mypy(strict)/pytest/coverage config; pre-commit
  (local hooks via `uv run`); TASK/STATE converted to English. Green locally:
  ruff, ruff-format, mypy strict, pytest 1/1, coverage 100 %.
- T-0001 (2026-07-13) Kickoff plan confirmed: name capstat ("Capsat" typo
  resolved explicitly), LICENSE name André Leopold, language English, GitHub
  account Xindaan; hosting split out into T-0019.
