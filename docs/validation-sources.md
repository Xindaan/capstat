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
