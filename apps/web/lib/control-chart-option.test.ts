import { describe, expect, it } from "vitest";

import {
  buildControlChartOption,
  describeLimits,
  formatLimit,
  type ControlChartProps,
} from "./control-chart-option";

// An in-control series whose data stay well inside the limits -- the normal
// case for a small sample, and the one the old option got wrong: the axis was
// fitted to the data alone, so ECharts clipped both limit lines away.
function inControl(overrides: Partial<ControlChartProps> = {}) {
  return {
    title: "Individuals",
    points: [9.99, 10.01, 10.0, 10.02, 9.98, 10.01, 9.99, 10.0],
    center: 10,
    lower: 9.8,
    upper: 10.2,
    violations: [],
    zones: true,
    ...overrides,
  } satisfies ControlChartProps;
}

/** The explicit [min, max] the option gives the y-axis. */
function extent(props: ControlChartProps): [number, number] {
  const option = buildControlChartOption(props, false);
  const y = option.yAxis as { min?: unknown; max?: unknown };
  expect(typeof y.min).toBe("number");
  expect(typeof y.max).toBe("number");
  return [y.min as number, y.max as number];
}

/** The label text of every markLine entry, by line value. */
function markLabels(props: ControlChartProps): Map<number, string> {
  const option = buildControlChartOption(props, false);
  const series = option.series as {
    markLine?: {
      data: { yAxis: number; label: { show?: boolean; formatter?: string } }[];
    };
  }[];
  const out = new Map<number, string>();
  for (const entry of series[0].markLine?.data ?? []) {
    if (entry.label.show !== false) {
      out.set(entry.yAxis, entry.label.formatter ?? "");
    }
  }
  return out;
}

describe("buildControlChartOption y-axis", () => {
  it("contains UCL and LCL when the data lie inside the limits", () => {
    const props = inControl();
    const [min, max] = extent(props);
    expect(min).toBeLessThanOrEqual(props.lower);
    expect(max).toBeGreaterThanOrEqual(props.upper);
  });

  it("keeps the limit lines off the very edge of the plot", () => {
    const props = inControl();
    const [min, max] = extent(props);
    expect(min).toBeLessThan(props.lower);
    expect(max).toBeGreaterThan(props.upper);
  });

  it("still contains the data when they run beyond the limits", () => {
    const props = inControl({ points: [9.5, 10, 10.6], violations: [0, 2] });
    const [min, max] = extent(props);
    expect(min).toBeLessThanOrEqual(9.5);
    expect(max).toBeGreaterThanOrEqual(10.6);
  });

  it("contains the lower limit on its own (moving range: LCL 0)", () => {
    const props = inControl({
      points: [0.05, 0.07, 0.06],
      center: 0.06,
      lower: 0,
      upper: 0.2,
      zones: false,
    });
    const [min, max] = extent(props);
    expect(min).toBeLessThanOrEqual(0);
    expect(max).toBeGreaterThanOrEqual(0.2);
  });

  it("contains the zone lines even when they fall outside the limits", () => {
    // sigma = 0.1 so the -2 sigma line is at 9.8, below the (odd) LCL 9.95.
    const props = inControl({ lower: 9.95, upper: 10.3 });
    const [min] = extent(props);
    expect(min).toBeLessThanOrEqual(9.8);
  });

  it("does not stretch for zone lines that are not drawn", () => {
    const props = inControl({ lower: 9.95, upper: 10.3, zones: false });
    const [min] = extent(props);
    expect(min).toBeGreaterThan(9.8);
  });

  it("gives a constant series with collapsed limits a non-empty axis", () => {
    const props = inControl({
      points: [10, 10, 10],
      lower: 10,
      upper: 10,
      zones: false,
    });
    const [min, max] = extent(props);
    expect(min).toBeLessThan(10);
    expect(max).toBeGreaterThan(10);
  });
});

describe("buildControlChartOption labels", () => {
  it("prints the value of the centre line and both limits", () => {
    const labels = markLabels(inControl());
    expect(labels.get(10)).toBe("CL 10");
    expect(labels.get(10.2)).toBe("UCL 10.2");
    expect(labels.get(9.8)).toBe("LCL 9.8");
  });

  it("does not label the zone lines", () => {
    expect(markLabels(inControl()).size).toBe(3);
  });
});

describe("formatLimit", () => {
  it("drops floating-point noise and trailing zeros", () => {
    expect(formatLimit(10.056900000000001)).toBe("10.0569");
    expect(formatLimit(10)).toBe("10");
    expect(formatLimit(9.943)).toBe("9.943");
  });

  it("keeps six significant digits", () => {
    expect(formatLimit(12345.6789)).toBe("12345.7");
    expect(formatLimit(-0.0123456789)).toBe("-0.0123457");
  });

  it("writes zero and tiny or huge numbers without lying", () => {
    expect(formatLimit(0)).toBe("0");
    expect(formatLimit(2.5e-7)).toBe("2.5e-7");
    expect(formatLimit(4e12)).toBe("4e+12");
  });

  it("passes a non-finite value through visibly", () => {
    expect(formatLimit(Number.NaN)).toBe("NaN");
  });
});

describe("describeLimits", () => {
  it("lists CL, UCL and LCL in that order", () => {
    expect(describeLimits(10, 9.8, 10.2)).toBe("CL 10, UCL 10.2, LCL 9.8");
  });
});
