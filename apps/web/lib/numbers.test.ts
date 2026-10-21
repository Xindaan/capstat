import { describe, expect, it } from "vitest";

import {
  readCount,
  readDecimal,
  readNumberList,
  readPastedBlock,
} from "./numbers";

/** The value of a successful read, or the failure's reason, for terse asserts. */
function value<T>(read: ReturnType<typeof readDecimal> & { value?: T }) {
  return read.ok ? read.value : `refused: ${read.reason}`;
}

describe("readDecimal", () => {
  it("reads a point and a comma as the same decimal mark", () => {
    expect(value(readDecimal("3.29"))).toBe(3.29);
    expect(value(readDecimal("3,29"))).toBe(3.29);
    expect(value(readDecimal("-0,5"))).toBe(-0.5);
    expect(value(readDecimal("+.5"))).toBe(0.5);
    expect(value(readDecimal(",5"))).toBe(0.5);
    expect(value(readDecimal("5."))).toBe(5);
    expect(value(readDecimal("5,"))).toBe(5);
  });

  it("reads exponents and a typographic minus", () => {
    expect(value(readDecimal("1e-3"))).toBe(0.001);
    expect(value(readDecimal("2,5E2"))).toBe(250);
    expect(value(readDecimal("−3.5"))).toBe(-3.5);
  });

  it("ignores surrounding space, including a non-breaking one", () => {
    expect(value(readDecimal("  3,29 "))).toBe(3.29);
  });

  it("reads three decimals as decimals, not as thousands", () => {
    // 3.290 is an ordinary instrument reading; refusing it would make the field
    // unusable. The one-separator rule is documented in lib/numbers.ts.
    expect(value(readDecimal("3.290"))).toBe(3.29);
    expect(value(readDecimal("1,234"))).toBe(1.234);
  });

  it("calls an empty field empty, not wrong", () => {
    const read = readDecimal("   ");
    expect(read).toMatchObject({ ok: false, empty: true });
  });

  it("refuses thousands separators with that reason", () => {
    for (const text of ["1.234,5", "1,234,567", "1 234", "12.345.678"]) {
      const read = readDecimal(text);
      expect(read.ok).toBe(false);
      if (!read.ok) expect(read.reason).toMatch(/thousands separator/);
    }
  });

  it("refuses everything Number() would have taken and a person would not", () => {
    for (const text of [
      "Infinity",
      "-Infinity",
      "NaN",
      "0x10",
      "1_000",
      "1..2",
      "1,,2",
      "3 29",
      "abc",
      "3.2.1",
      "--1",
      "1e",
      "e5",
      ".",
      ",",
    ]) {
      expect(readDecimal(text).ok, text).toBe(false);
    }
  });

  it("refuses a number too large for a double", () => {
    const read = readDecimal("1e999");
    expect(read.ok).toBe(false);
    if (!read.ok) expect(read.reason).toMatch(/too large/);
  });
});

describe("readCount", () => {
  it("reads whole numbers, with either decimal mark for a whole value", () => {
    expect(value(readCount("12"))).toBe(12);
    expect(value(readCount("12,0"))).toBe(12);
    expect(value(readCount("0", { min: 0 }))).toBe(0);
  });

  it("refuses 5.000 and 1,234 as ambiguous, naming both readings", () => {
    for (const [text, a, b] of [
      ["5.000", 5, 5000],
      ["5,000", 5, 5000],
      ["1,234", 1.234, 1234],
      ["12.345", 12.345, 12345],
    ] as const) {
      const read = readCount(text);
      expect(read.ok, text).toBe(false);
      if (!read.ok) {
        expect(read.reason).toContain(`could mean ${a} or ${b}`);
      }
    }
  });

  it("does not take 5.00 or 0.500 for the ambiguous shape", () => {
    expect(value(readCount("5.00"))).toBe(5);
    expect(readCount("5.0000").ok).toBe(true);
  });

  it("refuses a fraction", () => {
    const read = readCount("2,5");
    expect(read.ok).toBe(false);
    if (!read.ok) expect(read.reason).toMatch(/whole number/);
  });

  it("enforces the bounds, inclusive", () => {
    expect(readCount("1", { min: 2 }).ok).toBe(false);
    expect(readCount("2", { min: 2 }).ok).toBe(true);
    expect(readCount("30", { min: 2, max: 30 }).ok).toBe(true);
    expect(readCount("31", { min: 2, max: 30 }).ok).toBe(false);
    expect(readCount("-1").ok).toBe(false);
  });

  it("passes an empty field and a non-number through unchanged", () => {
    expect(readCount("")).toMatchObject({ ok: false, empty: true });
    expect(readCount("x").ok).toBe(false);
  });
});

