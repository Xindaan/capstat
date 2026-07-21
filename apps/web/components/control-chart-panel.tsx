"use client";

import { useEffect, useMemo, useState } from "react";

import {
  imrChart,
  nelsonRules,
  rulesCatalogue,
  type ChartPair,
  type IngestColumn,
  type RuleViolation,
} from "@/lib/api-client";
import { describeApiError } from "@/lib/errors";
import { describeRuleSelection } from "@/lib/rules";
import { ControlChart } from "./control-chart";

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "done"; chart: ChartPair };

/**
 * Rules 1-4 by default: beyond 3 sigma, 9 on one side, 6 trending, 14
 * alternating. Nelson's own advice is against running all eight at once, and
 * T-0009 measured what that costs -- the full set signals roughly eight times
 * as often on in-control data as rule 1 alone. The others are one click away,
 * which is the point of this control, but they are not the default.
 */
const DEFAULT_RULES = [1, 2, 3, 4];
const ALL_RULES = [1, 2, 3, 4, 5, 6, 7, 8];

export function ControlChartPanel({ column }: { column: IngestColumn }) {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [selected, setSelected] = useState<number[]>(DEFAULT_RULES);
  // Violations are stored with the chart they were computed from. Without that
  // tie, switching column would briefly paint the previous column's flags onto
  // the new chart -- points marked out of control that are not.
  const [ruleState, setRuleState] = useState<{
    chart: ChartPair | null;
    violations: RuleViolation[];
  }>({ chart: null, violations: [] });
  const [descriptions, setDescriptions] = useState<Record<string, string>>({});

  // The chart depends only on the data: changing which rules are applied must
  // not recompute the control limits (and must not make them look unstable).
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data, error } = await imrChart(column.values);
        if (cancelled) return;
        if (error || !data) {
          setState({
            kind: "error",
            message: describeApiError(
              error,
              "The control chart could not be computed.",
            ),
          });
          return;
        }
        setState({ kind: "done", chart: data });
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

  // Run-rules read their sigma zones from the individuals chart's own limits,
  // so this waits for the chart and re-runs whenever the selection changes.
  const chart = state.kind === "done" ? state.chart : null;
  useEffect(() => {
    if (!chart) return; // nothing to run rules against yet
    let cancelled = false;
    (async () => {
      const loc = chart.location;
      const res = await nelsonRules(loc.points, loc.limits, selected);
      if (!cancelled) setRuleState({ chart, violations: res.data ?? [] });
    })().catch(() => {
      if (!cancelled) setRuleState({ chart, violations: [] });
    });
    return () => {
      cancelled = true;
    };
  }, [chart, selected]);

  // Only trust violations that belong to the chart on screen.
  const rules = ruleState.chart === chart ? ruleState.violations : [];

  useEffect(() => {
    let cancelled = false;
    rulesCatalogue()
      .then((res) => {
        if (!cancelled && res.data) setDescriptions(res.data.nelson ?? {});
      })
      .catch(() => {
        // Labels fall back to the rule number; not worth an error banner.
      });
    return () => {
      cancelled = true;
    };
  }, []);

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
              ruleFlags={[...new Set(rules.map((r) => r.point))]}
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

          <RuleSelector
            selected={selected}
            descriptions={descriptions}
            onChange={setSelected}
          />
          <RuleList rules={rules} selected={selected} />
        </div>
      )}
    </section>
  );
}

function RuleSelector({
  selected,
  descriptions,
  onChange,
}: {
  selected: number[];
  descriptions: Record<string, string>;
  onChange: (rules: number[]) => void;
}) {
  const isDefault = useMemo(
    () =>
      selected.length === DEFAULT_RULES.length &&
      DEFAULT_RULES.every((r) => selected.includes(r)),
    [selected],
  );

  const toggle = (rule: number) =>
    onChange(
      selected.includes(rule)
        ? selected.filter((r) => r !== rule)
        : [...selected, rule].sort((a, b) => a - b),
    );

  return (
    // no-print: which rules were applied belongs in the report (RuleList says
    // so); the checkboxes to change them do not.
    <fieldset className="no-print flex flex-col gap-2 rounded-lg border border-foreground/15 p-4">
      <legend className="px-1 text-xs font-medium text-foreground/60">
        Nelson rules to apply
      </legend>
      <div className="grid gap-1.5 sm:grid-cols-2">
        {ALL_RULES.map((rule) => (
          <label
            key={rule}
            className="flex cursor-pointer items-start gap-2 text-xs text-foreground/70"
          >
            <input
              type="checkbox"
              className="mt-0.5 accent-blue-500"
              checked={selected.includes(rule)}
              onChange={() => toggle(rule)}
            />
            <span>
              <span className="font-medium">Rule {rule}</span>
              {descriptions[rule] ? ` — ${descriptions[rule]}` : ""}
            </span>
          </label>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-3 pt-1">
        <button
          type="button"
          onClick={() => onChange(DEFAULT_RULES)}
          disabled={isDefault}
          className="text-xs text-foreground/50 underline underline-offset-4 hover:text-foreground disabled:no-underline disabled:opacity-40"
        >
          Reset to 1–4
        </button>
        {selected.length === 0 && (
          <span className="text-xs text-foreground/50">
            No rules selected — only the 3-sigma limit violations above are
            flagged.
          </span>
        )}
        {selected.length > DEFAULT_RULES.length && (
          <span className="text-xs text-amber-600 dark:text-amber-400">
            More rules means more false alarms: on in-control data the full set
            of eight signals roughly eight times as often as rule 1 alone.
          </span>
        )}
      </div>
    </fieldset>
  );
}

function RuleList({
  rules,
  selected,
}: {
  rules: RuleViolation[];
  selected: number[];
}) {
  const applied = describeRuleSelection(selected);
  if (selected.length === 0) {
    return (
      <p className="text-sm text-foreground/50">
        No run rules are applied. Only the 3-sigma limit violations on the
        charts above are flagged.
      </p>
    );
  }
  if (rules.length === 0) {
    return (
      <p className="text-sm text-foreground/50">
        No Nelson run-rule violations (rules {applied}) on the individuals
        chart.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-1">
      <p className="text-xs font-medium text-foreground/60">
        Nelson run-rule violations (rules {applied})
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
