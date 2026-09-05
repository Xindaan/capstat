"use client";

import { useEffect, useState } from "react";

import { linearityStudy, type LinearityReport } from "@/lib/api-client";
import { parseNumberList } from "@/lib/stats";
import { ErrorAlert } from "./error-alert";
import { callApi } from "@/lib/call-api";

export interface Row {
  reference: string;
  readings: string;
}

// The AIAG linearity example: each part's readings average to the published
// bias (+0.49 at the low end down to -0.61 at the high end), so this computes
// the documented slope of -0.132 on first load.
const EXAMPLE: Row[] = [
  { reference: "7", readings: "7.39, 7.44, 7.54, 7.59" },
  { reference: "9", readings: "9.06, 9.11, 9.21, 9.26" },
  { reference: "11", readings: "10.92, 10.97, 11.07, 11.12" },
  { reference: "13", readings: "12.62, 12.67, 12.77, 12.82" },
  { reference: "15", readings: "14.29, 14.34, 14.44, 14.49" },
];

type Status =
  | { kind: "idle" }
  | { kind: "computing" }
  | { kind: "done"; result: LinearityReport }
  | { kind: "error"; message: string };

function fmt(v: number | null | undefined, d = 4): string {
  return v == null || Number.isNaN(v) ? "—" : v.toFixed(d);
}

export interface LinearityInputs {
  rows: Row[];
  processVariation: string;
}

export const EXAMPLE_LINEARITY_INPUTS: LinearityInputs = {
  rows: EXAMPLE,
  processVariation: "",
};

