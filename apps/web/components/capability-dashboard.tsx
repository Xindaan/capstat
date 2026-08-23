"use client";

import { useMemo, useState } from "react";

import {
  analyzeCapability,
  type CapabilityAnalysis,
  type IngestColumn,
} from "@/lib/api-client";
import { callApi } from "@/lib/call-api";
import { CapabilityHistogram, type NormalFit } from "./capability-histogram";
import { ErrorAlert } from "./error-alert";

type Status =
  | { kind: "idle" }
  | { kind: "computing" }
  | { kind: "done"; result: CapabilityAnalysis }
  | { kind: "error"; message: string };

const PATH_LABEL: Record<CapabilityAnalysis["path"], string> = {
  normal: "Normal",
  "box-cox": "Box-Cox transform",
  percentile: "Percentile (non-normal)",
};

function fmt(value: number | null | undefined, digits = 3): string {
  return value == null || Number.isNaN(value) ? "—" : value.toFixed(digits);
}

/** Capability verdict colouring on the usual 1.00 / 1.33 thresholds. */
function indexTone(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "text-muted";
  if (value >= 1.33) return "text-emerald-600 dark:text-emerald-400";
  if (value >= 1.0) return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

export function CapabilityDashboard({ column }: { column: IngestColumn }) {
  const [lsl, setLsl] = useState("");
  const [usl, setUsl] = useState("");
  const [target, setTarget] = useState("");
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  const parsed = useMemo(() => {
    const num = (s: string) => (s.trim() === "" ? null : Number(s));
    const l = num(lsl);
    const u = num(usl);
    const t = num(target);
    const bad =
      [l, u, t].some((v) => v != null && Number.isNaN(v)) ||
      (l == null && u == null) ||
      (l != null && u != null && l >= u);
    return { l, u, t, valid: !bad };
  }, [lsl, usl, target]);

  const compute = async () => {
    if (!parsed.valid) return;
    setStatus({ kind: "computing" });
    const outcome = await callApi(
      () =>
        analyzeCapability(column.values, {
          lsl: parsed.l,
          usl: parsed.u,
          target: parsed.t,
        }),
      "Capability could not be computed.",
    );
    if (!outcome.ok) {
      setStatus({ kind: "error", message: outcome.message });
      return;
    }
    setStatus({ kind: "done", result: outcome.data });
  };

  const result = status.kind === "done" ? status.result : null;
  // The within-based report (Cp/Cpk) for the active path: the normal fit, or
  // the Box-Cox fit on the transformed scale. The percentile path has no
  // within/overall split, hence no Cp/Cpk.
  const report =
    result?.path === "normal"
      ? result.normal
      : result?.path === "box-cox"
        ? (result.box_cox?.capability ?? null)
        : null;
  // The percentile method reads percentiles off the overall fitted distribution
  // and has no within/between subgroup split, so Cp and Cpk do not exist there
  // at all -- as opposed to merely being undefined for a one-sided spec. Saying
  // which is which is the whole point: an empty card otherwise reads as "your
  // input was wrong".
  const withinUnavailable =
    result?.path === "percentile"
      ? "not defined on the percentile path"
      : undefined;
  // Only the normal path gets a fitted curve; a Box-Cox normal lives in the
  // transformed space and would be wrong drawn over the original-scale bars.
  const fit: NormalFit | null =
    result?.path === "normal" && result.normal
      ? { mean: result.normal.mean, sigma: result.normal.sigma_overall }
      : null;

  return (
    <section className="flex flex-col gap-5" aria-label="Capability analysis">
      <div className="flex flex-col gap-1">
        <h2 className="text-sm font-medium text-foreground/70">
          Process capability
        </h2>
        <p className="text-xs text-muted">
          Enter the specification limits for{" "}
          <span className="font-mono">{column.name}</span>. At least one of LSL
          or USL is required.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <SpecField label="LSL" value={lsl} onChange={setLsl} />
        <SpecField label="Target" value={target} onChange={setTarget} />
        <SpecField label="USL" value={usl} onChange={setUsl} />
        <button
          type="button"
          onClick={() => void compute()}
          disabled={!parsed.valid || status.kind === "computing"}
          className="h-10 rounded-lg bg-foreground px-4 text-sm font-medium text-background transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {status.kind === "computing" ? "Computing…" : "Compute capability"}
        </button>
      </div>
      {!parsed.valid && (lsl !== "" || usl !== "" || target !== "") && (
        <p className="text-xs text-amber-600 dark:text-amber-400">
          {parsed.l != null && parsed.u != null && parsed.l >= parsed.u
            ? "LSL must be less than USL."
            : "Enter a valid LSL or USL (numbers only)."}
        </p>
      )}

      {status.kind === "error" && <ErrorAlert message={status.message} />}

      {result && (
        <div className="flex flex-col gap-5">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <IndexCard
              label="Pp"
              value={result.pp}
              unavailable="needs both spec limits"
            />
            <IndexCard label="Ppk" value={result.ppk} emphasize />
            <IndexCard
              label="Cp"
              value={report?.cp}
              unavailable={withinUnavailable ?? "needs both spec limits"}
            />
            <IndexCard
              label="Cpk"
              value={report?.cpk}
              emphasize
              unavailable={withinUnavailable}
            />
          </div>

          <div className="rounded-lg border border-foreground/15 p-4">
            <div className="mb-2 flex items-center gap-2">
              <span className="rounded bg-foreground/10 px-2 py-0.5 text-xs font-medium">
                Path: {PATH_LABEL[result.path]}
              </span>
              <NormalityBadge normal={result.normality.normal} />
            </div>
            <p className="text-sm text-foreground/70">{result.rationale}</p>
            <p className="mt-2 text-xs text-muted">
              {result.normality.recommendation}
            </p>
          </div>

          {result.warnings.length > 0 && (
            <ul className="list-disc space-y-1 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 pl-8 text-sm text-amber-800 dark:text-amber-200/90">
              {result.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}

          <div className="rounded-lg border border-foreground/15 p-4">
            <p className="mb-2 text-xs text-muted">
              Histogram with specification limits
              {fit ? " and the fitted normal curve" : ""}.
            </p>
            <CapabilityHistogram
              values={column.values}
              lsl={parsed.l}
              usl={parsed.u}
              target={parsed.t}
              fit={fit}
            />
          </div>
        </div>
      )}
    </section>
  );
}

function SpecField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-muted">
        {label}
      </span>
      <input
        type="number"
        inputMode="decimal"
        step="any"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-10 w-28 rounded-lg border border-foreground/20 bg-transparent px-3 text-sm tabular-nums focus:border-foreground/50 focus:outline-none"
        placeholder="—"
      />
    </label>
  );
}

function IndexCard({
  label,
  value,
  emphasize = false,
  unavailable,
}: {
  label: string;
  value: number | null | undefined;
  emphasize?: boolean;
  /**
   * Why this index has no value, for the cases where it genuinely has none.
   * An index that does not exist and one whose data is missing look identical
   * as a bare dash — and a reader who typed the spec limits correctly should
   * not have to wonder which they are looking at.
   */
  unavailable?: string;
}) {
  const missing = value == null || Number.isNaN(value);
  return (
    <div className="rounded-lg border border-foreground/15 p-3">
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
      {missing && unavailable ? (
        <div className="text-xs leading-snug text-muted">{unavailable}</div>
      ) : (
        <div
          className={[
            "font-mono tabular-nums",
            emphasize ? "text-2xl" : "text-xl",
            indexTone(value),
          ].join(" ")}
        >
          {fmt(value)}
        </div>
      )}
    </div>
  );
}

function NormalityBadge({ normal }: { normal: boolean }) {
  return (
    <span
      className={[
        "rounded px-2 py-0.5 text-xs font-medium",
        normal
          ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
          : "bg-amber-500/15 text-amber-700 dark:text-amber-300",
      ].join(" ")}
    >
      {normal ? "Normal" : "Non-normal"}
    </span>
  );
}
