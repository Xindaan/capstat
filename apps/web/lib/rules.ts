/**
 * Pure helpers for the run-rule selection. Kept out of the component so the
 * label logic can be unit-tested -- a report that names the wrong rules is
 * worse than one that names none.
 */

/**
 * "1–4" when the selection is a contiguous run of three or more, "1, 2, 5"
 * otherwise, "none" when empty.
 *
 * The label has to name the rules actually applied: "no violations" is not a
 * statement about a process unless you know what was looked for, and a printed
 * report that omitted it would not be reproducible.
 */
export function describeRuleSelection(selected: number[]): string {
  if (selected.length === 0) return "none";
  const sorted = [...selected].sort((a, b) => a - b);
  const contiguous = sorted.every((r, i) => i === 0 || r === sorted[i - 1] + 1);
  return contiguous && sorted.length > 2
    ? `${sorted[0]}–${sorted[sorted.length - 1]}`
    : sorted.join(", ");
}
