"use client";

import { useMemo, useState } from "react";

import {
  analyzeCapability,
  capabilityFromSubgroups,
  type CapabilityAnalysis,
  type CapabilityReport,
  type IngestColumn,
} from "@/lib/api-client";
import { callApi } from "@/lib/call-api";
import {
  DEFAULT_REQUIRED_INDEX,
  capabilityBand,
  parseRequiredIndex,
  type CapabilityBand,
} from "@/lib/capability";
import { intoSubgroups } from "@/lib/subgroups";
import { CapabilityHistogram, type NormalFit } from "./capability-histogram";
import { ErrorAlert } from "./error-alert";

/**
 * The two shapes a capability answer comes in.
 *
 * Individuals go through `analyze_capability`, which chooses normal / Box-Cox /
 * percentile and says why. Subgroups go through `capability`, which has no
 * decision path -- Box-Cox and the percentile fit both work on a flat sample --
 * but does give a genuine within-subgroup sigma, which is the reason to
 * subgroup at all (T-0075).
 */
type Answer =
  | { kind: "analysis"; analysis: CapabilityAnalysis }
  | { kind: "report"; report: CapabilityReport };

type Status =
  | { kind: "idle" }
  | { kind: "computing" }
  | { kind: "done"; answer: Answer }
  | { kind: "error"; message: string };

const PATH_LABEL: Record<CapabilityAnalysis["path"], string> = {
  normal: "Normal",
  "box-cox": "Box-Cox transform",
  percentile: "Percentile (non-normal)",
};

function fmt(value: number | null | undefined, digits = 3): string {
  return value == null || Number.isNaN(value) ? "—" : value.toFixed(digits);
}

/** Colour per band. The bands themselves live in lib/capability (T-0073). */
const BAND_TONE: Record<CapabilityBand, string> = {
  meets: "text-emerald-600 dark:text-emerald-400",
  capable: "text-amber-600 dark:text-amber-400",
  incapable: "text-red-600 dark:text-red-400",
  unjudged: "text-muted",
};

