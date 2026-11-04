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

/**
 * A column as the ingest endpoint returns it: the values that survived, and the
 * 0-based data row each one came from. The rows are what make a gap visible --
 * `values` alone is compacted, and cutting it moves every boundary after a
 * blank cell (T-0102).
 */
export interface RowedColumn {
  values: number[];
  rows: number[];
}

/** A block of rows that lost a cell and so could not make a subgroup. */
export interface IncompleteSubgroup {
  /** 1-based, the way the page counts subgroups. */
  index: number;
  /** How many of the `size` values it still holds. */
  present: number;
}

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
  /**
   * Blocks of `size` rows with a missing cell inside. They are left out and
   * named, not re-cut from the values after them, which would mix neighbouring
   * subgroups.
   */
  incomplete: IncompleteSubgroup[];
}

/**
 * Split a column into subgroups of `size` consecutive **rows**.
 *
 * Subgroup k is rows [k*size, (k+1)*size) of the file. With no gap that is the
 * same as chunking the values; with a blank cell in row 8 the compacted list
 * would shift every later boundary by one, so the block that lost a cell is
 * reported as incomplete and every other block stays where the file put it.
 * Rows after the last full block are the leftover.
 *
 * A `size` of 1 or less yields nothing -- the caller is on the individuals path
 * and should not be chunking at all.
 */
export function intoSubgroups(column: RowedColumn, size: number): Subgrouping {
  if (!Number.isInteger(size) || size < 2 || column.rows.length === 0) {
    return { subgroups: [], leftover: [], incomplete: [] };
  }
  const lastRow = column.rows[column.rows.length - 1];
  const blocks = Math.floor((lastRow + 1) / size);
  const held: number[][] = Array.from({ length: blocks }, () => []);
  const leftover: number[] = [];
  column.rows.forEach((row, i) => {
    const block = Math.floor(row / size);
    if (block < blocks) held[block].push(column.values[i]);
    else leftover.push(column.values[i]);
  });
  const subgroups: number[][] = [];
  const incomplete: IncompleteSubgroup[] = [];
  held.forEach((group, k) => {
    if (group.length === size) subgroups.push(group);
    else incomplete.push({ index: k + 1, present: group.length });
  });
  return { subgroups, leftover, incomplete };
}

/**
 * Missing cells *inside* the column: rows between its first and last value that
 * hold no value. Blanks before the first or after the last value are not gaps
 * -- the column is just offset or shorter than its neighbour -- and shift
 * nothing.
 */
export function interiorGaps(column: RowedColumn): number {
  if (column.rows.length === 0) return 0;
  const first = column.rows[0];
  const last = column.rows[column.rows.length - 1];
  return last - first + 1 - column.rows.length;
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
