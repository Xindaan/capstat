import { describe, expect, it } from "vitest";

import {
  MAX_SUBGROUP_SIZE,
  chartForSize,
  interiorGaps,
  intoSubgroups,
  parseSubgroupSize,
} from "@/lib/subgroups";

/** A column with no gaps: row i holds value i. */
const dense = (values: number[]) => ({
  values,
  rows: values.map((_, i) => i),
});

describe("intoSubgroups", () => {
  it("splits consecutive values, in file order", () => {
    const { subgroups, leftover } = intoSubgroups(dense([1, 2, 3, 4, 5, 6]), 3);
    expect(subgroups).toEqual([
      [1, 2, 3],
      [4, 5, 6],
    ]);
    expect(leftover).toEqual([]);
  });

  it("keeps the remainder instead of dropping it", () => {
    // The whole point: a study quietly computed on 6 of 8 measurements is a
    // different study, and nothing on screen would have said so.
    const { subgroups, leftover } = intoSubgroups(
      dense([1, 2, 3, 4, 5, 6, 7, 8]),
      3,
    );
    expect(subgroups).toEqual([
      [1, 2, 3],
      [4, 5, 6],
    ]);
    expect(leftover).toEqual([7, 8]);
  });

  it("yields nothing for a size that is not a subgrouping", () => {
    // Size 1 is the individuals path; the caller must not chunk at all there.
    const empty = { subgroups: [], leftover: [], incomplete: [] };
    expect(intoSubgroups(dense([1, 2, 3]), 1)).toEqual(empty);
    expect(intoSubgroups(dense([1, 2, 3]), 0)).toEqual(empty);
    expect(intoSubgroups(dense([1, 2, 3]), 2.5)).toEqual(empty);
    expect(intoSubgroups({ values: [], rows: [] }, 3)).toEqual(empty);
  });

  it("makes no subgroup at all from a column shorter than one", () => {
    expect(intoSubgroups(dense([1, 2]), 5)).toEqual({
      subgroups: [],
      leftover: [1, 2],
      incomplete: [],
    });
  });

  it("cuts by row, so a blank cell costs its own subgroup and moves no other", () => {
    // Six rows of three; row 4 (0-based) is blank. Cutting the compacted values
    // [1,2,3,4,6,7,8,9] would give [1,2,3] [4,6,7] [8,9] -- the second
    // subgroup silently mixes rows 3, 5 and 6 (CHART-2).
    const column = {
      values: [1, 2, 3, 4, 6, 7, 8, 9],
      rows: [0, 1, 2, 3, 5, 6, 7, 8],
    };
    const { subgroups, leftover, incomplete } = intoSubgroups(column, 3);
    expect(subgroups).toEqual([
      [1, 2, 3],
      [7, 8, 9],
    ]);
    expect(incomplete).toEqual([{ index: 2, present: 2 }]);
    expect(leftover).toEqual([]);
  });

  it("does not move the leftover boundary when a gap sits before it", () => {
    // Rows 0-7, row 1 blank: two full blocks of three would need rows 0-5;
    // block 1 lost a cell, block 2 (rows 3-5) is intact, rows 6-7 are leftover.
    const column = {
      values: [1, 3, 4, 5, 6, 7, 8],
      rows: [0, 2, 3, 4, 5, 6, 7],
    };
    const { subgroups, leftover, incomplete } = intoSubgroups(column, 3);
    expect(subgroups).toEqual([[4, 5, 6]]);
    expect(incomplete).toEqual([{ index: 1, present: 2 }]);
    expect(leftover).toEqual([7, 8]);
  });

  it("treats blanks after the last value as no gap at all", () => {
    // A column shorter than its neighbour: rows 6-9 are empty, nothing shifts.
    const { subgroups, incomplete } = intoSubgroups(
      dense([1, 2, 3, 4, 5, 6]),
      3,
    );
    expect(subgroups).toHaveLength(2);
    expect(incomplete).toEqual([]);
  });

  it("starts counting at the row the data starts on", () => {
    // Leading blanks are rows, too: the first value sits in row 2, so block 0
    // holds one value and is incomplete, and block 1 (rows 3-5) is intact.
    const column = { values: [1, 2, 3, 4], rows: [2, 3, 4, 5] };
    const { subgroups, incomplete } = intoSubgroups(column, 3);
    expect(subgroups).toEqual([[2, 3, 4]]);
    expect(incomplete).toEqual([{ index: 1, present: 1 }]);
  });
});

describe("interiorGaps", () => {
  it("counts the blank rows between the first and last value", () => {
    expect(interiorGaps({ values: [1, 2, 3], rows: [0, 2, 5] })).toBe(3);
    expect(interiorGaps(dense([1, 2, 3]))).toBe(0);
  });

  it("ignores blanks before the first and after the last value", () => {
    expect(interiorGaps({ values: [1, 2], rows: [3, 4] })).toBe(0);
    expect(interiorGaps({ values: [], rows: [] })).toBe(0);
  });
});

describe("chartForSize", () => {
  it("switches from the range to the standard deviation above 10", () => {
    // The range reads only two values per subgroup, so it discards more of
    // each subgroup as the subgroup grows.
    expect(chartForSize(2)).toBe("xbar-r");
    expect(chartForSize(10)).toBe("xbar-r");
    expect(chartForSize(11)).toBe("xbar-s");
    expect(chartForSize(MAX_SUBGROUP_SIZE)).toBe("xbar-s");
  });
});

describe("parseSubgroupSize", () => {
  it("reads a whole number in range", () => {
    expect(parseSubgroupSize("1")).toBe(1);
    expect(parseSubgroupSize("5")).toBe(5);
    expect(parseSubgroupSize(String(MAX_SUBGROUP_SIZE))).toBe(
      MAX_SUBGROUP_SIZE,
    );
  });

  it("refuses anything it cannot subgroup by", () => {
    expect(parseSubgroupSize("")).toBeNull();
    expect(parseSubgroupSize("0")).toBeNull();
    expect(parseSubgroupSize("-2")).toBeNull();
    expect(parseSubgroupSize("2.5")).toBeNull();
    expect(parseSubgroupSize("abc")).toBeNull();
    // Above the range the library computes d2 for at all.
    expect(parseSubgroupSize(String(MAX_SUBGROUP_SIZE + 1))).toBeNull();
  });
});
