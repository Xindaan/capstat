<!--
  GENERATED FILE -- do not edit.
  Rendered from packages/capstat-core/tests/references/*.yaml by
  scripts/gen_sources_page.py. Edit the YAML, then re-run that script.
-->

# Sources

Every reference value capstat is tested against, and where it came from. This
page is generated from the reference files themselves, so it cannot drift from
what the test suite actually asserts.

A source is listed here because a *number* was taken from it -- a certified
value, a published table, a worked example -- not merely because it was read.

## Descriptive statistics

Reference file: `tests/references/nist_strd_univariate.yaml`

Certified values ship with the datasets in `tests/references/data/`; each file states its own source in its header.

## Normality testing

Reference file: `tests/references/normality.yaml`

- **Anderson, T. W., & Darling, D. A. (1954). A test of goodness of fit. Journal of the American Statistical Association, 49(268), 765-769.**
  Statistic cross-validated against scipy.stats.anderson, an independent implementation, on all nine NIST StRD univariate datasets (see test_normality.py).
- **D'Agostino, R. B., & Stephens, M. A. (1986). Goodness-of-Fit Techniques. Marcel Dekker.**
  <https://cran.r-project.org/package=nortest> Retrieved 2026-07-14.
- **Stephens, M. A. (1974). EDF statistics for goodness of fit and some comparisons. JASA, 69(347), 730-737.**
  <https://www.itl.nist.gov/div898/handbook/eda/section3/eda35e.htm>
- **Royston, P. (1995). Remark AS R94: A remark on Algorithm AS 181: The W test for normality. Applied Statistics, 44(4), 547-551.**
  Retrieved 2026-07-14.

## Capability indices and chart constants

Reference file: `tests/references/capability.yaml`

- **NIST/SEMATECH e-Handbook of Statistical Methods, section 1.3.5.16 / 6.1.6**
  <https://www.itl.nist.gov/div898/handbook/pmc/section1/pmc16.htm> Retrieved 2026-07-14.
- **Chan, L. K., Cheng, S. W., & Spiring, F. A. (1988). A new measure of process capability: Cpm. Journal of Quality Technology, 20(3), 162-175.**
  Formula as stated by the NIST e-Handbook: Cpm = (USL - LSL) / (6 * sqrt(sigma^2 + (mu - T)^2)).
- **Montgomery, D. C. Introduction to Statistical Quality Control, Appendix VI; ASTM E2587.**
- **NIST/SEMATECH e-Handbook of Statistical Methods, section 6.3.2.1**
  <https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc321.htm> Retrieved 2026-07-14.
- **NIST/SEMATECH e-Handbook of Statistical Methods, section 6.3.2**
  Stated check value: "the c4 factor for n=10 is 0.9727"

## Non-normal capability

Reference file: `tests/references/nonnormal.yaml`

- **Box, G. E. P., & Cox, D. R. (1964). An analysis of transformations. Journal of the Royal Statistical Society, Series B, 26(2), 211-252.**
  NIST/SEMATECH e-Handbook, section 6.5.2, describes the same transformation for capability work.
- **ISO 22514-4, Statistical methods in process management -- Capability and performance -- Part 4: Process capability estimates and performance measures.**
  X_p are percentiles of the fitted distribution. The method yields performance (long-term) indices only: it uses the overall distribution and has no within/between subgroup split, so it cannot produce Cp/Cpk.

## Shewhart control charts

Reference file: `tests/references/control_charts.yaml`

- **Table of control chart constants, adapted from ASTM International (widely reproduced; matches Montgomery, Introduction to Statistical Quality Control, Appendix VI).**
  Retrieved 2026-07-14.
- **NIST/SEMATECH e-Handbook of Statistical Methods, section 6.3.2.1**
  <https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc321.htm> NIST tabulates A2, D3, D4 for n = 2..10. It does NOT tabulate d2 or d3, so checking our computed d2 against it (via A2 = 3/(d2*sqrt(n))) uses a table that never states the quantity being checked.
- **NIST/SEMATECH e-Handbook of Statistical Methods, section 6.3.2**
  Stated check value: "UCL = sbar + 3*(sbar/c4)*sqrt(1 - c4^2)" Confirms the B3/B4 definitions used here.

## EWMA and CUSUM

Reference file: `tests/references/time_weighted.yaml`

- **NIST/SEMATECH e-Handbook of Statistical Methods, section 6.3.2.4**
  <https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc324.htm> Retrieved 2026-07-14. NIST applies the steady-state limit width to every point. capstat defaults to the exact time-varying limits (Montgomery), and offers time_varying_limits=False to reproduce this example.
- **NIST/SEMATECH e-Handbook of Statistical Methods, section 6.3.2.3**
  <https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc323.htm> Retrieved 2026-07-14.
- **Montgomery, D. C. Introduction to Statistical Quality Control, ch. 9; Hawkins, D. M., & Olwell, D. H. (1998). Cumulative Sum Charts and Charting for Quality Improvement.**
  The ARL figures are verified by simulation in the tests, not taken on trust: a 3-sigma Shewhart chart needs ~44 points to see a one-sigma shift (analytic: 1 / (Phi(-2) + Phi(-4)) = 43.9), while a CUSUM with k=0.5, h=5 sees it in ~10 while holding an in-control ARL of ~465.

## Run rules

Reference file: `tests/references/rules.yaml`

- **Nelson, L. S. (1984). The Shewhart control chart -- tests for special causes. Journal of Quality Technology, 16(4), 237-239.**
  Retrieved 2026-07-14.
- **Western Electric Company (1956). Statistical Quality Control Handbook. As stated by the NIST/SEMATECH e-Handbook, section 6.3.2.**
  <https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc32.htm> Retrieved 2026-07-14.

## Gage R&R

Reference file: `tests/references/gage_rr.yaml`

- **AIAG. Measurement Systems Analysis (MSA), 4th ed., 2010, ch. III sec. B (Gage R&R -- ANOVA method).**
- **SPC for Excel: ANOVA Gage R&R (Part 3)**
  <https://www.spcforexcel.com/knowledge/measurement-systems-analysis-gage-rr/anova-gage-rr-part-3/> Retrieved 2026-07-15. 5 parts, 3 operators, 3 trials. Interaction not significant (p = 0.9964), so the ANOVA is re-run without it and the components pooled.
- **Duncan, A. J. Quality Control and Industrial Statistics, 5th ed., Table D3 (d2* factors); reproduced in the AIAG MSA manual appendix.**
  capstat computes d2*(n, g) = sqrt(d2(n)^2 + d3(n)^2 / g) from its own d2/d3 rather than copying the table. The AIAG K2 and K3 constants are 1 / d2*(., 1): K2(2 operators) = 1/1.4142 = 0.7071, K3(10 parts) = 1/3.179 = 0.3146.
- **SPC for Excel: Three Methods to Analyze Gage R&R Studies**
  <https://www.spcforexcel.com/knowledge/measurement-systems-analysis-gage-rr/three-methods-analyze-gage-rr-studies/> Retrieved 2026-07-15. The canonical AIAG 10-part x 3-operator x 3-trial average-and-range example. Summary ranges Rbar = 0.342, X_diff = 0.445, Rp = 3.511 give EV = 0.202, AV = 0.230, PV = 1.104, GRR = 0.306, TV = 1.146, %GRR = 26.68.

## Bias

Reference file: `tests/references/bias.yaml`

- **AIAG. Measurement Systems Analysis (MSA), 4th ed., 2010, ch. III sec. B (Bias). Worked examples reproduced by SPC for Excel.**
  <https://www.spcforexcel.com/knowledge/measurement-systems-analysis-gage-rr/variable-measurement-systems-part-2-bias/> Retrieved 2026-07-16.
- **scipy.stats.ttest_1samp -- independent one-sample t-test.**

## Linearity

Reference file: `tests/references/linearity.yaml`

- **AIAG. Measurement Systems Analysis (MSA), 4th ed. (Linearity). Worked example reproduced by SPC for Excel ("The Calculations Behind a Gage Linearity Study").**
  <https://www.spcforexcel.com/knowledge/measurement-systems-analysis-gage-rr/calculations-behind-gagerr-linearity-study/> Retrieved 2026-07-16.
- **scipy.stats.linregress -- independent least-squares regression.**

## Acceptance sampling

Reference file: `tests/references/acceptance_sampling.yaml`

- **NIST/SEMATECH e-Handbook of Statistical Methods, section 6.2.3.2 "Choosing a Sampling Plan with a given OC Curve" -- the worked (n=52, c=3) plan with N=10000: OC table, AOQ table, AOQL, ATI table.**
  <https://www.itl.nist.gov/div898/handbook/pmc/section2/pmc232.htm> Retrieved 2026-07-21. Stated check value: "Using this formula with n=52, c=3, and p = 0.01, 0.02, ..., 0.12 we find: Pa = 0.998, 0.980, 0.930, 0.845, 0.739, 0.620, ..." Validating against this page turned up four inconsistencies in the published tables, all pinned by the tests rather than tolerated. The AOQ column is computed with the AOQ ~ Pa*p approximation instead of the exact AOQ = Pa*p*(N-n)/N given above it; its p=0.03 row is the exception, matching instead the page's own prose calculation with a rounded Pa; and its first entry (0.0010 at p=0.01) is the digits of 0.0100 transposed, a factor-of-ten error -- the exact AOQ there is 0.0099. The ATI column is truncated rather than rounded, again except at p=0.03.
- **NIST/SEMATECH e-Handbook of Statistical Methods, section 6.2.2 "What kinds of Lot Acceptance Sampling Plans (LASPs) are there?" -- definitions of AQL, LTPD, producer's and consumer's risk, OC curve, AOQ, AOQL and ATI.**
  <https://www.itl.nist.gov/div898/handbook/pmc/section2/pmc22.htm> Retrieved 2026-07-21. Stated check value: "AOQ = pa*p*(N - n)/N ... ATI = n + (1-pa)(N-n)"
- **Kiermeier, A. "Visualizing and Assessing Acceptance Sampling Plans: The R Package AcceptanceSampling", CRAN vignette (acceptance_sampling_manual), sections 2.5-2.6 -- the assess() output for the (n=20, c=0) plan and the find.plan() two-point design.**
  <https://cran.r-project.org/web/packages/AcceptanceSampling/vignettes/acceptance_sampling_manual.pdf> Retrieved 2026-07-21. Stated check value: "find.plan(PRP=c(0.05, 0.95), CRP=c(0.15, 0.075), type="binom") -- $n [1] 80, $c [1] 7, $r [1] 8" An independent implementation, not a table: it prints eight significant digits, where the NIST handbook prints three. capstat reproduces every digit of both P(accept) values and returns the same (n, c) plan.
- **AccSamplingDesign R package, CRAN vignette "Introduction to AccSamplingDesign" -- optPlan() attribute design on the binomial model.**
  <https://cran.r-project.org/web/packages/AccSamplingDesign/vignettes/introduction.html> Retrieved 2026-07-21. Stated check value: "PRQ = 0.01, CRQ = 0.05, alpha = 0.02, beta = 0.15 -> Sample Size (n) = 144, Acceptance Number (c) = 4, Producer's Risk 0.01534843, Consumer's Risk 0.1487162"
- **Minitab Support, "All statistics and graphs for Attributes Acceptance Sampling" -- worked example with lot size 5000, n=52, c=2, AQL 1.5 %, RQL 10 %: P(accept), AOQ, ATI and the AOQL with its location.**
  <https://support.minitab.com/en-us/minitab/help-and-how-to/quality-and-process-improvement/acceptance-sampling/how-to/attributes-acceptance-sampling/interpret-the-results/all-statistics-and-graphs/> Retrieved 2026-07-21. Stated check value: "The worst average outgoing defect level (AOQL) of 2.603% defective occurs when the incoming quality level is 4.3% defective." The only independent source found that publishes an AOQL together with the incoming quality that produces it, which is what makes it a real check on the maximisation rather than on the AOQ formula alone. Minitab also uses the exact AOQ = Pa*p*(N-n)/N -- its 1.420 % at p=1.5 % matches capstat's 1.42013 % -- confirming which of the two AOQ formulas is the correct one where the NIST column disagrees with itself.
- **scipy.stats.binom / poisson / hypergeom -- independent implementations of the three OC models, evaluated inside the tests themselves.**
  The Type A (hypergeometric) path has no published worked example with an acceptance number above zero behind it: every Type A example found in the search was c=0, which collapses the sum to a single term and so exercises nothing. It is validated instead against scipy's hypergeom and against a hand-written combinatorial enumeration of the definition, and this gap is stated rather than papered over.

## Switching rules

Reference file: `tests/references/sampling_scheme.yaml`

- **ISO 2859-1:1999, Sampling procedures for inspection by attributes -- Part 1, clauses 9.1 (start of inspection), 9.2 (per class of nonconformities), 9.3.1-9.3.4 (the transitions and the switching score) and 9.4 (discontinuation). Cited by clause; no text reproduced.**
  The thresholds taken from this standard, restated in capstat's own words: tightened inspection begins as soon as two of five or fewer consecutive lots are non-acceptable on original inspection; normal inspection is restored after five consecutive acceptable ones; inspection is discontinued when five lots have not been accepted, cumulatively, while on tightened; and reduced inspection becomes possible at a switching score of thirty. The score is kept two ways depending on the plan's acceptance number, and the difference matters: for Ac >= 2 an accepted lot adds three only if it would still have been accepted one AQL step tighter, and **resets the score to zero otherwise**; for Ac <= 1 an accepted lot adds two. So an accepted lot does not always raise the score -- reading it as "three or two per accepted lot", which an earlier wording of this note invited, makes capstat's reset look like a defect when it is the clause. What capstat reads into the rules rather than out of them -- the window boundary and the fresh window on re-entering normal -- is pinned by tests that label it an interpretation.
- **ANSI/ASQ Z1.4-2003, the US equivalent standard, used only to cross-check that the two thresholds above are stated identically there.**
  Agreement on both numbers. Z1.4 and ISO 2859-1 are not identical documents, so this is corroboration of two figures, not evidence that the schemes coincide.
- **ANSI/ASQ Z1.4-2003, clause 8.4 -- the discontinuation rule, used to settle a contradiction between secondary sources rather than as a source of record.**
  Restatements of the discontinuation threshold disagree in the wild: some say ten consecutive lots on tightened inspection, others five lots not accepted. The disagreement turned out to be an edition artefact, not a real conflict -- Z1.4-2003 changed the rule from the former to the latter, so material predating that revision states the old figure. ISO 2859-1:1999 clause 9.4 and Z1.4-2003 clause 8.4 agree: five lots *not accepted*, counted cumulatively over a sequence of consecutive lots on original tightened inspection. Counting lots inspected rather than lots not accepted is a different rule entirely, and an early version of capstat's implementation made exactly that mistake.
- **Simulated lot sequences, constructed so that two plausible readings of a rule produce different severities -- the validation method, in place of reference values that do not exist for a procedure.**
