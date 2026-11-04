import type { EChartsOption } from "echarts";

/**
 * The ECharts option for one control chart, as a pure function of its props.
 *
 * It lives outside the component so a test can build the option for any series
 * and read back what the chart will draw -- T-0098 (CHART-1 / WEB-8) was a
 * chart that dropped its own control limits, and nothing short of looking at
 * the built option could have seen it from the data side.
 */

export interface ControlChartProps {
  title: string;
  points: number[];
  center: number;
  lower: number;
  upper: number;
  /** Indices (0-based) the core flagged as out of control. */
  violations: number[];
  /** Indices flagged by run rules (patterns inside the limits). */
  ruleFlags?: number[];
  /** Draw the +/-1 and +/-2 sigma zone lines (individuals chart). */
  zones?: boolean;
}

interface Theme {
  axis: string;
  grid: string;
  line: string;
  center: string;
  limit: string;
  zone: string;
  flag: string;
  tooltipBg: string;
  tooltipText: string;
}

function themeFor(dark: boolean): Theme {
  return dark
    ? {
        axis: "#a1a1a1",
        grid: "#2a2a2a",
        line: "#93a4bd",
        center: "#8b8b8b",
        limit: "#f87171",
        zone: "#3a3a3a",
        flag: "#fbbf24",
        tooltipBg: "#171717",
        tooltipText: "#ededed",
      }
    : {
        axis: "#6b6b6b",
        grid: "#ececec",
        line: "#3f5a80",
        center: "#6b6b6b",
        limit: "#dc2626",
        zone: "#d4d4d4",
        flag: "#d97706",
        tooltipBg: "#ffffff",
        tooltipText: "#171717",
      };
}

/**
 * A limit as the reader should quote it: six significant digits, no trailing
 * zeros, and no exponent unless the number really is tiny or huge.
 */
export function formatLimit(value: number): string {
  if (!Number.isFinite(value)) return String(value);
  if (value === 0) return "0";
  const magnitude = Math.abs(value);
  if (magnitude < 1e-4 || magnitude >= 1e9) {
    return value.toExponential(4).replace(/\.?0+e/, "e");
  }
  return String(Number(value.toPrecision(6)));
}

/** "CL 10, UCL 10.2, LCL 9.8" -- the limits as one sentence-sized string. */
export function describeLimits(
  center: number,
  lower: number,
  upper: number,
): string {
  return `CL ${formatLimit(center)}, UCL ${formatLimit(upper)}, LCL ${formatLimit(lower)}`;
}

/**
 * The y-axis extent: every plotted point, the centre line, both limits and the
 * zone lines, plus a margin.
 *
 * ECharts' `scale: true` fits the axis to the *series* only, and a markLine
 * outside that extent is not drawn at all, label included (T-0098, CHART-1).
 * An in-control process rarely reaches 3 sigma, so the limits were missing
 * exactly when nothing was wrong. The extent is therefore computed here and
 * handed over as a number, never left to the series.
 */
export function yAxisExtent(values: number[]): { min: number; max: number } {
  const finite = values.filter((v) => Number.isFinite(v));
  const lo = Math.min(...finite);
  const hi = Math.max(...finite);
  const span = hi - lo;
  // A constant series with collapsed limits has no span to take a margin from.
  const pad = span > 0 ? span * 0.08 : Math.max(Math.abs(hi) * 0.05, 1e-6);
  return { min: lo - pad, max: hi + pad };
}

export function buildControlChartOption(
  {
    title,
    points,
    center,
    lower,
    upper,
    violations,
    ruleFlags = [],
    zones = false,
  }: ControlChartProps,
  dark: boolean,
): EChartsOption {
  const t = themeFor(dark);
  const sigma = (upper - center) / 3;
  const categories = points.map((_, i) => String(i + 1));

  const line = (
    value: number,
    color: string,
    name: string,
    dashed = false,
  ) => ({
    yAxis: value,
    lineStyle: {
      color,
      type: dashed ? ("dashed" as const) : ("solid" as const),
      width: dashed ? 1.5 : 1,
    },
    label: {
      formatter: `${name} ${formatLimit(value)}`,
      color,
      position: "insideEndTop" as const,
      fontSize: 11,
    },
  });

  const zoneLine = (value: number) => ({
    yAxis: value,
    lineStyle: { color: t.zone, type: "dotted" as const, width: 1 },
    label: { show: false },
  });

  const zoneValues = [
    center + sigma,
    center - sigma,
    center + 2 * sigma,
    center - 2 * sigma,
  ];
  const { min, max } = yAxisExtent([
    ...points,
    center,
    lower,
    upper,
    ...(zones ? zoneValues : []),
  ]);

  const markLineData = [
    line(center, t.center, "CL"),
    line(upper, t.limit, "UCL", true),
    line(lower, t.limit, "LCL", true),
    ...(zones ? zoneValues.map(zoneLine) : []),
  ];

  return {
    animation: false,
    title: {
      text: title,
      left: 0,
      top: 0,
      textStyle: { color: t.axis, fontSize: 12, fontWeight: "normal" },
    },
    grid: { left: 8, right: 48, top: 32, bottom: 24, containLabel: true },
    tooltip: {
      trigger: "axis",
      backgroundColor: t.tooltipBg,
      borderWidth: 0,
      textStyle: { color: t.tooltipText, fontSize: 12 },
    },
    xAxis: {
      type: "category",
      data: categories,
      boundaryGap: false,
      axisLine: { lineStyle: { color: t.axis } },
      axisLabel: { color: t.axis },
    },
    yAxis: {
      type: "value",
      min,
      max,
      axisLabel: { color: t.axis },
      splitLine: { lineStyle: { color: t.grid } },
    },
    series: [
      {
        type: "line",
        name: title,
        data: points,
        showSymbol: true,
        symbolSize: 4,
        lineStyle: { color: t.line, width: 1.5 },
        itemStyle: { color: t.line },
        markLine: { symbol: "none", silent: true, data: markLineData },
        z: 2,
      },
      {
        type: "scatter",
        name: "Run-rule flag",
        data: ruleFlags.map((i) => [i, points[i]]),
        symbolSize: 11,
        itemStyle: {
          color: "transparent",
          borderColor: t.flag,
          borderWidth: 2,
        },
        z: 3,
      },
      {
        type: "scatter",
        name: "Out of control",
        data: violations.map((i) => [i, points[i]]),
        symbolSize: 7,
        itemStyle: { color: t.limit },
        z: 4,
      },
    ],
  };
}
