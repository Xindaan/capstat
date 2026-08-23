"use client";

import type { EChartsOption } from "echarts";

import { useEchart, usePrefersDark } from "@/lib/echarts";

export interface OcCurveChartProps {
  /** Incoming lot quality, as a fraction defective. */
  fractionDefective: number[];
  /** Probability of accepting a lot of that quality. */
  probabilityAccept: number[];
  /** The producer's quality level, marked on the curve. */
  aql: number;
  /** The consumer's quality level, marked on the curve. */
  ltpd: number;
}

interface Theme {
  axis: string;
  grid: string;
  line: string;
  aql: string;
  ltpd: string;
  tooltipBg: string;
  tooltipText: string;
}

function themeFor(dark: boolean): Theme {
  return dark
    ? {
        axis: "#a1a1a1",
        grid: "#2a2a2a",
        line: "#93a4bd",
        aql: "#34d399",
        ltpd: "#f87171",
        tooltipBg: "#171717",
        tooltipText: "#ededed",
      }
    : {
        axis: "#6b6b6b",
        grid: "#ececec",
        line: "#3f5a80",
        aql: "#059669",
        ltpd: "#dc2626",
        tooltipBg: "#ffffff",
        tooltipText: "#171717",
      };
}

const pct = (fraction: number) => fraction * 100;

/**
 * The operating characteristic curve: the probability of accepting a lot
 * against how defective that lot really is.
 *
 * Both quality levels are drawn on it, because the whole point of the curve is
 * how steeply it falls between them — a plan is chosen by looking at that gap,
 * not at either point alone. Axes are in percent defective, which is how AQLs
 * are always quoted, while the API speaks fractions.
 */
export function OcCurveChart({
  fractionDefective,
  probabilityAccept,
  aql,
  ltpd,
}: OcCurveChartProps) {
  const dark = usePrefersDark();

  const buildOption = (): EChartsOption => {
    const t = themeFor(dark);
    const points = fractionDefective.map((p, i) => [
      pct(p),
      probabilityAccept[i],
    ]);

    const marker = (value: number, color: string, name: string) => ({
      xAxis: pct(value),
      lineStyle: { color, type: "dashed" as const, width: 1.5 },
      label: {
        formatter: name,
        color,
        position: "end" as const,
        // rotate: 0 is load-bearing. A markLine label inherits the line's
        // direction, and these lines are vertical -- left alone, ECharts turns
        // "AQL" on its side and the top of the label is clipped by the grid.
        // The control chart never hit this because its marklines are horizontal.
        rotate: 0,
        distance: 6,
        fontSize: 11,
      },
    });

    return {
      animation: false,
      grid: { left: 56, right: 24, top: 32, bottom: 44 },
      xAxis: {
        type: "value",
        name: "% defective",
        nameLocation: "middle",
        nameGap: 26,
        nameTextStyle: { color: t.axis, fontSize: 11 },
        axisLine: { lineStyle: { color: t.axis } },
        axisLabel: { color: t.axis, fontSize: 11 },
        splitLine: { lineStyle: { color: t.grid } },
      },
      yAxis: {
        type: "value",
        name: "P(accept)",
        min: 0,
        max: 1,
        nameTextStyle: { color: t.axis, fontSize: 11, align: "left" },
        axisLine: { lineStyle: { color: t.axis } },
        axisLabel: { color: t.axis, fontSize: 11 },
        splitLine: { lineStyle: { color: t.grid } },
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: t.tooltipBg,
        borderWidth: 0,
        textStyle: { color: t.tooltipText, fontSize: 12 },
        valueFormatter: (v) =>
          typeof v === "number" ? v.toFixed(3) : String(v),
      },
      series: [
        {
          type: "line",
          name: "P(accept)",
          data: points,
          showSymbol: false,
          smooth: false,
          lineStyle: { color: t.line, width: 2 },
          markLine: {
            symbol: "none",
            silent: true,
            data: [marker(aql, t.aql, "AQL"), marker(ltpd, t.ltpd, "LTPD")],
          },
        },
      ],
    };
  };

  const ref = useEchart(buildOption, [
    fractionDefective,
    probabilityAccept,
    aql,
    ltpd,
    dark,
  ]);

  // See control-chart.tsx: the name is derived from what is drawn (T-0060).
  // The two acceptance probabilities are read off the curve rather than
  // recomputed, so the sentence quotes the same points the picture plots.
  const nearest = (p: number): number | null => {
    if (fractionDefective.length === 0) return null;
    let best = 0;
    for (let i = 1; i < fractionDefective.length; i += 1) {
      if (
        Math.abs(fractionDefective[i] - p) <
        Math.abs(fractionDefective[best] - p)
      ) {
        best = i;
      }
    }
    return probabilityAccept[best];
  };
  const say = (p: number): string => {
    const pa = nearest(p);
    return pa == null ? "not plotted" : `about ${(pa * 100).toFixed(0)} %`;
  };
  const label =
    `Operating characteristic curve: acceptance probability against percent ` +
    `defective. At the AQL (${pct(aql).toFixed(2)} %) the plan accepts ` +
    `${say(aql)} of lots; at the LTPD (${pct(ltpd).toFixed(2)} %), ${say(ltpd)}.`;

  return (
    <div ref={ref} role="img" aria-label={label} className="h-64 w-full" />
  );
}
