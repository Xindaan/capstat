import {
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type DependencyList,
} from "react";
import type { ECharts, EChartsOption } from "echarts";

const DARK_QUERY = "(prefers-color-scheme: dark)";

/** Track the colour scheme without a setState-in-effect (React's blessed way). */
export function usePrefersDark(): boolean {
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

/**
 * Own an ECharts instance for the returned container ref and keep its option in
 * sync with `deps`. echarts is imported lazily (client-only, code-split), which
 * makes the ordering subtle: the option must be (re-)applied *after* the async
 * init resolves and after every StrictMode remount, or the canvas stays blank.
 * The init nonce below guarantees exactly that -- callers just pass a builder
 * and its dependency list.
 */
export function useEchart(
  buildOption: () => EChartsOption,
  deps: DependencyList,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ECharts | null>(null);
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
    chart.setOption(buildOption(), { notMerge: true });
    // If init raced ahead of layout (0-width), this draws at the real size now.
    chart.resize();
    // buildOption is intentionally excluded; `deps` is the caller's contract for
    // what the option depends on (a fresh closure every render would thrash).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initNonce, ...deps]);

  return containerRef;
}
