"use client";

import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import type {
  CustomSeriesRenderItemAPI,
  CustomSeriesRenderItemParams,
} from "echarts";

import { useEchart, usePrefersDark } from "@/lib/echarts";
import {
  capabilityDomain,
  histogram,
  normalPdf,
  type NormalFit,
} from "@/lib/stats";

export type { NormalFit };

interface Props {
  values: number[];
  lsl: number | null;
  usl: number | null;
  target: number | null;
  /** Fitted normal (overall) params; null when the path is non-normal. */
  fit: NormalFit | null;
}

interface Theme {
  axis: string;
  grid: string;
  bar: string;
  pdf: string;
  spec: string;
  target: string;
  tooltipBg: string;
  tooltipText: string;
}

function themeFor(dark: boolean): Theme {
  return dark
    ? {
        axis: "#a1a1a1",
        grid: "#2a2a2a",
        bar: "rgba(96, 165, 250, 0.55)",
        pdf: "#fbbf24",
        spec: "#f87171",
        target: "#34d399",
        tooltipBg: "#171717",
        tooltipText: "#ededed",
      }
    : {
        axis: "#6b6b6b",
        grid: "#ececec",
        bar: "rgba(37, 99, 235, 0.45)",
        pdf: "#d97706",
        spec: "#dc2626",
        target: "#059669",
        tooltipBg: "#ffffff",
        tooltipText: "#171717",
      };
}

export function CapabilityHistogram({ values, lsl, usl, target, fit }: Props) {
  const dark = usePrefersDark();

  const bins = useMemo(() => histogram(values), [values]);

  // The x-range must always span the spec limits, even when a limit sits well
  // outside the data (a capable process, or a USL far above the sample) --
  // otherwise the spec markLine is clipped and silently vanishes.
  const domain = useMemo(
    () => capabilityDomain(bins.edges, [lsl, usl, target], fit),
    [bins, lsl, usl, target, fit],
  );

  // Sampled normal PDF across the full domain (null on the non-normal paths).
  const pdfLine = useMemo(() => {
    if (!fit || fit.sigma <= 0) return null;
    const steps = 160;
    return Array.from({ length: steps + 1 }, (_, i): [number, number] => {
      const x = domain.lo + ((domain.hi - domain.lo) * i) / steps;
      return [x, normalPdf(x, fit.mean, fit.sigma)];
    });
  }, [fit, domain]);

  const buildOption = (): EChartsOption => {
    const t = themeFor(dark);

    const specLine = (value: number, color: string, name: string) => ({
      xAxis: value,
      lineStyle: { color, type: "dashed" as const, width: 1.5 },
      label: {
        formatter: name,
        color,
        position: "insideEndTop" as const,
        fontSize: 11,
      },
    });
    const markLines = [
      lsl != null ? specLine(lsl, t.spec, "LSL") : null,
      usl != null ? specLine(usl, t.spec, "USL") : null,
      target != null ? specLine(target, t.target, "Target") : null,
    ].filter((v): v is NonNullable<typeof v> => v != null);

    return {
        animation: false,
        grid: { left: 8, right: 16, top: 24, bottom: 24, containLabel: true },
        tooltip: {
          trigger: "axis",
          backgroundColor: t.tooltipBg,
          borderWidth: 0,
          textStyle: { color: t.tooltipText, fontSize: 12 },
        },
        xAxis: {
          type: "value",
          min: domain.lo,
          max: domain.hi,
          axisLine: { lineStyle: { color: t.axis } },
          axisLabel: { color: t.axis },
          splitLine: { show: false },
        },
        yAxis: {
          type: "value",
          name: "density",
          nameTextStyle: { color: t.axis, align: "left" },
          axisLabel: { color: t.axis },
          splitLine: { lineStyle: { color: t.grid } },
        },
        series: [
          {
            type: "custom",
            name: "Histogram",
            dimensions: ["x0", "x1", "density"],
            encode: { x: [0, 1], y: 2, tooltip: [2] },
            data: bins.bars,
            renderItem: (
              _params: CustomSeriesRenderItemParams,
              api: CustomSeriesRenderItemAPI,
            ) => {
              const x0 = api.value(0) as number;
              const x1 = api.value(1) as number;
              const y = api.value(2) as number;
              const start = api.coord([x0, y]);
              const base = api.coord([x1, 0]);
              return {
                type: "rect",
                shape: {
                  x: start[0] + 0.5,
                  y: start[1],
                  width: base[0] - start[0] - 1,
                  height: base[1] - start[1],
                },
                // Literal fill rather than the deprecated api.style().
                style: { fill: t.bar },
              };
            },
            itemStyle: { color: t.bar },
            // The spec limits ride on the histogram series so they render even
            // when there is no fitted curve (the non-normal paths).
            markLine: {
              symbol: "none",
              silent: true,
              data: markLines,
            },
          },
          ...(pdfLine
            ? [
                {
                  type: "line" as const,
                  name: "Normal fit",
                  data: pdfLine,
                  showSymbol: false,
                  smooth: true,
                  lineStyle: { color: t.pdf, width: 2 },
                  z: 3,
                },
              ]
            : []),
        ],
    };
  };

  const ref = useEchart(buildOption, [bins, pdfLine, domain, lsl, usl, target, dark]);

  return <div ref={ref} className="h-72 w-full" />;
}
