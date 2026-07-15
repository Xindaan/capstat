"use client";

import { useEffect, useState } from "react";

import {
  imrChart,
  nelsonRules,
  type ChartPair,
  type IngestColumn,
  type RuleViolation,
} from "@/lib/api-client";
import { ControlChart } from "./control-chart";

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "done"; chart: ChartPair; rules: RuleViolation[] };

function describeError(error: unknown): string {
  if (error && typeof error === "object" && "detail" in error) {
    const detail = (error as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const first = detail[0] as { msg?: string } | undefined;
      if (first?.msg) return first.msg;
    }
  }
  return "The control chart could not be computed.";
}

export function ControlChartPanel({ column }: { column: IngestColumn }) {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data, error } = await imrChart(column.values);
        if (cancelled) return;
        if (error || !data) {
          setState({ kind: "error", message: describeError(error) });
          return;
        }
        // Run-rules read their sigma zones from the individuals chart's limits.
        // Nelson's own advice is against enabling all eight at once, so this
        // defaults to the strongest four (beyond 3 sigma; 9 one side; 6
        // trending; 14 alternating) rather than the full, noisier set.
        const loc = data.location;
        const rulesRes = await nelsonRules(loc.points, loc.limits, [1, 2, 3, 4]);
        if (cancelled) return;
        setState({ kind: "done", chart: data, rules: rulesRes.data ?? [] });
      } catch {
        if (!cancelled) {
          setState({ kind: "error", message: "Could not reach the API." });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [column.values]);

  return (
    <section className="flex flex-col gap-4" aria-label="Control chart">
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-medium text-foreground/70">
          Control chart (I-MR)
        </h2>
        {state.kind === "done" && (
          <span
            className={[
              "rounded px-2 py-0.5 text-xs font-medium",
              state.chart.in_control
                ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
                : "bg-red-500/15 text-red-700 dark:text-red-300",
            ].join(" ")}
          >
            {state.chart.in_control ? "In control" : "Out of control"}
          </span>
        )}
      </div>

      {state.kind === "loading" && (
        <p className="text-sm text-foreground/50">Computing control limits…</p>
      )}

      {state.kind === "error" && (
        <div
          role="alert"
          className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-700 dark:text-red-300"
        >
          {state.message}
        </div>
      )}

      {state.kind === "done" && (
        <div className="flex flex-col gap-4">
          <div className="rounded-lg border border-foreground/15 p-4">
            <ControlChart
              title="Individuals"
              points={state.chart.location.points}
              center={state.chart.location.limits.center}
              lower={state.chart.location.limits.lower}
              upper={state.chart.location.limits.upper}
              violations={state.chart.location.violations}
              ruleFlags={[...new Set(state.rules.map((r) => r.point))]}
              zones
            />
          </div>
          <div className="rounded-lg border border-foreground/15 p-4">
            <ControlChart
              title="Moving range"
              points={state.chart.dispersion.points}
              center={state.chart.dispersion.limits.center}
              lower={state.chart.dispersion.limits.lower}
              upper={state.chart.dispersion.limits.upper}
              violations={state.chart.dispersion.violations}
            />
          </div>

          {state.chart.warnings.length > 0 && (
            <ul className="list-disc space-y-1 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 pl-8 text-sm text-amber-800 dark:text-amber-200/90">
              {state.chart.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}

          <RuleList rules={state.rules} />
        </div>
      )}
    </section>
  );
}

function RuleList({ rules }: { rules: RuleViolation[] }) {
  if (rules.length === 0) {
    return (
      <p className="text-sm text-foreground/50">
        No Nelson run-rule violations (rules 1–4) on the individuals chart.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-1">
      <p className="text-xs font-medium text-foreground/60">
        Nelson run-rule violations (rules 1–4)
      </p>
      <ul className="flex flex-col gap-1 text-sm text-foreground/70">
        {rules.map((r, i) => (
          <li key={i} className="flex gap-2">
            <span className="shrink-0 rounded bg-amber-500/15 px-1.5 py-0.5 text-xs text-amber-700 dark:text-amber-300">
              Rule {r.rule} @ point {r.point + 1}
            </span>
            <span>{r.description}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
