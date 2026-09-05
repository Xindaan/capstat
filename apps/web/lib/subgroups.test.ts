import { describe, expect, it } from "vitest";

import {
  MAX_SUBGROUP_SIZE,
  chartForSize,
  intoSubgroups,
  parseSubgroupSize,
} from "@/lib/subgroups";

describe("intoSubgroups", () => {
  it("splits consecutive values, in file order", () => {
    const { subgroups, leftover } = intoSubgroups([1, 2, 3, 4, 5, 6], 3);
    expect(subgroups).toEqual([
      [1, 2, 3],
      [4, 5, 6],
    ]);
    expect(leftover).toEqual([]);
  });

  it("keeps the remainder instead of dropping it", () => {
    // The whole point: a study quietly computed on 6 of 8 measurements is a
    // different study, and nothing on screen would have said so.
    const { subgroups, leftover } = intoSubgroups([1, 2, 3, 4, 5, 6, 7, 8], 3);
    expect(subgroups).toEqual([
      [1, 2, 3],
      [4, 5, 6],
    ]);
    expect(leftover).toEqual([7, 8]);
  });

  it("yields nothing for a size that is not a subgrouping", () => {
    // Size 1 is the individuals path; the caller must not chunk at all there.
    expect(intoSubgroups([1, 2, 3], 1)).toEqual({
      subgroups: [],
      leftover: [],
    });
    expect(intoSubgroups([1, 2, 3], 0)).toEqual({
      subgroups: [],
      leftover: [],
    });
    expect(intoSubgroups([1, 2, 3], 2.5)).toEqual({
      subgroups: [],
      leftover: [],
    });
  });

  it("makes no subgroup at all from a column shorter than one", () => {
    expect(intoSubgroups([1, 2], 5)).toEqual({
      subgroups: [],
      leftover: [1, 2],
    });
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
