# capstat

Reference-validated statistical process control, process capability and
measurement-system analysis — as a Python library, an HTTP API, and a web app.

## What makes it different

Most SPC software will give you a number for anything you hand it. capstat is
built on the premise that the number is the easy part, and that the ways a
capability study goes wrong are not arithmetic mistakes — they are unexamined
assumptions.

**Every statistic is validated against a published reference value.** Not
against our own earlier output, and not against a table we copied into the test.
The sources are listed in full under [Validation](validation.md), and the test
suite asserts against them on every commit.

**Constants are computed, not transcribed.** `d2`, `c4`, `d3` and the rest are
evaluated from their definitions. A copied table can carry a typo that the test
never catches, because the test was written by copying the same table. This is
not hypothetical: capstat's computed `E2(2)` is 2.6587, while the published
tables print 2.660 — they evaluated `3 / d2` with an already-rounded `d2` and
propagated the error.

**Every report says what its numbers cannot say.** A capability report on a
drifting process carries a warning that Cpk describes a potential the process is
not delivering. A Gage R&R whose interaction was pooled says so. A percentile
capability study reports no Cp/Cpk at all, because that method has no
within/between split and those indices do not exist for it — rather than
printing a plausible number nobody can defend.

## Where to start

- **[Getting started](getting-started.md)** — install it, run it, and put a CSV
  through it.
- **[Methods](methods/index.md)** — what each statistic means, the formula, and
  the source it is checked against.
- **[Validation](validation.md)** — how the reference values work, and the
  errors this approach has actually caught.
- **[API reference](api-reference.md)** — every public function and dataclass.

## The three pieces

| | |
|---|---|
| `capstat-core` | The statistics. numpy + scipy only, independently installable. |
| `capstat-api` | A stateless FastAPI service over the core, plus CSV/XLSX ingestion. |
| `apps/web` | A Next.js app: upload, capability, control charts, Gage R&R, MSA. |

The core never imports the web stack. fastapi, pandas and openpyxl live only in
the API package, so the library stays a library.
