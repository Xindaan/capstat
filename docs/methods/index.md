# Methods

What each statistic means, the formula capstat evaluates, and the source that
formula is checked against.

These pages are about the *reasoning*: when a method applies, what it assumes,
and how it misleads when the assumption fails. For signatures and return types,
see the [API reference](../api-reference.md).

| Area | Covers |
|---|---|
| [Capability](capability.md) | Cp, Cpk, Cpm, Pp, Ppk; the two sigmas; the non-normal decision path |
| [Control charts](control-charts.md) | X-bar/R, X-bar/s, I-MR, EWMA, CUSUM, run rules |
| [Measurement systems](measurement-systems.md) | Gage R&R, bias, linearity, stability |

## A note on assumptions

Every method here rests on assumptions, and each one fails differently:

- **Normality** — capability indices read tail probabilities off a fitted
  normal. On skewed data those tails are wrong, and wrong in the flattering
  direction as often as not.
- **Time order** — a moving-range sigma and every control-chart limit assume the
  data arrive in the order they were produced. Shuffle the rows and the limits
  become meaningless, and *nothing about them will look wrong*.
- **Independence** — autocorrelated readings make a process look far more
  capable than it is, because consecutive points no longer carry independent
  information.

capstat checks what it can check and warns about the rest. It does not silently
substitute a defensible-looking number for an undefined one.
