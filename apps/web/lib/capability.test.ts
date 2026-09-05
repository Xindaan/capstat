import { describe, expect, it } from "vitest";

import {
  CAPABLE_AT_OR_ABOVE,
  capabilityBand,
  parseRequiredIndex,
} from "@/lib/capability";

describe("parseRequiredIndex", () => {
  it("reads a positive number", () => {
    expect(parseRequiredIndex("1.33")).toBe(1.33);
    expect(parseRequiredIndex(" 1.67 ")).toBe(1.67);
  });

  it("refuses anything it cannot judge by, rather than substituting a default", () => {
    // null means "unjudged" downstream. Falling back to 1.33 here would put
    // the very assumption back that this field exists to remove.
    expect(parseRequiredIndex("")).toBeNull();
    expect(parseRequiredIndex("   ")).toBeNull();
    expect(parseRequiredIndex("abc")).toBeNull();
    expect(parseRequiredIndex("0")).toBeNull();
    expect(parseRequiredIndex("-1")).toBeNull();
  });
});

describe("capabilityBand", () => {
  it("judges against the stated requirement, not a built-in one", () => {
    // The discriminating case: one index, two customers. 1.35 passes a 1.33
    // requirement and falls short of 1.67 -- and the old fixed threshold
    // called it green for both.
    expect(capabilityBand(1.35, 1.33)).toBe("meets");
    expect(capabilityBand(1.35, 1.67)).toBe("capable");
  });

  it("treats the requirement as inclusive", () => {
    expect(capabilityBand(1.33, 1.33)).toBe("meets");
  });

  it("calls anything below 1.00 incapable, whatever the requirement", () => {
    // 1.00 is not a convention: below it the spread does not fit the
    // tolerance at all, so a lenient requirement cannot make it green.
    expect(capabilityBand(0.95, 1.33)).toBe("incapable");
    expect(capabilityBand(0.95, 0.5)).toBe("meets");
    expect(capabilityBand(0.99, 1.0)).toBe("incapable");
    expect(CAPABLE_AT_OR_ABOVE).toBe(1.0);
  });

  it("holds for a requirement below 1.00", () => {
    expect(capabilityBand(1.1, 0.9)).toBe("meets");
    expect(capabilityBand(0.95, 0.9)).toBe("meets");
    expect(capabilityBand(0.85, 0.9)).toBe("incapable");
  });

  it("judges nothing without a value or a requirement", () => {
    expect(capabilityBand(null, 1.33)).toBe("unjudged");
    expect(capabilityBand(undefined, 1.33)).toBe("unjudged");
    expect(capabilityBand(Number.NaN, 1.33)).toBe("unjudged");
    expect(capabilityBand(1.5, null)).toBe("unjudged");
  });
});
