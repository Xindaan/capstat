"use client";

import type { EChartsOption } from "echarts";

import { useEchart, usePrefersDark } from "@/lib/echarts";

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

export function ControlChart({
  title,
  points,
  center,
  lower,
  upper,
  violations,
  ruleFlags = [],
  zones = false,
}: ControlChartProps) {
  const dark = usePrefersDark();

  const buildOption = (): EChartsOption => {
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
        formatter: name,
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

    const markLineData = [
      line(center, t.center, "CL"),
      line(upper, t.limit, "UCL", true),
      line(lower, t.limit, "LCL", true),
      ...(zones
        ? [
            zoneLine(center + sigma),
            zoneLine(center - sigma),
            zoneLine(center + 2 * sigma),
            zoneLine(center - 2 * sigma),
          ]
        : []),
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
        scale: true,
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
  };

  const ref = useEchart(buildOption, [
    title,
    points,
    center,
    lower,
    upper,
    violations,
    ruleFlags,
    zones,
    dark,
  ]);

  return <div ref={ref} className="h-64 w-full" />;
}
