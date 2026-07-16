"use client";

import { useState } from "react";

import { biasStudy, type BiasReport } from "@/lib/api-client";
import { describeApiError } from "@/lib/errors";
import { parseNumberList } from "@/lib/stats";

const EXAMPLE = "36.1, 35.9, 36.0, 36.05, 35.95, 36.2, 35.85, 36.0, 36.1, 35.9";

type Status =
  | { kind: "idle" }
  | { kind: "computing" }
  | { kind: "done"; result: BiasReport }
  | { kind: "error"; message: string };

function fmt(v: number | null | undefined, d = 4): string {
  return v == null || Number.isNaN(v) ? "—" : v.toFixed(d);
}

export function BiasPanel() {
  const [readings, setReadings] = useState(EXAMPLE);
  const [reference, setReference] = useState("36");
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  const values = parseNumberList(readings);
  const ref = reference.trim() === "" ? null : Number(reference);
  const refValid = ref != null && Number.isFinite(ref);
  const valid = values != null && values.length >= 2 && refValid;

  const compute = async () => {
    if (!valid) return;
    setStatus({ kind: "computing" });
    try {
      const { data, error } = await biasStudy(values, ref);
      if (error || !data) {
        setStatus({
          kind: "error",
          message: describeApiError(error, "Bias could not be computed."),
        });
        return;
      }
      setStatus({ kind: "done", result: data });
    } catch {
      setStatus({ kind: "error", message: "Could not reach the API." });
    }
  };

  const result = status.kind === "done" ? status.result : null;

  return (
    <section className="flex flex-col gap-4" aria-label="Bias study">
      <div>
        <h2 className="text-lg font-medium">Bias</h2>
        <p className="text-sm text-foreground/60">
          Measure one part whose true value you know, several times. Is the
          average significantly off it?
        </p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
        <label className="flex flex-1 flex-col gap-1">
          <span className="text-xs uppercase tracking-wide text-foreground/50">
            Readings
          </span>
          <textarea
            value={readings}
            onChange={(e) => setReadings(e.target.value)}
            rows={3}
            className="rounded-lg border border-foreground/20 bg-transparent p-3 font-mono text-sm tabular-nums focus:border-foreground/50 focus:outline-none"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs uppercase tracking-wide text-foreground/50">
            Reference
          </span>
          <input
            type="number"
            step="any"
            value={reference}
            onChange={(e) => setReference(e.target.value)}
            className="h-10 w-28 rounded-lg border border-foreground/20 bg-transparent px-3 text-sm tabular-nums focus:border-foreground/50 focus:outline-none"
          />
        </label>
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => void compute()}
          disabled={!valid || status.kind === "computing"}
          className="h-10 rounded-lg bg-foreground px-4 text-sm font-medium text-background transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {status.kind === "computing" ? "Computing…" : "Compute bias"}
        </button>
        {!valid && (
          <span className="text-xs text-amber-600 dark:text-amber-400">
            Need at least two numeric readings and a numeric reference.
          </span>
        )}
      </div>

      {status.kind === "error" && (
        <div
          role="alert"
          className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-700 dark:text-red-300"
        >
          {status.message}
        </div>
      )}

      {result && (
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Bias" value={fmt(result.bias)} big
              tone={
                result.bias_significant
                  ? "text-red-600 dark:text-red-400"
                  : "text-emerald-600 dark:text-emerald-400"
              } />
            <Stat label="Verdict"
              value={result.bias_significant ? "Biased" : "No bias"}
              tone={
                result.bias_significant
                  ? "text-red-600 dark:text-red-400"
                  : "text-emerald-600 dark:text-emerald-400"
              } />
            <Stat label="Repeatability" value={fmt(result.repeatability)} />
            <Stat label="p-value" value={fmt(result.p_value, 4)} />
          </div>
          <p className="text-xs text-foreground/50">
            95% interval for the bias: [{fmt(result.ci_lower)},{" "}
            {fmt(result.ci_upper)}] — {result.bias_significant
              ? "it excludes zero, so the bias is real."
              : "it straddles zero, so there is no evidence of bias."}
          </p>
          {result.warnings.length > 0 && (
            <ul className="list-disc space-y-1 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 pl-8 text-sm text-amber-800 dark:text-amber-200/90">
              {result.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

function Stat({
  label,
  value,
  tone,
  big = false,
}: {
  label: string;
  value: string;
  tone?: string;
  big?: boolean;
}) {
  return (
    <div className="rounded-lg border border-foreground/15 p-3">
      <div className="text-xs uppercase tracking-wide text-foreground/40">
        {label}
      </div>
      <div
        className={[
          "font-mono tabular-nums",
          big ? "text-xl" : "text-lg",
          tone ?? "text-foreground",
        ].join(" ")}
      >
        {value}
      </div>
    </div>
  );
}
