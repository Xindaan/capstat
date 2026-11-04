"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  gageRR,
  type GageRRMethod,
  type GageRRReport,
  type GageRRVerdict,
} from "@/lib/api-client";
import { ErrorAlert } from "./error-alert";
import { NumericInput } from "./numeric-input";
import { callApi } from "@/lib/call-api";
import {
  readCount,
  readDecimal,
  readPastedBlock,
  type Block,
  type Read,
} from "@/lib/numbers";

// The SPC/AIAG worked example (5 parts x 3 operators x 3 trials), so the page
// computes something real on first load.
const EXAMPLE: string[][][] = [
  [
    ["3.29", "3.41", "3.64"],
    ["3.08", "3.25", "3.07"],
    ["3.04", "2.89", "2.85"],
  ],
  [
    ["2.44", "2.32", "2.42"],
    ["2.53", "1.78", "2.32"],
    ["1.62", "1.87", "2.04"],
  ],
  [
    ["4.34", "4.17", "4.27"],
    ["4.19", "3.94", "4.34"],
    ["3.88", "4.09", "3.67"],
  ],
  [
    ["3.47", "3.50", "3.64"],
    ["3.01", "4.03", "3.20"],
    ["3.14", "3.20", "3.11"],
  ],
  [
    ["2.20", "2.08", "2.16"],
    ["2.44", "1.80", "1.72"],
    ["1.54", "1.93", "1.55"],
  ],
];

const OPERATOR_LABELS = "ABCDEFGH";

/**
 * Largest value a study dimension may take.
 *
 * Not a statistical limit — the core imposes none — but a guard on the grid this
 * page builds: three fields multiply, so an unbounded one turns a fat-fingered
 * "1000" into a million inputs and a wedged tab. Thirty is well above any real
 * study (AIAG's worked example is 10 parts x 3 operators x 3 trials), and a
 * value beyond it is refused rather than clamped, so nothing is resized to a
 * number nobody asked for.
 */
const MAX_DIMENSION = 30;

type Status =
  | { kind: "idle" }
  | { kind: "computing" }
  | { kind: "done"; result: GageRRReport }
  | { kind: "error"; message: string };

function fmt(value: number | null | undefined, digits = 4): string {
  return value == null || Number.isNaN(value) ? "—" : value.toFixed(digits);
}

/**
 * Colour for the AIAG verdict the API states.
 *
 * The bands used to be written here as 10 and 30 as well as in the core, so a
 * threshold changed in one place would leave the card coloured by the other --
 * a traffic light contradicting the printed warning beside it (T-0058). This
 * function now knows the three words and none of the numbers.
 *
 * `null` is "not judged" -- a gage with no variation of its own -- and is
 * deliberately not green: nothing was established.
 */
function verdictTone(verdict: GageRRVerdict | null): string {
  switch (verdict) {
    case "good":
      return "text-emerald-600 dark:text-emerald-400";
    case "marginal":
      return "text-amber-600 dark:text-amber-400";
    case "unacceptable":
      return "text-red-600 dark:text-red-400";
    default:
      return "text-muted";
  }
}

