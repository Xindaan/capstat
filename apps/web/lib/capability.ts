/**
 * Which band a capability index falls in, against a *stated* requirement.
 *
 * The page used to colour Cp/Cpk green at 1.33 and amber at 1.00, thresholds
 * the core contains nowhere and declines to assert -- what counts as capable is
 * a customer's specification, not a property of the statistic. So the app was
 * stating a verdict the library refuses to (T-0073).
 *
 * The two numbers are not the same kind of thing, and separating them is the
 * point:
 *
 * - **The requirement** is the customer's. 1.33 is common, but 1.67 and 2.00
 *   are ordinary in automotive and safety work, and a process at 1.35 is green
 *   under one and short under another. It is now an input.
 * - **1.00** is not a convention at all. It is the point where the process
 *   spread exactly fills the tolerance -- below it the process cannot hold the
 *   specification however the requirement is set. That belongs in code.
 *
 * Compare `gage_rr.py`, where the core *does* own the 10 %/30 % bands: AIAG
 * states them, so there is a source to point at. For Cpk there is none, which
 * is exactly why this asks rather than assumes.
 */

/** The index below which a process cannot hold its tolerance at all. */
export const CAPABLE_AT_OR_ABOVE = 1.0;

/** Default requirement: common, changeable, and now visible rather than implied. */
export const DEFAULT_REQUIRED_INDEX = "1.33";

export type CapabilityBand = "meets" | "capable" | "incapable" | "unjudged";

/**
 * Read a typed requirement. Returns null for anything that is not a positive
 * number, including an empty field -- and null means *unjudged*, not "use the
 * default". A requirement nobody could read must not colour anything.
 */
export function parseRequiredIndex(text: string): number | null {
  if (text.trim() === "") return null;
  const value = Number(text);
  if (!Number.isFinite(value) || value <= 0) return null;
  return value;
}

/**
 * The band for one index.
 *
 * Holds for any positive requirement, including one below 1.00: an index at or
 * above the requirement meets it, one that is merely capable sits between, and
 * anything under 1.00 is incapable regardless.
 */
export function capabilityBand(
  value: number | null | undefined,
  required: number | null,
): CapabilityBand {
  if (value == null || Number.isNaN(value)) return "unjudged";
  if (required == null) return "unjudged";
  if (value >= required) return "meets";
  if (value >= CAPABLE_AT_OR_ABOVE) return "capable";
  return "incapable";
}
