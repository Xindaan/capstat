"use client";

import {
  buildControlChartOption,
  describeLimits,
  type ControlChartProps,
} from "@/lib/control-chart-option";
import { useEchart, usePrefersDark } from "@/lib/echarts";

export type { ControlChartProps };

export function ControlChart(props: ControlChartProps) {
  const {
    title,
    points,
    center,
    lower,
    upper,
    violations,
    ruleFlags = [],
    zones = false,
  } = props;
  const dark = usePrefersDark();

  const ref = useEchart(
    () =>
      buildControlChartOption(
        { title, points, center, lower, upper, violations, ruleFlags, zones },
        dark,
      ),
    [title, points, center, lower, upper, violations, ruleFlags, zones, dark],
  );

  // The chart's own words, for a reader who cannot see it. Built from the same
  // props that are drawn, so the sentence cannot describe a different picture
  // than the one on screen (T-0060). `role="img"` stops a screen reader walking
  // into the SVG, which is a maze of coordinates and no information.
  const flagged = [...new Set([...violations, ...ruleFlags])].sort(
    (a, b) => a - b,
  );
  const limits = describeLimits(center, lower, upper);
  const label =
    `${title} chart, ${points.length} points, limits ${limits}, ` +
    (flagged.length === 0
      ? "in control"
      : `out of control at point${flagged.length > 1 ? "s" : ""} ` +
        flagged.map((i) => i + 1).join(", "));

  // The limits as plain text under the picture: the numbers a report quotes,
  // present on the page and in the printout (T-0098, WEB-9) and independent
  // of whether the line is drawn legibly.
  return (
    <>
      <div ref={ref} role="img" aria-label={label} className="h-64 w-full" />
      <p
        className="mt-2 text-xs tabular-nums text-foreground/70"
        data-testid="chart-limits"
      >
        {limits}
      </p>
    </>
  );
}
