"use client";

import { useCallback, useMemo, useState } from "react";

import { gageRR, type GageRRMethod, type GageRRReport } from "@/lib/api-client";
import { describeApiError } from "@/lib/errors";

// The SPC/AIAG worked example (5 parts x 3 operators x 3 trials), so the page
// computes something real on first load.
const EXAMPLE: string[][][] = [
  [["3.29", "3.41", "3.64"], ["3.08", "3.25", "3.07"], ["3.04", "2.89", "2.85"]],
  [["2.44", "2.32", "2.42"], ["2.53", "1.78", "2.32"], ["1.62", "1.87", "2.04"]],
  [["4.34", "4.17", "4.27"], ["4.19", "3.94", "4.34"], ["3.88", "4.09", "3.67"]],
  [["3.47", "3.50", "3.64"], ["3.01", "4.03", "3.20"], ["3.14", "3.20", "3.11"]],
  [["2.20", "2.08", "2.16"], ["2.44", "1.80", "1.72"], ["1.54", "1.93", "1.55"]],
];

const OPERATOR_LABELS = "ABCDEFGH";

type Status =
  | { kind: "idle" }
  | { kind: "computing" }
  | { kind: "done"; result: GageRRReport }
  | { kind: "error"; message: string };

function fmt(value: number | null | undefined, digits = 4): string {
  return value == null || Number.isNaN(value) ? "—" : value.toFixed(digits);
}