export function CapabilityDashboard({
  column,
  subgroupSize,
}: {
  column: IngestColumn;
  /** 1 = individuals; anything more groups consecutive rows. */
  subgroupSize: number;
}) {
  const [lsl, setLsl] = useState("");
  const [usl, setUsl] = useState("");
  const [target, setTarget] = useState("");
  const [required, setRequired] = useState(DEFAULT_REQUIRED_INDEX);
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  // Colouring only -- it never reaches the API, so changing it re-judges the
  // indices on screen without recomputing them.
  const requiredIndex = parseRequiredIndex(required);

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
    const limits = { lsl: parsed.l, usl: parsed.u, target: parsed.t };
    if (subgroupSize > 1) {
      const { subgroups } = intoSubgroups(column.values, subgroupSize);
      const outcome = await callApi(
        () => capabilityFromSubgroups(subgroups, limits),
        "Capability could not be computed.",
      );
      if (!outcome.ok) {
        setStatus({ kind: "error", message: outcome.message });
        return;
      }
      setStatus({
        kind: "done",
        answer: { kind: "report", report: outcome.data },
      });
      return;
    }
    const outcome = await callApi(
      () => analyzeCapability(column.values, limits),
      "Capability could not be computed.",
    );
    if (!outcome.ok) {
      setStatus({ kind: "error", message: outcome.message });
      return;
    }
    setStatus({
      kind: "done",
      answer: { kind: "analysis", analysis: outcome.data },
    });
  };

  const answer = status.kind === "done" ? status.answer : null;
  const analysis = answer?.kind === "analysis" ? answer.analysis : null;
  // The within-based report (Cp/Cpk). On the individuals path that is whichever
  // branch the decision path took -- the normal fit, or the Box-Cox fit on the
  // transformed scale. With subgroups it is the report itself.
  const within =
    answer?.kind === "report"
      ? answer.report
      : analysis?.path === "normal"
        ? analysis.normal
        : analysis?.path === "box-cox"
          ? (analysis.box_cox?.capability ?? null)
          : null;
  // The percentile method reads percentiles off the overall fitted distribution
  // and has no within/between subgroup split, so Cp and Cpk do not exist there
  // at all -- as opposed to merely being undefined for a one-sided spec. Saying
  // which is which is the whole point: an empty card otherwise reads as "your
  // input was wrong".
  const withinUnavailable =
    analysis?.path === "percentile"
      ? "not defined on the percentile path"
      : undefined;
  const headline =
    answer?.kind === "report"
      ? { pp: answer.report.pp, ppk: answer.report.ppk }
      : { pp: analysis?.pp ?? null, ppk: analysis?.ppk ?? null };
  const warnings =
    answer?.kind === "report"
      ? answer.report.warnings
      : (analysis?.warnings ?? []);
  const normality =
    answer?.kind === "report"
      ? answer.report.normality
      : (analysis?.normality ?? null);
  // A fitted curve is drawn only where it belongs on the original scale: the
  // normal path, or a subgroup report whose normal model was not rejected. A
  // Box-Cox normal lives in the transformed space and would be wrong here.
  const fit: NormalFit | null =
    answer?.kind === "report"
      ? answer.report.normality?.normal
        ? { mean: answer.report.mean, sigma: answer.report.sigma_overall }
        : null
      : analysis?.path === "normal" && analysis.normal
        ? { mean: analysis.normal.mean, sigma: analysis.normal.sigma_overall }
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
        <SpecField
          label="Required Cpk"
          value={required}
          onChange={setRequired}
        />
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

      {answer && (
        <div className="flex flex-col gap-5">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <IndexCard
              label="Pp"
              value={headline.pp}
              required={requiredIndex}
              unavailable="needs both spec limits"
            />
            <IndexCard
              label="Ppk"
              value={headline.ppk}
              required={requiredIndex}
              emphasize
            />
            <IndexCard
              label="Cp"
              value={within?.cp}
              required={requiredIndex}
              unavailable={withinUnavailable ?? "needs both spec limits"}
            />
            <IndexCard
              label="Cpk"
              value={within?.cpk}
              required={requiredIndex}
              emphasize
              unavailable={withinUnavailable}
            />
          </div>

          {/* A printed report has to say what it was judged against: a colour
              means nothing without the threshold behind it, the same reason
              the control chart names the rule set it applied. */}
          <p className="text-xs text-muted">
            {requiredIndex == null
              ? "No required index is set, so the indices below are not coloured. Enter the value your customer specifies — 1.33 and 1.67 are both common, and the same Cpk passes one and fails the other."
              : `Coloured against a required index of ${requiredIndex}: at or above it, the process meets the requirement; between 1.00 and it, the process is capable but short; below 1.00 the spread does not fit the tolerance at all. capstat-core states no such threshold — it is a customer's specification, not a property of the statistic.`}
          </p>

          <div className="rounded-lg border border-foreground/15 p-4">
            <div className="mb-2 flex items-center gap-2">
              <span className="rounded bg-foreground/10 px-2 py-0.5 text-xs font-medium">
                {analysis
                  ? `Path: ${PATH_LABEL[analysis.path]}`
                  : `Subgroups of ${subgroupSize}`}
              </span>
              {normality && <NormalityBadge normal={normality.normal} />}
            </div>
            <p className="text-sm text-foreground/70">
              {analysis
                ? analysis.rationale
                : `Cp and Cpk here rest on a within-subgroup sigma estimated from ${within?.subgroups ?? 0} subgroups of ${subgroupSize}, which is what subgrouping buys. The normal/Box-Cox/percentile decision path is not run on subgrouped data — it works on a flat sample — so if the normal model is in doubt, read the warnings below and re-run at subgroup size 1 to have the path choose.`}
            </p>
            {normality && (
              <p className="mt-2 text-xs text-muted">
                {normality.recommendation}
              </p>
            )}
          </div>

          {warnings.length > 0 && (
            <ul className="list-disc space-y-1 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 pl-8 text-sm text-amber-800 dark:text-amber-200/90">
              {warnings.map((w, i) => (
                <li key={i} data-code={w.code}>
                  {w.message}
                </li>
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
  required,
  emphasize = false,
  unavailable,
}: {
  label: string;
  value: number | null | undefined;
  /** The customer's required index; null leaves the card uncoloured. */
  required: number | null;
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
            BAND_TONE[capabilityBand(value, required)],
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
