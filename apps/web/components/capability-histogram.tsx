"use client";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import type { ECharts } from "echarts";

export interface NormalFit {
  mean: number;
  sigma: number;
}

interface Props {
  values: number[];
  lsl: number | null;
  usl: number | null;
  target: number | null;
  /** Fitted normal (overall) params; null when the path is non-normal. */
  fit: NormalFit | null;
}

interface Bins {
  edges: number[];
  /** One [x0, x1, density] triple per bin, density = count / (n * width). */
  bars: [number, number, number][];
}

/** Freedman-Diaconis bin count, with a Sturges fallback and a sane clamp. */
function binCount(values: number[], min: number, max: number): number {
  const n = values.length;
  const sorted = [...values].sort((a, b) => a - b);
  const q = (p: number) => {
    const idx = (n - 1) * p;
    const lo = Math.floor(idx);
    const hi = Math.ceil(idx);
    return sorted[lo] + (sorted[hi] - sorted[lo]) * (idx - lo);
  };
  const iqr = q(0.75) - q(0.25);
  const sturges = Math.ceil(Math.log2(n) + 1);
  if (iqr <= 0 || max <= min) return Math.max(5, Math.min(sturges, 40));
  const width = (2 * iqr) / Math.cbrt(n);
  const fd = Math.ceil((max - min) / width);
  return Math.max(5, Math.min(fd, 40));
}

function histogram(values: number[]): Bins {
  const n = values.length;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const k = binCount(values, min, max);
  const width = (max - min) / k || 1;
  const edges = Array.from({ length: k + 1 }, (_, i) => min + i * width);
  const counts = new Array<number>(k).fill(0);
  for (const v of values) {
    // The last edge is inclusive so the maximum lands in the final bin.
    const raw = Math.floor((v - min) / width);
    const bin = Math.min(raw, k - 1);
    counts[bin] += 1;
  }
  const bars = counts.map(
    (c, i): [number, number, number] => [
      edges[i],
      edges[i + 1],
      c / (n * width),
    ],
  );
  return { edges, bars };
}

function normalPdf(x: number, mean: number, sigma: number): number {
  const z = (x - mean) / sigma;
  return Math.exp(-0.5 * z * z) / (sigma * Math.sqrt(2 * Math.PI));
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

const DARK_QUERY = "(prefers-color-scheme: dark)";

/** Track the colour scheme without a setState-in-effect (React's blessed way). */
function usePrefersDark(): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const mq = window.matchMedia(DARK_QUERY);
      mq.addEventListener("change", onChange);
      return () => mq.removeEventListener("change", onChange);
    },
    () => window.matchMedia(DARK_QUERY).matches,
    () => false,
  );
}

export function CapabilityHistogram({ values, lsl, usl, target, fit }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ECharts | null>(null);
  const dark = usePrefersDark();

  const bins = useMemo(() => histogram(values), [values]);

  // The x-range must always span the spec limits, even when a limit sits well
  // outside the data (a capable process, or a USL far above the sample) --
  // otherwise the spec markLine is clipped and silently vanishes.
  const domain = useMemo(() => {
    const specs = [lsl, usl, target].filter((v): v is number => v != null);
    const edgeLo = bins.edges[0];
    const edgeHi = bins.edges[bins.edges.length - 1];
    const lo = Math.min(edgeLo, ...specs, ...(fit ? [fit.mean - 4 * fit.sigma] : []));
    const hi = Math.max(edgeHi, ...specs, ...(fit ? [fit.mean + 4 * fit.sigma] : []));
    const pad = (hi - lo) * 0.03 || 1;
    return { lo: lo - pad, hi: hi + pad };
  }, [bins, lsl, usl, target, fit]);

  // Sampled normal PDF across the full domain (null on the non-normal paths).
  const pdfLine = useMemo(() => {
    if (!fit || fit.sigma <= 0) return null;
    const steps = 160;
    return Array.from({ length: steps + 1 }, (_, i): [number, number] => {
      const x = domain.lo + ((domain.hi - domain.lo) * i) / steps;
      return [x, normalPdf(x, fit.mean, fit.sigma)];
    });
  }, [fit, domain]);

  // Bumped once the chart is live. echarts is imported asynchronously, so the
  // option effect below cannot rely on chartRef being set on first paint (nor
  // after a StrictMode remount) -- keying it on this nonce re-applies the option
  // every time a fresh chart is created.
  const [initNonce, setInitNonce] = useState(0);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    let disposed = false;
    let observer: ResizeObserver | undefined;

    void import("echarts").then((echarts) => {
      if (disposed) return;
      const chart = echarts.init(el, undefined, { renderer: "canvas" });
      chartRef.current = chart;
      observer = new ResizeObserver(() => chart.resize());
      observer.observe(el);
      setInitNonce((n) => n + 1);
    });

    return () => {
      disposed = true;
      observer?.disconnect();
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
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

    chart.setOption(
      {
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
              _params: unknown,
              api: {
                value: (i: number) => number;
                coord: (p: [number, number]) => [number, number];
                style: () => object;
              },
            ) => {
              const x0 = api.value(0);
              const x1 = api.value(1);
              const y = api.value(2);
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
                style: api.style(),
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
      },
      { notMerge: true },
    );
    // If the chart initialised before layout settled (0-width), the option
    // above is drawn at the real size now.
    chart.resize();
  }, [bins, pdfLine, domain, lsl, usl, target, dark, initNonce]);

  return <div ref={containerRef} className="h-72 w-full" />;
}
