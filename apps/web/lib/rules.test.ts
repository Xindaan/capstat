import { describe, expect, it } from "vitest";

import { describeRuleSelection } from "@/lib/rules";

describe("describeRuleSelection", () => {
  it("collapses a contiguous run to a range", () => {
    expect(describeRuleSelection([1, 2, 3, 4])).toBe("1–4");
  });

  it("lists a gapped selection instead of implying a range", () => {
    // The dangerous failure: "1–5" would claim rule 3 and 4 were applied.
    expect(describeRuleSelection([1, 2, 5])).toBe("1, 2, 5");
  });

  it("sorts before describing, whatever order the clicks arrived in", () => {
    expect(describeRuleSelection([4, 1, 3, 2])).toBe("1–4");
    expect(describeRuleSelection([5, 1])).toBe("1, 5");
  });

  it("does not turn a pair into a range", () => {
    // "1–2" reads as a range of a set that is more clearly written out.
    expect(describeRuleSelection([1, 2])).toBe("1, 2");
  });

  it("says none rather than producing an empty label", () => {
    expect(describeRuleSelection([])).toBe("none");
  });

  it("handles a single rule", () => {
    expect(describeRuleSelection([7])).toBe("7");
  });
});
