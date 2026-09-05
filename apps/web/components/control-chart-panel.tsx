"use client";

import { useEffect, useMemo, useState } from "react";

import {
  imrChart,
  nelsonRules,
  xbarRChart,
  xbarSChart,
  type Baseline,
  rulesCatalogue,
  type ChartPair,
  type IngestColumn,
  type RuleViolation,
} from "@/lib/api-client";
import { callApi } from "@/lib/call-api";
import { describeRuleSelection } from "@/lib/rules";
import { chartForSize, intoSubgroups } from "@/lib/subgroups";
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

/**
 * A baseline, or null when it is not complete.
 *
 * Null for half a baseline as much as for none: the panel must not send a
 * known centre with an estimated sigma, and falling back to "just the centre"
 * would be exactly that.
 */
function readBaseline(center: string, sigma: string): Baseline | null {
  if (center.trim() === "" || sigma.trim() === "") return null;
  const c = Number(center);
  const s = Number(sigma);
  if (!Number.isFinite(c) || !Number.isFinite(s) || s <= 0) return null;
  return { center: c, sigma: s };
}

/** "individuals" -> "Individuals"; "X-bar" is already how the core writes it. */
function titleCase(name: string): string {
  return name.charAt(0).toUpperCase() + name.slice(1);
}

/**
 * The pair's name, derived from the charts themselves rather than restated.
 *
 * "I-MR" is what everyone calls the individuals pair, so it keeps that name;
 * the subgroup pairs are named by their two charts. Either way the label comes
 * from what was actually computed, so it cannot announce a chart the panel is
 * not showing.
 */
function chartPairName(chart: ChartPair): string {
  return chart.location.name === "individuals"
    ? "I-MR"
    : `${chart.location.name} / ${chart.dispersion.name}`;
}
const ALL_RULES = [1, 2, 3, 4, 5, 6, 7, 8];

export function ControlChartPanel({
  column,
  subgroupSize,
}: {
  column: IngestColumn;
  /** 1 = an I-MR chart; anything more charts subgroup averages. */
  subgroupSize: number;
}) {
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
  // A known in-control centre and sigma turn this into a Phase II chart. Both
  // or neither: half a baseline is neither phase, so the panel only sends one
  // when both fields parse (T-0076).
  const [centerText, setCenterText] = useState("");
  const [sigmaText, setSigmaText] = useState("");
  // Memoised so its identity is stable while the fields are: the chart
  // effect keys on it, and a fresh object each render would refetch forever.
  const baseline = useMemo(
    () => readBaseline(centerText, sigmaText),
    [centerText, sigmaText],
  );
  const halfGiven =
    baseline == null && (centerText.trim() !== "" || sigmaText.trim() !== "");

  // The chart depends only on the data: changing which rules are applied must
  // not recompute the control limits (and must not make them look unstable).
  useEffect(() => {
    let cancelled = false;
    (async () => {
      // Which pair of charts suits the data is a consequence of the subgroup
      // size, not a separate choice: the range discards all but two values per
      // subgroup, so above 10 the s chart is the better estimator. The panel
      // picks and then says which it picked, rather than making the user know.
      const request = () => {
        if (subgroupSize <= 1) return imrChart(column.values, baseline);
        const { subgroups } = intoSubgroups(column.values, subgroupSize);
        return chartForSize(subgroupSize) === "xbar-r"
          ? xbarRChart(subgroups, baseline)
          : xbarSChart(subgroups, baseline);
      };
      const outcome = await callApi(
        request,
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
  }, [column.values, subgroupSize, baseline]);

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
          Control chart (
          {state.kind === "done" ? chartPairName(state.chart) : "…"})
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
        {state.kind === "done" && (
          <span className="rounded bg-foreground/10 px-2 py-0.5 text-xs font-medium">
            Phase {state.chart.phase}
          </span>
        )}
      </div>

      <BaselineFields
        center={centerText}
        sigma={sigmaText}
        onCenter={setCenterText}
        onSigma={setSigmaText}
        active={baseline != null}
        halfGiven={halfGiven}
      />

      {state.kind === "loading" && (
        <p className="text-sm text-muted">Computing control limits…</p>
      )}

      {state.kind === "error" && <ErrorAlert message={state.message} />}

      {state.kind === "done" && (
        <div className="flex flex-col gap-4">
          <div className="rounded-lg border border-foreground/15 p-4">
            <ControlChart
              title={titleCase(state.chart.location.name)}
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
              title={titleCase(state.chart.dispersion.name)}
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

function BaselineFields({
  center,
  sigma,
  onCenter,
  onSigma,
  active,
  halfGiven,
}: {
  center: string;
  sigma: string;
  onCenter: (v: string) => void;
  onSigma: (v: string) => void;
  active: boolean;
  halfGiven: boolean;
}) {
  return (
    <fieldset className="flex flex-col gap-2 rounded-lg border border-foreground/15 p-4">
      <legend className="px-1 text-xs font-medium text-foreground/60">
        Known limits from a stable period (optional)
      </legend>
      <div className="no-print flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs uppercase tracking-wide text-muted">
            Centre
          </span>
          <input
            type="number"
            step="any"
            value={center}
            onChange={(e) => onCenter(e.target.value)}
            aria-label="Known centre"
            placeholder="estimated"
            className="h-9 w-28 rounded-lg border border-foreground/20 bg-transparent px-3 text-sm tabular-nums focus:border-foreground/50 focus:outline-none"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs uppercase tracking-wide text-muted">
            Sigma (within)
          </span>
          <input
            type="number"
            step="any"
            value={sigma}
            onChange={(e) => onSigma(e.target.value)}
            aria-label="Known sigma"
            placeholder="estimated"
            className="h-9 w-28 rounded-lg border border-foreground/20 bg-transparent px-3 text-sm tabular-nums focus:border-foreground/50 focus:outline-none"
          />
        </label>
      </div>
      <p className="max-w-2xl text-xs text-muted">
        {active
          ? "Phase II: the limits come from these numbers, not from the data plotted, so a large excursion cannot move the limits meant to catch it — nor drag the centre line towards itself and condemn the points that were fine."
          : "Leave both empty for Phase I: the limits are estimated from the data being plotted, which is what you do when establishing a chart. Fill both in once the process is known to be stable, and this chart judges new data against that history instead."}
      </p>
      {halfGiven && (
        <p className="text-xs text-amber-600 dark:text-amber-400">
          A baseline needs both a centre and a positive sigma from the same
          period. One without the other mixes a known parameter with one
          estimated from the data under test, which is neither phase — so this
          chart is still Phase I.
        </p>
      )}
    </fieldset>
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