describe("readNumberList", () => {
  const values = (text: string) => {
    const read = readNumberList(text);
    return read.ok ? read.value.values : `refused: ${read.reason}`;
  };

  it("accepts commas, spaces, semicolons and new lines as separators", () => {
    expect(values("1, 2\n3;4  5")).toEqual([1, 2, 3, 4, 5]);
    expect(values("1,\n2,")).toEqual([1, 2]);
    expect(values("1 ,2")).toEqual([1, 2]);
    expect(values("7\t8")).toEqual([7, 8]);
  });

  it("reads '36,1 35,9' as two readings", () => {
    const read = readNumberList("36,1 35,9");
    expect(read).toEqual({
      ok: true,
      value: { values: [36.1, 35.9], decimalComma: true },
    });
  });

  it("reads a decimal-comma column, a row, and semicolon-separated readings", () => {
    expect(values("36,1\n35,9\n36,0")).toEqual([36.1, 35.9, 36]);
    expect(values("36,1\t35,9\t36,0")).toEqual([36.1, 35.9, 36]);
    expect(values("36,1;35,9;36,0")).toEqual([36.1, 35.9, 36]);
    expect(values("36,1\r\n35,9\r\n")).toEqual([36.1, 35.9]);
  });

  it("allows point decimals next to a comma-free decimal-comma text only per token", () => {
    // A dot inside a token that also has no comma is fine in a decimal-comma
    // text; it is the dot AND comma in one token that cannot be read.
    expect(values("36,1 35.9")).toEqual([36.1, 35.9]);
  });

  it("does not flag a point-decimal list as decimal-comma", () => {
    const read = readNumberList("36.1, 35.9, 36");
    expect(read).toEqual({
      ok: true,
      value: { values: [36.1, 35.9, 36], decimalComma: false },
    });
  });

  it("refuses a text that mixes decimal commas with comma separators", () => {
    for (const text of ["36,1, 35,9", "36,1 , 35,9", "1,5\n2,\n3"]) {
      const read = readNumberList(text);
      expect(read.ok, text).toBe(false);
      if (!read.ok) expect(read.reason).toMatch(/two ways/);
    }
  });

  it("refuses a token that could be one number or several", () => {
    for (const text of ["1,2,3", "10.1,10.2", "36.1,35.9 36.0", "1.234,5"]) {
      const read = readNumberList(text);
      expect(read.ok, text).toBe(false);
      if (!read.ok) expect(read.reason).toMatch(/one number or several/);
    }
  });

  it("returns the reason for a non-numeric token and never drops it", () => {
    for (const text of ["1, 2, oops, 4", "1 2 NaN", "1 2 Infinity", "1;x"]) {
      expect(readNumberList(text).ok, text).toBe(false);
    }
    const read = readNumberList("1, 2, oops, 4");
    if (!read.ok) expect(read.reason).toContain('"oops"');
  });

  it("calls empty input empty", () => {
    expect(readNumberList("")).toMatchObject({ ok: false, empty: true });
    expect(readNumberList("  \n ")).toMatchObject({ ok: false, empty: true });
  });

  it("reads negatives, exponents and the typographic minus", () => {
    expect(values("-1,5 −2,5 1e-2")).toEqual([-1.5, -2.5, 0.01]);
  });
});

describe("readPastedBlock", () => {
  const cells = (text: string) => {
    const read = readPastedBlock(text);
    if (read === null) return null;
    return read.ok ? read.value : `refused: ${read.reason}`;
  };

  it("ignores text without a tab or a new line: a single value is not a block", () => {
    expect(cells("3,29")).toBeNull();
    expect(cells("3,29 3,41")).toBeNull();
  });

  it("splits rows on new lines and columns on tabs, keeping decimal commas", () => {
    expect(cells("3,29\t3,41\n3,08\t3,25\n")).toEqual([
      ["3,29", "3,41"],
      ["3,08", "3,25"],
    ]);
    expect(cells("1\r\n2\r\n3")).toEqual([["1"], ["2"], ["3"]]);
    expect(cells("1\t2\t3")).toEqual([["1", "2", "3"]]);
  });

  it("refuses the whole block, naming the cell, if any cell is not a number", () => {
    const refused = cells("Part\tTrial 1\n1\t3,2");
    expect(refused).toMatch(/^refused: Nothing was pasted: row 1, column 1/);
    expect(cells("1\t2\n3\t\n")).toMatch(/row 2, column 2/);
  });
});
