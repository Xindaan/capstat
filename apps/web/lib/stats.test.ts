import { describe, expect, it } from "vitest";

import {
  binCount,
  capabilityDomain,
  columnStats,
  histogram,
  normalPdf,
} from "@/lib/stats";

describe("columnStats", () => {
  it("computes min, max and mean in one pass", () => {
    expect(columnStats([2, 5, 1, 4])).toEqual({ min: 1, max: 5, mean: 3 });
  });

  it("handles a single value", () => {
    expect(columnStats([7])).toEqual({ min: 7, max: 7, mean: 7 });
  });

  it("handles negatives", () => {
    expect(columnStats([-3, -1, -2])).toEqual({ min: -3, max: -1, mean: -2 });
  });
});

describe("binCount", () => {
  it("clamps to at least 5 bins", () => {
    const v = [1, 2, 3];
    expect(binCount(v, 1, 3)).toBeGreaterThanOrEqual(5);
  });

  it("never exceeds 40 bins", () => {
    const v = Array.from({ length: 5000 }, (_, i) => i);
    expect(binCount(v, 0, 4999)).toBeLessThanOrEqual(40);
  });

  it("falls back to Sturges when the IQR is zero", () => {
    // All-equal data: IQR = 0, so the FD width is undefined; Sturges applies.
    const v = new Array(16).fill(3);
    const sturges = Math.ceil(Math.log2(16) + 1); // 5
    expect(binCount(v, 3, 3)).toBe(Math.max(5, Math.min(sturges, 40)));
  });
});

describe("histogram", () => {
  const values = [1, 2, 2, 3, 3, 3, 4, 4, 5];

  it("produces edges spanning [min, max] with binCount + 1 entries", () => {
    const { edges } = histogram(values);
    expect(edges[0]).toBe(1);
    expect(edges[edges.length - 1]).toBeCloseTo(5, 10);
    expect(edges.length).toBe(binCount(values, 1, 5) + 1);
  });

  it("is a density: bars integrate to 1", () => {
    const { bars } = histogram(values);
    const area = bars.reduce((sum, [x0, x1, d]) => sum + d * (x1 - x0), 0);
    expect(area).toBeCloseTo(1, 10);
  });

  it("counts every value, including the maximum in the last bin", () => {
    const { bars, edges } = histogram(values);
    const width = edges[1] - edges[0];
    const totalCount = bars.reduce(
      (sum, [, , d]) => sum + Math.round(d * values.length * width),
      0,
    );
    expect(totalCount).toBe(values.length);
  });

  it("does not divide by zero for all-equal data", () => {
    const { bars } = histogram([5, 5, 5, 5]);
    expect(bars.every(([, , d]) => Number.isFinite(d))).toBe(true);
  });
});

describe("normalPdf", () => {
  it("peaks at the mean with the analytic height", () => {
    const sigma = 2;
    expect(normalPdf(10, 10, sigma)).toBeCloseTo(
      1 / (sigma * Math.sqrt(2 * Math.PI)),
      12,
    );
  });

  it("is symmetric about the mean", () => {
    expect(normalPdf(8, 10, 1.5)).toBeCloseTo(normalPdf(12, 10, 1.5), 12);
  });

  it("decreases away from the mean", () => {
    expect(normalPdf(11, 10, 1)).toBeGreaterThan(normalPdf(13, 10, 1));
  });
});

describe("capabilityDomain", () => {
  const edges = [9.9, 10.1];

  it("always includes a spec limit outside the data range", () => {
    const { lo, hi } = capabilityDomain(edges, [null, 12, null], null);
    expect(hi).toBeGreaterThanOrEqual(12);
    expect(lo).toBeLessThanOrEqual(9.9);
  });

  it("ignores null limits", () => {
    const bounded = capabilityDomain(edges, [null, null, null], null);
    expect(bounded.lo).toBeLessThan(9.9);
    expect(bounded.hi).toBeGreaterThan(10.1);
  });

  it("widens to +/- 4 sigma of a fitted normal", () => {
    const { lo, hi } = capabilityDomain(edges, [null, null, null], {
      mean: 10,
      sigma: 1,
    });
    expect(lo).toBeLessThanOrEqual(6);
    expect(hi).toBeGreaterThanOrEqual(14);
  });

  it("adds padding so points are not flush against the axis", () => {
    const { lo, hi } = capabilityDomain(edges, [9.9, 10.1, null], null);
    expect(lo).toBeLessThan(9.9);
    expect(hi).toBeGreaterThan(10.1);
  });
});
