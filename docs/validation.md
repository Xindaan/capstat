# How validation works

Claiming a statistic is "tested" is cheap. What matters is *what it was tested
against*, and whether that source could have been contaminated by the code under
test.

capstat follows five rules. They are not stylistic — each one exists because it
caught something.

## 1. Compute from the definition; never transcribe a constant

`d2`, `d3`, `c4` and the chart factors derived from them are evaluated from
their mathematical definitions, not copied from a table.

A transcribed table can carry a typo that no test will catch, because the test
was written by copying the same table. Two real cases:

!!! example "E2(2): the published tables are wrong"
    Tables print `E2(2) = 2.660`. The true value is **2.6587**. The discrepancy
    is not ours: the tables computed `3 / d2` with an already-rounded
    `d2 = 1.128` and propagated the rounding error. Deriving from the definition
    avoids importing that mistake.

!!! example "D4(3): the published tables disagree with each other"
    capstat computes **2.5746**. NIST prints 2.575; a widely reproduced
    ASTM-derived table prints 2.574. The published tables disagree in the last
    digit, and the computed value settles it.

## 2. Validate against a source that did not produce the value

A computed constant is checked against an independent publication. `d2` is
checked three ways, none of which share a source:

1. against the classical published table (Montgomery / ASTM), printed to three
   decimals;
2. against NIST's `A2` table, via the identity `A2 = 3/(d2*sqrt(n))` — NIST
   publishes A2 but *not* d2, so this recovers d2 from a table that was never
   meant to state it;
3. against a Monte-Carlo estimate of `E[range]` over 2 × 10⁶ draws, which shares
   no code path with the quadrature at all.

The same principle applies to whole methods: the bias study is checked against
scipy's `ttest_1samp`, and linearity against scipy's `linregress` — independent
implementations, not our own earlier output.

## 3. Prefer identities to quoted numbers

An identity holds for every dataset, not just the one somebody published. The
sum of squares in a Gage R&R must decompose exactly; %Contribution must sum to
100 %; the two Gage R&R methods must land close to each other on the same data.

These caught a false claim of ours during development that a quoted number never
would have.

## 4. Explain a discrepancy exactly, rather than widening a tolerance

A loose tolerance is where a real bug hides. Every tolerance in the reference
files is justified by the *published* value's precision — a table printed to
three decimals gets `5e-4`, not "whatever makes it pass".

**Values may carry a tolerance; decisions must not.** NIST's first CUSUM signal
is group 14, and capstat asserts group 14 exactly.

## 5. Suspect your own test, and your own docstring, before the library

Three tests in the EWMA/CUSUM work turned out to be wrong, not the code. In the
run-rules work a *docstring claim* was wrong: the full Nelson set was asserted
to be "four times as jumpy" as the 3σ test. Simulation said eight times. The
docstring now says eight, because the claim was simulated rather than repeated.

## Where the numbers live

Reference values are not embedded in test code. They live in
`packages/capstat-core/tests/references/*.yaml`, each with its source, the
retrieval date where relevant, and a written justification for its tolerance.
The tests read those files.

That separation is what makes the [Sources](validation-sources.md) page possible
— it is generated from those same files, so it cannot drift from what the suite
actually asserts.

## What is *not* claimed

- **Not certified.** capstat reproduces published reference values; it is not
  accredited by any standards body.
- **Not a substitute for judgement.** The warnings tell you when a number rests
  on an assumption the data do not support. They cannot tell you whether your
  sampling plan was sensible or your parts representative.
- **Not exhaustive.** Coverage is 100 % of lines and branches, which says every
  path runs — not that every statistical edge case has been imagined. One line
  is deliberately excluded: a `verdict` guard in `gage_rr.py` against a
  not-a-number percentage, which the clamping upstream of it makes unreachable.
  It is kept as a floor under a future change and marked, rather than deleted to
  make the number look better or left in to make it look worse.
