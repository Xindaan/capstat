/**
 * Splitting a column into subgroups (T-0075).
 *
 * The app only ever sent one-dimensional data, so every Cp/Cpk it showed rested
 * on a moving-range sigma -- the fallback the library itself warns about on
 * every such report. `capability()` has taken subgroups all along, and
 * `xbar_r_chart` / `xbar_s_chart` have existed since T-0007; none of it was
 * reachable from the page.
 *
 * Subgroups here are **consecutive rows in the order the file supplied them**,
 * which is the ordinary SPC arrangement: five parts measured every hour, one
 * row each. That convention is also the assumption the whole thing rests on, so
 * the panel states it rather than leaving it implied.
 */

/** The largest subgroup capstat will chart from a column. */
export const MAX_SUBGROUP_SIZE = 25;

/** Above this, the range loses too much efficiency and the s chart is better. */
export const RANGE_CHART_MAX_SIZE = 10;

export interface Subgrouping {
  /** Complete subgroups, each of exactly `size` values. */
  subgroups: number[][];
  /**
   * Values left over because the column does not divide evenly.
   *
   * Kept and reported rather than dropped: a study quietly computed on 60 of
   * 63 measurements is a different study, and nothing on screen would say so.
   */
  leftover: number[];
}

/**
 * Split `values` into consecutive subgroups of `size`.
 *
 * A `size` of 1 or less yields no subgroups and no leftovers -- the caller is
 * on the individuals path and should not be chunking at all.
 */
export function intoSubgroups(values: number[], size: number): Subgrouping {
  if (!Number.isInteger(size) || size < 2) {
    return { subgroups: [], leftover: [] };
  }
  const complete = Math.floor(values.length / size);
  const subgroups: number[][] = [];
  for (let i = 0; i < complete; i += 1) {
    subgroups.push(values.slice(i * size, (i + 1) * size));
  }
  return { subgroups, leftover: values.slice(complete * size) };
}

/**
 * Which dispersion chart suits a subgroup of this size.
 *
 * The range uses only the largest and smallest value, so it discards more of
 * each subgroup as the subgroup grows. Montgomery's usual crossover is 10, and
 * the core warns above it -- so the app picks rather than making the user
 * know, and says which it picked.
 */
export function chartForSize(size: number): "xbar-r" | "xbar-s" {
  return size <= RANGE_CHART_MAX_SIZE ? "xbar-r" : "xbar-s";
}

/**
 * Read a typed subgroup size. Null for anything unusable, which the caller
 * shows as a hint rather than silently treating as individuals.
 */
export function parseSubgroupSize(text: string): number | null {
  if (text.trim() === "") return null;
  const value = Number(text);
  if (!Number.isInteger(value) || value < 1 || value > MAX_SUBGROUP_SIZE) {
    return null;
  }
  return value;
}
