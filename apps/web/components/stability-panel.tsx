"use client";

import { useEffect, useState } from "react";

import { stabilityStudy, type StabilityReport } from "@/lib/api-client";
import { parseNumberList } from "@/lib/stats";
import { ControlChart } from "./control-chart";
import { ErrorAlert } from "./error-alert";
import { callApi } from "@/lib/call-api";

// A master measured over time, with one late excursion — the gage drifting,
// not the part.
const EXAMPLE = [
  "10.02, 9.98, 10.01, 9.99, 10.03, 9.97, 10.00, 10.02,",
  "9.98, 10.01, 10.00, 9.99, 10.02, 9.98, 10.01, 10.00,",
  "9.99, 10.03, 10.28, 10.31",
].join(" ");

type Status =
  | { kind: "idle" }
  | { kind: "computing" }
  | { kind: "done"; result: StabilityReport }
  | { kind: "error"; message: string };

export interface StabilityInputs {
  readings: string;
}

export const EXAMPLE_STABILITY_INPUTS: StabilityInputs = {
  readings: EXAMPLE,
};

export function StabilityPanel({
  initial = EXAMPLE_STABILITY_INPUTS,
  onInputsChange,
}: {
  initial?: StabilityInputs;
  onInputsChange?: (inputs: StabilityInputs) => void;
} = {}) {
  const [readings, setReadings] = useState(initial.readings);

  useEffect(() => {
    onInputsChange?.({ readings });
  }, [readings, onInputsChange]);
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  const values = parseNumberList(readings);
  const valid = values != null && values.length >= 2;

  const compute = async () => {
    if (!valid) return;
    setStatus({ kind: "computing" });
    const outcome = await callApi(
      () => stabilityStudy(values),
      "Stability could not be computed.",
    );
    if (!outcome.ok) {
      setStatus({ kind: "error", message: outcome.message });
      return;
    }
    setStatus({ kind: "done", result: outcome.data });
  };

  const result = status.kind === "done" ? status.result : null;

  return (
    <section className="flex flex-col gap-4" aria-label="Stability study">
      <div>
        <h2 className="text-lg font-medium">Stability</h2>
        <p className="text-sm text-foreground/60">
          The same master, measured over time. A point outside the limits is the
          gage drifting — the part&apos;s true value never moved.
        </p>
      </div>

      <label className="flex flex-col gap-1">
        <span className="text-xs uppercase tracking-wide text-muted">
          Readings, in time order
        </span>
        <textarea
          value={readings}
          onChange={(e) => setReadings(e.target.value)}
          rows={3}
          className="rounded-lg border border-foreground/20 bg-transparent p-3 font-mono text-sm tabular-nums focus:border-foreground/50 focus:outline-none"
        />
      </label>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => void compute()}
          disabled={!valid || status.kind === "computing"}
          className="h-10 rounded-lg bg-foreground px-4 text-sm font-medium text-background transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {status.kind === "computing" ? "Computing…" : "Check stability"}
        </button>
        {result && (
          <span
            className={[
              "rounded px-2 py-0.5 text-xs font-medium",
              result.stable
                ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
                : "bg-red-500/15 text-red-700 dark:text-red-300",
            ].join(" ")}
          >
            {result.stable ? "Stable" : "Not stable"}
          </span>
        )}
        {!valid && (
          <span className="text-xs text-amber-600 dark:text-amber-400">
            Need at least two numeric readings.
          </span>
        )}
      </div>

      {status.kind === "error" && <ErrorAlert message={status.message} />}

      {result && (
        <div className="flex flex-col gap-3">
          <div className="rounded-lg border border-foreground/15 p-4">
            <ControlChart
              title="Master readings (individuals)"
              points={result.chart.location.points}
              center={result.chart.location.limits.center}
              lower={result.chart.location.limits.lower}
              upper={result.chart.location.limits.upper}
              violations={result.chart.location.violations}
              zones
            />
          </div>
          <div className="rounded-lg border border-foreground/15 p-4">
            <ControlChart
              title="Moving range"
              points={result.chart.dispersion.points}
              center={result.chart.dispersion.limits.center}
              lower={result.chart.dispersion.limits.lower}
              upper={result.chart.dispersion.limits.upper}
              violations={result.chart.dispersion.violations}
            />
          </div>
          {(result.warnings.length > 0 || result.chart.warnings.length > 0) && (
            <ul className="list-disc space-y-1 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 pl-8 text-sm text-amber-800 dark:text-amber-200/90">
              {[...result.warnings, ...result.chart.warnings].map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}