/** Same rule for ndc: the API says whether it is adequate, this picks a colour. */
function adequacyTone(adequate: boolean | null): string {
  if (adequate == null) return "text-muted";
  return adequate
    ? "text-emerald-600 dark:text-emerald-400"
    : "text-red-600 dark:text-red-400";
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

export interface GageRRInputs {
  parts: number;
  operators: number;
  trials: number;
  grid: string[][][];
  method: GageRRMethod;
  tolerance: string;
}

export const EXAMPLE_GAGE_RR_INPUTS: GageRRInputs = {
  parts: 5,
  operators: 3,
  trials: 3,
  grid: EXAMPLE,
  method: "anova",
  tolerance: "",
};

export function GageRRPanel({
  initial = EXAMPLE_GAGE_RR_INPUTS,
  onInputsChange,
}: {
  initial?: GageRRInputs;
  onInputsChange?: (inputs: GageRRInputs) => void;
} = {}) {
  const [parts, setParts] = useState(initial.parts);
  const [operators, setOperators] = useState(initial.operators);
  const [trials, setTrials] = useState(initial.trials);
  const [grid, setGrid] = useState<string[][][]>(initial.grid);
  const [method, setMethod] = useState<GageRRMethod>(initial.method);
  const [tolerance, setTolerance] = useState(initial.tolerance);
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  // Why the last paste into the grid was refused, if it was.
  const [pasteNote, setPasteNote] = useState<string | null>(null);

  useEffect(() => {
    onInputsChange?.({ parts, operators, trials, grid, method, tolerance });
  }, [parts, operators, trials, grid, method, tolerance, onInputsChange]);

  const resize = useCallback((p: number, o: number, t: number) => {
    setParts(p);
    setOperators(o);
    setTrials(t);
    setGrid((g) => resizeGrid(g, p, o, t));
    setStatus({ kind: "idle" });
    setPasteNote(null);
  }, []);

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

  /**
   * Fill the grid from a block copied out of a spreadsheet (T-0100, WEB-22).
   *
   * The sheet's layout is the grid's layout: one row per part, and the columns
   * run through each operator's trials in turn. The block lands with its
   * top-left corner on the cell it was pasted into. A block that does not fit,
   * or whose rows are uneven, is refused whole -- a partly pasted study is the
   * thing to avoid, since the rest of the grid already holds the example.
   */
  const pasteBlock = (
    p0: number,
    o0: number,
    t0: number,
    pasted: Read<Block>,
  ) => {
    if (!pasted.ok) {
      setPasteNote(pasted.reason);
      return;
    }
    const block = pasted.value;
    const columns = operators * trials;
    const start = o0 * trials + t0;
    const width = block[0].length;
    const where = `Part ${p0 + 1}, operator ${OPERATOR_LABELS[o0] ?? o0 + 1}, trial ${t0 + 1}`;
    if (block.some((row) => row.length !== width)) {
      setPasteNote(
        "Nothing was pasted: the rows of the block have different numbers of columns.",
      );
      return;
    }
    if (p0 + block.length > parts || start + width > columns) {
      setPasteNote(
        `Nothing was pasted: the block has ${block.length} rows and ${width} columns, ` +
          `but from ${where} only ${parts - p0} rows and ${columns - start} columns fit. ` +
          "Rows are parts; columns run through each operator's trials.",
      );
      return;
    }
    setPasteNote(null);
    setGrid((g) =>
      g.map((part, p) =>
        part.map((op, o) =>
          op.map((cell, t) => {
            const row = block[p - p0];
            const col = o * trials + t - start;
            return row !== undefined && col >= 0 && col < width
              ? row[col]
              : cell;
          }),
        ),
      ),
    );
  };

  // Parse to numbers; the grid is valid only when every cell is a finite number.
  const parsed = useMemo(() => {
    const data: number[][][] = [];
    for (const part of grid) {
      const prow: number[][] = [];
      for (const op of part) {
        const cells: number[] = [];
        for (const cell of op) {
          const read = readDecimal(cell);
          if (!read.ok) return null;
          cells.push(read.value);
        }
        prow.push(cells);
      }
      data.push(prow);
    }
    return data;
  }, [grid]);

  const tolRead = readDecimal(tolerance);
  const tol = tolRead.ok ? tolRead.value : null;
  const tolInvalid =
    tolerance.trim() !== "" && (!tolRead.ok || (tol != null && tol <= 0));
  const canCompute =
    parsed != null && !tolInvalid && status.kind !== "computing";

  const compute = async () => {
    if (parsed == null || tolInvalid) return;
    setStatus({ kind: "computing" });
    const outcome = await callApi(
      () => gageRR(parsed, { method, tolerance: tol }),
      "Gage R&R could not be computed.",
    );
    if (!outcome.ok) {
      setStatus({ kind: "error", message: outcome.message });
      return;
    }
    setStatus({ kind: "done", result: outcome.data });
  };

  const result = status.kind === "done" ? status.result : null;

  return (
    <section className="flex flex-col gap-6" aria-label="Gage R&R">
      <div className="flex flex-wrap items-end gap-3">
        <DimField
          label="Parts"
          value={parts}
          min={2}
          onChange={(v) => resize(v, operators, trials)}
        />
        <DimField
          label="Operators"
          value={operators}
          min={2}
          onChange={(v) => resize(parts, v, trials)}
        />
        <DimField
          label="Trials"
          value={trials}
          min={2}
          onChange={(v) => resize(parts, operators, v)}
        />
        <label className="flex flex-col gap-1">
          <span className="text-xs uppercase tracking-wide text-muted">
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
          <span className="text-xs uppercase tracking-wide text-muted">
            Tolerance
          </span>
          <NumericInput
            aria-label="Tolerance"
            value={tolerance}
            onChange={setTolerance}
            placeholder="optional"
            className="h-10 w-28 rounded-lg border border-foreground/20 bg-transparent px-3 text-sm tabular-nums focus:border-foreground/50 focus:outline-none"
          />
        </label>
      </div>

      <DataGrid grid={grid} onCell={setCell} onBlock={pasteBlock} />
      {pasteNote && (
        <p role="status" className="text-xs text-amber-600 dark:text-amber-400">
          {pasteNote}
        </p>
      )}

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

      {status.kind === "error" && <ErrorAlert message={status.message} />}

      {result && <Report result={result} />}
    </section>
  );
}

/**
 * A study dimension: typed freely, applied only when it is a whole number in
 * range.
 *
 * It used to resize the grid on every keystroke, clamping whatever stood in the
 * box up to `min` as it went. Typing "10" over a 5 therefore went through "1",
 * which clamped to 2 and truncated the grid to two parts — the measurements for
 * parts 3 to 5 were gone before the second digit was typed, with no undo
 * (T-0065). The draft is now local text, and the resize happens when the field
 * is left or Enter is pressed: one resize per edit, from the number the user
 * actually meant.
 */
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
  const [draft, setDraft] = useState(String(value));

  // The committed value also changes from outside — a loaded study, a remount —
  // and the box has to follow it rather than keep showing what was last typed.
  // Adjusted during render rather than in an effect: React supports exactly
  // this for "a prop changed, reset the state derived from it", and it avoids
  // the extra paint an effect would cause (the lint rule that forbids
  // setState-in-effect is pointing at the same thing).
  const [lastSeen, setLastSeen] = useState(value);
  if (lastSeen !== value) {
    setLastSeen(value);
    setDraft(String(value));
  }

  const read = readCount(draft, { min, max: MAX_DIMENSION });
  const valid = read.ok;
  const parsed = read.ok ? read.value : NaN;

  const commit = () => {
    if (valid) {
      if (parsed !== value) onChange(parsed);
    } else {
      // Refuse rather than clamp: clamping is what silently resized the grid to
      // a number nobody asked for.
      setDraft(String(value));
    }
  };

  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-muted">
        {label}
      </span>
      <NumericInput
        // Named explicitly because the range hint below lives inside this
        // label, and without an aria-label it would join the field's accessible
        // name the moment it appears — the box would stop being "Parts" and
        // become "Parts 2–30" exactly when a user most needs it to be findable.
        aria-label={label}
        kind="integer"
        min={min}
        max={MAX_DIMENSION}
        showProblem={false}
        value={draft}
        onChange={setDraft}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            commit();
          }
        }}
        className="h-10 w-20 rounded-lg border border-foreground/20 bg-transparent px-3 text-sm tabular-nums focus:border-foreground/50 focus:outline-none"
      />
      {!valid && (
        <span className="text-[11px] text-amber-600 dark:text-amber-400">
          {min}–{MAX_DIMENSION}
        </span>
      )}
    </label>
  );
}

