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
import { callApi } from "@/lib/call-api";
import { describeRuleSelection } from "@/lib/rules";
import { ControlChart } from "./control-chart";
import { ErrorAlert } from "./error-alert";

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
  // `status` is the rule run's own outcome, kept apart from the chart's. An
  // empty violation list means "the rules ran and found nothing" and nothing
  // else -- a failed or unfinished run must never be able to produce one.
  const [ruleState, setRuleState] = useState<{
    chart: ChartPair | null;
    rules: number[] | null;
    violations: RuleViolation[];
    status: "done" | "error";
    message: string;
  }>({
    chart: null,
    rules: null,
    violations: [],
    status: "done",
    message: "",
  });
  const [descriptions, setDescriptions] = useState<Record<string, string>>({});

  // The chart depends only on the data: changing which rules are applied must
  // not recompute the control limits (and must not make them look unstable).
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const outcome = await callApi(
        () => imrChart(column.values),
        "The control chart could not be computed.",
      );
      if (cancelled) return;
      if (!outcome.ok) {
        setState({ kind: "error", message: outcome.message });
        return;
      }
      setState({ kind: "done", chart: outcome.data });
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
      const outcome = await callApi(
        () => nelsonRules(loc.points, loc.limits, selected),
        "The run rules could not be computed.",
      );
      if (cancelled) return;
      if (!outcome.ok) {
        setRuleState({
          chart,
          rules: selected,
          violations: [],
          status: "error",
          message: outcome.message,
        });
        return;
      }
      setRuleState({
        chart,
        rules: selected,
        violations: outcome.data,
        status: "done",
        message: "",
      });
    })().catch(() => {
      // `callApi` is total -- it turns a rejection into an outcome -- so this
      // can only fire on a fault in the state update above. Saying "could not
      // reach the API" here would be false; what is true is that the rules
      // produced nothing to trust, which is the part the reader needs.
      if (!cancelled) {
        setRuleState({
          chart,
          rules: selected,
          violations: [],
          status: "error",
          message: "The run rules could not be applied.",
        });
      }
    });
    return () => {
      cancelled = true;
    };
  }, [chart, selected]);

  // Only trust a rule run that belongs to *this* chart and *this* rule
  // selection. Anything else is a run still in flight, and while one is in
  // flight the panel is not entitled to say anything about violations -- an
  // empty list here would read as "no violations" when it means "not yet".
  // Both comparisons are by reference, which is what the effect keys on too.
  const settled =
    ruleState.chart === chart && ruleState.rules === selected
      ? ruleState
      : null;
  const rules = settled?.status === "done" ? settled.violations : [];
  const ruleStatus = settled?.status ?? "running";
  const ruleMessage = settled?.message ?? "";

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
        <p className="text-sm text-muted">Computing control limits…</p>
      )}

      {state.kind === "error" && <ErrorAlert message={state.message} />}

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
                <li key={i} data-code={w.code}>
                  {w.message}
                </li>
              ))}
            </ul>
          )}

          <RuleSelector
            selected={selected}
            descriptions={descriptions}
            onChange={setSelected}
          />
          <RuleList
            rules={rules}
            selected={selected}
            status={ruleStatus}
            message={ruleMessage}
          />
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
          className="text-xs text-muted underline underline-offset-4 hover:text-foreground disabled:no-underline disabled:opacity-40"
        >
          Reset to 1–4
        </button>
        {selected.length === 0 && (
          <span className="text-xs text-muted">
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
  status,
  message,
}: {
  rules: RuleViolation[];
  selected: number[];
  status: "running" | "done" | "error";
  message: string;
}) {
  const applied = describeRuleSelection(selected);
  if (selected.length === 0) {
    return (
      <p className="text-sm text-muted">
        No run rules are applied. Only the 3-sigma limit violations on the
        charts above are flagged.
      </p>
    );
  }
  if (status === "error") {
    // "No violations" would be a statement about the process. Nothing was
    // measured, so there is nothing to state.
    return (
      <ErrorAlert
        message={`The run rules could not be applied, so this chart says nothing about rules ${applied}. ${message}`}
      />
    );
  }
  if (status === "running") {
    return (
      <p className="text-sm text-muted">
        Applying run rules (rules {applied})…
      </p>
    );
  }
  if (rules.length === 0) {
    return (
      <p className="text-sm text-muted">
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