/** AIAG verdict colouring for %Study Variation of Gage R&R. */
function grrTone(pct: number | null): string {
  if (pct == null || Number.isNaN(pct)) return "text-foreground/40";
  if (pct < 10) return "text-emerald-600 dark:text-emerald-400";
  if (pct <= 30) return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

/** Resize a parts x operators x trials grid, keeping any overlapping values. */
function resizeGrid(
  old: string[][][],
  parts: number,
  operators: number,
  trials: number,
): string[][][] {
  return Array.from({ length: parts }, (_, p) =>
    Array.from({ length: operators }, (_, o) =>
      Array.from({ length: trials }, (_, t) => old[p]?.[o]?.[t] ?? ""),
    ),
  );
}

export function GageRRPanel() {
  const [parts, setParts] = useState(5);
  const [operators, setOperators] = useState(3);
  const [trials, setTrials] = useState(3);
  const [grid, setGrid] = useState<string[][][]>(EXAMPLE);
  const [method, setMethod] = useState<GageRRMethod>("anova");
  const [tolerance, setTolerance] = useState("");
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  const resize = useCallback(
    (p: number, o: number, t: number) => {
      setParts(p);
      setOperators(o);
      setTrials(t);
      setGrid((g) => resizeGrid(g, p, o, t));
      setStatus({ kind: "idle" });
    },
    [],
  );

  const setCell = useCallback(
    (p: number, o: number, t: number, value: string) => {
      setGrid((g) =>
        g.map((pp, pi) =>
          pi !== p
            ? pp
            : pp.map((oo, oi) =>
                oi !== o ? oo : oo.map((tt, ti) => (ti === t ? value : tt)),
              ),
        ),
      );
    },
    [],
  );

  // Parse to numbers; the grid is valid only when every cell is a finite number.
  const parsed = useMemo(() => {
    const data: number[][][] = [];
    for (const part of grid) {
      const prow: number[][] = [];
      for (const op of part) {
        const cells: number[] = [];
        for (const cell of op) {
          const n = Number(cell);
          if (cell.trim() === "" || Number.isNaN(n)) return null;
          cells.push(n);
        }
        prow.push(cells);
      }
      data.push(prow);
    }
    return data;
  }, [grid]);

  const tol = tolerance.trim() === "" ? null : Number(tolerance);
  const tolInvalid = tol != null && (Number.isNaN(tol) || tol <= 0);
  const canCompute = parsed != null && !tolInvalid && status.kind !== "computing";

  const compute = async () => {
    if (parsed == null || tolInvalid) return;
    setStatus({ kind: "computing" });
    try {
      const { data, error } = await gageRR(parsed, { method, tolerance: tol });
      if (error || !data) {
        setStatus({
          kind: "error",
          message: describeApiError(error, "Gage R&R could not be computed."),
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
    <section className="flex flex-col gap-6" aria-label="Gage R&R">
      <div className="flex flex-wrap items-end gap-3">
        <DimField label="Parts" value={parts} min={2}
          onChange={(v) => resize(v, operators, trials)} />
        <DimField label="Operators" value={operators} min={2}
          onChange={(v) => resize(parts, v, trials)} />
        <DimField label="Trials" value={trials} min={2}
          onChange={(v) => resize(parts, operators, v)} />
        <label className="flex flex-col gap-1">
          <span className="text-xs uppercase tracking-wide text-foreground/50">
            Method
          </span>
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value as GageRRMethod)}
            className="h-10 rounded-lg border border-foreground/20 bg-transparent px-3 text-sm focus:border-foreground/50 focus:outline-none"
          >
            <option value="anova">ANOVA</option>
            <option value="average_range">Average & range</option>
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs uppercase tracking-wide text-foreground/50">
            Tolerance
          </span>
          <input
            type="number"
            inputMode="decimal"
            step="any"
            value={tolerance}
            onChange={(e) => setTolerance(e.target.value)}
            placeholder="optional"
            className="h-10 w-28 rounded-lg border border-foreground/20 bg-transparent px-3 text-sm tabular-nums focus:border-foreground/50 focus:outline-none"
          />
        </label>
      </div>

      <DataGrid grid={grid} onCell={setCell} />

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => void compute()}
          disabled={!canCompute}
          className="h-10 rounded-lg bg-foreground px-4 text-sm font-medium text-background transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {status.kind === "computing" ? "Computing…" : "Compute Gage R&R"}
        </button>
        {parsed == null && (
          <span className="text-xs text-amber-600 dark:text-amber-400">
            Every cell must be a number.
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

      {result && <Report result={result} />}
    </section>
  );
}

function DimField({
  label,
  value,
  min,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-foreground/50">
        {label}
      </span>
      <input
        type="number"
        min={min}
        value={value}
        onChange={(e) => {
          const v = Math.max(min, Math.floor(Number(e.target.value) || min));
          onChange(v);
        }}
        className="h-10 w-20 rounded-lg border border-foreground/20 bg-transparent px-3 text-sm tabular-nums focus:border-foreground/50 focus:outline-none"
      />
    </label>
  );
}

function DataGrid({
  grid,
  onCell,
}: {
  grid: string[][][];
  onCell: (p: number, o: number, t: number, value: string) => void;
}) {
  const operators = grid[0]?.length ?? 0;
  const trials = grid[0]?.[0]?.length ?? 0;
  return (
    <div className="overflow-x-auto rounded-lg border border-foreground/15">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-foreground/15">
            <th className="p-2 text-left font-medium text-foreground/50">Part</th>
            {Array.from({ length: operators }, (_, o) => (
              <th
                key={o}
                colSpan={trials}
                className="border-l border-foreground/15 p-2 text-center font-medium"
              >
                Operator {OPERATOR_LABELS[o] ?? o + 1}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {grid.map((part, p) => (
            <tr key={p} className="border-t border-foreground/10">
              <td className="p-2 text-foreground/50">{p + 1}</td>
              {part.map((op, o) =>
                op.map((cell, t) => (
                  <td
                    key={`${o}-${t}`}
                    className={t === 0 ? "border-l border-foreground/15 p-1" : "p-1"}
                  >
                    <input
                      type="number"
                      inputMode="decimal"
                      step="any"
                      value={cell}
                      onChange={(e) => onCell(p, o, t, e.target.value)}
                      aria-label={`Part ${p + 1}, operator ${OPERATOR_LABELS[o] ?? o + 1}, trial ${t + 1}`}
                      className="h-8 w-16 rounded border border-foreground/15 bg-transparent px-2 text-sm tabular-nums focus:border-foreground/50 focus:outline-none"
                    />
                  </td>
                )),
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Report({ result }: { result: GageRRReport }) {
  const rows: {
    label: string;
    variance: number;
    contribution: number | null;
    studyVar: number | null;
    indent?: boolean;
  }[] = [
    {
      label: "Gage R&R",
      variance: result.var_gage_rr,
      contribution: result.pct_contribution_gage_rr,
      studyVar: result.pct_study_var_gage_rr,
    },
    {
      label: "Repeatability (EV)",
      variance: result.var_repeatability,
      contribution: result.pct_contribution_repeatability,
      studyVar: result.pct_study_var_repeatability,
      indent: true,
    },
    {
      label: "Reproducibility (AV)",
      variance: result.var_reproducibility,
      contribution: result.pct_contribution_reproducibility,
      studyVar: result.pct_study_var_reproducibility,
      indent: true,
    },
    {
      label: "Part (PV)",
      variance: result.var_part,
      contribution: result.pct_contribution_part,
      studyVar: result.pct_study_var_part,
    },
    {
      label: "Total",
      variance: result.var_total,
      contribution: 100,
      studyVar: 100,
    },
  ];

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card label="% Study Var (GRR)" value={fmt(result.pct_study_var_gage_rr, 1)}
          suffix="%" tone={grrTone(result.pct_study_var_gage_rr)} emphasize />
        <Card label="ndc" value={result.ndc == null ? "—" : String(result.ndc)}
          tone={
            result.ndc != null && result.ndc < 5
              ? "text-red-600 dark:text-red-400"
              : "text-emerald-600 dark:text-emerald-400"
          }
          emphasize />
        <Card label="% Contribution (GRR)"
          value={fmt(result.pct_contribution_gage_rr, 2)} suffix="%" />
        <Card label="Method"
          value={result.method === "anova" ? "ANOVA" : "Avg & range"} />
      </div>

      <div className="overflow-x-auto rounded-lg border border-foreground/15">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-foreground/15 text-foreground/50">
              <th className="p-2 text-left font-medium">Source</th>
              <th className="p-2 text-right font-medium">Variance</th>
              <th className="p-2 text-right font-medium">% Contribution</th>
              <th className="p-2 text-right font-medium">% Study Var</th>
            </tr>
          </thead>
          <tbody className="tabular-nums">
            {rows.map((r) => (
              <tr key={r.label} className="border-t border-foreground/10">
                <td className={`p-2 ${r.indent ? "pl-6 text-foreground/70" : "font-medium"}`}>
                  {r.label}
                </td>
                <td className="p-2 text-right font-mono">{fmt(r.variance, 5)}</td>
                <td className="p-2 text-right font-mono">{fmt(r.contribution, 2)}</td>
                <td className="p-2 text-right font-mono">{fmt(r.studyVar, 2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {result.method === "anova" && (
        <p className="text-xs text-foreground/50">
          {result.interaction_included
            ? `Part-operator interaction retained (p = ${fmt(result.interaction_pvalue, 3)}).`
            : `Part-operator interaction pooled into repeatability (p = ${fmt(result.interaction_pvalue, 3)} > 0.25).`}
        </p>
      )}

      {result.warnings.length > 0 && (
        <ul className="list-disc space-y-1 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 pl-8 text-sm text-amber-800 dark:text-amber-200/90">
          {result.warnings.map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Card({
  label,
  value,
  suffix,
  tone,
  emphasize = false,
}: {
  label: string;
  value: string;
  suffix?: string;
  tone?: string;
  emphasize?: boolean;
}) {
  return (
    <div className="rounded-lg border border-foreground/15 p-3">
      <div className="text-xs uppercase tracking-wide text-foreground/40">
        {label}
      </div>
      <div
        className={[
          "font-mono tabular-nums",
          emphasize ? "text-2xl" : "text-xl",
          tone ?? "text-foreground",
        ].join(" ")}
      >
        {value}
        {suffix && value !== "—" ? suffix : ""}
      </div>
    </div>
  );
}