/**
 * The cell above or below the one that has focus (Up, Down, Enter).
 *
 * A grid of text boxes has no stepping arrows to misuse, so the keys are free
 * to do what a spreadsheet's do. Left and Right stay with the caret.
 */
function moveFocus(
  table: HTMLTableElement | null,
  p: number,
  o: number,
  t: number,
  by: 1 | -1,
) {
  table
    ?.querySelector<HTMLInputElement>(`[data-cell="${p + by}-${o}-${t}"]`)
    ?.focus();
}

function DataGrid({
  grid,
  onCell,
  onBlock,
}: {
  grid: string[][][];
  onCell: (p: number, o: number, t: number, value: string) => void;
  onBlock: (p: number, o: number, t: number, block: Read<Block>) => void;
}) {
  const operators = grid[0]?.length ?? 0;
  const trials = grid[0]?.[0]?.length ?? 0;
  const tableRef = useRef<HTMLTableElement>(null);
  return (
    <div className="overflow-x-auto rounded-lg border border-foreground/15">
      <table ref={tableRef} className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-foreground/15">
            <th className="p-2 text-left font-medium text-muted">Part</th>
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
              <td className="p-2 text-muted">{p + 1}</td>
              {part.map((op, o) =>
                op.map((cell, t) => (
                  <td
                    key={`${o}-${t}`}
                    className={
                      t === 0 ? "border-l border-foreground/15 p-1" : "p-1"
                    }
                  >
                    <NumericInput
                      showProblem={false}
                      value={cell}
                      onChange={(v) => onCell(p, o, t, v)}
                      data-cell={`${p}-${o}-${t}`}
                      onPaste={(e) => {
                        const block = readPastedBlock(
                          e.clipboardData.getData("text/plain"),
                        );
                        // A single value is not a block: the box takes it in.
                        if (block === null) return;
                        e.preventDefault();
                        onBlock(p, o, t, block);
                      }}
                      onKeyDown={(e) => {
                        if (
                          e.key === "ArrowDown" ||
                          (e.key === "Enter" && !e.shiftKey)
                        ) {
                          e.preventDefault();
                          moveFocus(tableRef.current, p, o, t, 1);
                        } else if (
                          e.key === "ArrowUp" ||
                          (e.key === "Enter" && e.shiftKey)
                        ) {
                          e.preventDefault();
                          moveFocus(tableRef.current, p, o, t, -1);
                        }
                      }}
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
        <Card
          label="% Study Var (GRR)"
          value={fmt(result.pct_study_var_gage_rr, 1)}
          suffix="%"
          tone={verdictTone(result.verdict)}
          emphasize
        />
        <Card
          label="ndc"
          value={result.ndc == null ? "—" : String(result.ndc)}
          tone={adequacyTone(result.ndc_adequate)}
          emphasize
        />
        <Card
          label="% Contribution (GRR)"
          value={fmt(result.pct_contribution_gage_rr, 2)}
          suffix="%"
        />
        <Card
          label="Method"
          value={result.method === "anova" ? "ANOVA" : "Avg & range"}
        />
      </div>

      <div className="overflow-x-auto rounded-lg border border-foreground/15">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-foreground/15 text-muted">
              <th className="p-2 text-left font-medium">Source</th>
              <th className="p-2 text-right font-medium">Variance</th>
              <th className="p-2 text-right font-medium">% Contribution</th>
              <th className="p-2 text-right font-medium">% Study Var</th>
            </tr>
          </thead>
          <tbody className="tabular-nums">
            {rows.map((r) => (
              <tr key={r.label} className="border-t border-foreground/10">
                <td
                  className={`p-2 ${r.indent ? "pl-6 text-foreground/70" : "font-medium"}`}
                >
                  {r.label}
                </td>
                <td className="p-2 text-right font-mono">
                  {fmt(r.variance, 5)}
                </td>
                <td className="p-2 text-right font-mono">
                  {fmt(r.contribution, 2)}
                </td>
                <td className="p-2 text-right font-mono">
                  {fmt(r.studyVar, 2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {result.method === "anova" && (
        <p className="text-xs text-muted">
          {result.interaction_included
            ? `Part-operator interaction retained (p = ${fmt(result.interaction_pvalue, 3)}).`
            : `Part-operator interaction pooled into repeatability (p = ${fmt(result.interaction_pvalue, 3)} > 0.25).`}
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
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
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