export function LinearityPanel({
  initial = EXAMPLE_LINEARITY_INPUTS,
  onInputsChange,
}: {
  initial?: LinearityInputs;
  onInputsChange?: (inputs: LinearityInputs) => void;
} = {}) {
  const [rows, setRows] = useState<Row[]>(initial.rows);
  const [processVariation, setProcessVariation] = useState(
    initial.processVariation,
  );
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  useEffect(() => {
    onInputsChange?.({ rows, processVariation });
  }, [rows, processVariation, onInputsChange]);

  const setRow = (i: number, patch: Partial<Row>) =>
    setRows((rs) => rs.map((r, j) => (j === i ? { ...r, ...patch } : r)));

  const parsed = (() => {
    if (rows.length < 2) return null;
    const references: number[] = [];
    const measurements: number[][] = [];
    for (const row of rows) {
      const ref = Number(row.reference);
      const vals = parseNumberList(row.readings);
      if (row.reference.trim() === "" || !Number.isFinite(ref)) return null;
      if (vals == null) return null;
      references.push(ref);
      measurements.push(vals);
    }
    return { references, measurements };
  })();

  const pv = processVariation.trim() === "" ? null : Number(processVariation);
  const pvInvalid = pv != null && !Number.isFinite(pv);
  const valid = parsed != null && !pvInvalid;

  const compute = async () => {
    if (!parsed || pvInvalid) return;
    setStatus({ kind: "computing" });
    const outcome = await callApi(
      () => linearityStudy(parsed.references, parsed.measurements, pv),
      "Linearity could not be computed.",
    );
    if (!outcome.ok) {
      setStatus({ kind: "error", message: outcome.message });
      return;
    }
    setStatus({ kind: "done", result: outcome.data });
  };

  const result = status.kind === "done" ? status.result : null;

  return (
    <section className="flex flex-col gap-4" aria-label="Linearity study">
      <div>
        <h2 className="text-lg font-medium">Linearity</h2>
        <p className="text-sm text-foreground/60">
          Several masters across the range. Does the bias stay put, or drift as
          the value grows?
        </p>
      </div>

      <div className="flex flex-col gap-2">
        {rows.map((row, i) => (
          <div key={i} className="flex items-center gap-2">
            <input
              type="number"
              step="any"
              value={row.reference}
              onChange={(e) => setRow(i, { reference: e.target.value })}
              aria-label={`Reference for part ${i + 1}`}
              placeholder="ref"
              className="h-9 w-20 rounded-lg border border-foreground/20 bg-transparent px-2 text-sm tabular-nums focus:border-foreground/50 focus:outline-none"
            />
            <input
              value={row.readings}
              onChange={(e) => setRow(i, { readings: e.target.value })}
              aria-label={`Readings for part ${i + 1}`}
              placeholder="readings, comma separated"
              className="h-9 flex-1 rounded-lg border border-foreground/20 bg-transparent px-3 font-mono text-sm tabular-nums focus:border-foreground/50 focus:outline-none"
            />
            <button
              type="button"
              onClick={() => setRows((rs) => rs.filter((_, j) => j !== i))}
              disabled={rows.length <= 2}
              aria-label={`Remove part ${i + 1}`}
              className="h-9 w-9 shrink-0 rounded-lg border border-foreground/15 text-muted hover:text-foreground disabled:opacity-30"
            >
              ×
            </button>
          </div>
        ))}
        <div className="flex flex-wrap items-end gap-3">
          <button
            type="button"
            onClick={() =>
              setRows((rs) => [...rs, { reference: "", readings: "" }])
            }
            className="h-9 rounded-lg border border-foreground/20 px-3 text-sm text-foreground/70 hover:text-foreground"
          >
            + Add part
          </button>
          <label className="flex flex-col gap-1">
            <span className="text-xs uppercase tracking-wide text-muted">
              Process variation
            </span>
            <input
              type="number"
              step="any"
              value={processVariation}
              onChange={(e) => setProcessVariation(e.target.value)}
              placeholder="optional"
              className="h-9 w-32 rounded-lg border border-foreground/20 bg-transparent px-3 text-sm tabular-nums focus:border-foreground/50 focus:outline-none"
            />
          </label>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => void compute()}
          disabled={!valid || status.kind === "computing"}
          className="h-10 rounded-lg bg-foreground px-4 text-sm font-medium text-background transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {status.kind === "computing" ? "Computing…" : "Compute linearity"}
        </button>
        {!valid && (
          <span className="text-xs text-amber-600 dark:text-amber-400">
            Every part needs a numeric reference and numeric readings.
          </span>
        )}
      </div>

      {status.kind === "error" && <ErrorAlert message={status.message} />}

      {result && (
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat
              label="Slope"
              value={fmt(result.slope)}
              tone={
                result.linearity_significant
                  ? "text-red-600 dark:text-red-400"
                  : "text-emerald-600 dark:text-emerald-400"
              }
            />
            <Stat
              label="% Linearity"
              value={fmt(result.percent_linearity, 2)}
            />
            <Stat label="Intercept" value={fmt(result.intercept)} />
            <Stat label="R²" value={fmt(result.r_squared, 4)} />
          </div>
          <div className="overflow-x-auto rounded-lg border border-foreground/15">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-foreground/15 text-muted">
                  <th className="p-2 text-left font-medium">Reference</th>
                  <th className="p-2 text-right font-medium">Mean bias</th>
                </tr>
              </thead>
              <tbody className="tabular-nums">
                {result.references.map((ref, i) => (
                  <tr key={i} className="border-t border-foreground/10">
                    <td className="p-2 font-mono">{fmt(ref, 2)}</td>
                    <td className="p-2 text-right font-mono">
                      {fmt(result.part_mean_biases[i], 3)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {result.linearity !== null && (
            <p className="text-xs text-muted">
              Absolute linearity (|slope| × process variation):{" "}
              {fmt(result.linearity)}
            </p>
          )}
          {result.warnings.length > 0 && (
            <ul className="list-disc space-y-1 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 pl-8 text-sm text-amber-800 dark:text-amber-200/90">
              {result.warnings.map((w, i) => (
                <li key={i} data-code={w.code}>
                  {w.message}
                </li>
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
}: {
  label: string;
  value: string;
  tone?: string;
}) {
  return (
    <div className="rounded-lg border border-foreground/15 p-3">
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
      <div
        className={[
          "font-mono text-lg tabular-nums",
          tone ?? "text-foreground",
        ].join(" ")}
      >
        {value}
      </div>
    </div>
  );
}
