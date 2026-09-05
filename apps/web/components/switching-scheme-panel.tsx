"use client";

import { useEffect, useState } from "react";

import {
  switchingRules,
  type SchemeHistory,
  type InspectionSeverity,
} from "@/lib/api-client";
import { ErrorAlert } from "./error-alert";
import { callApi } from "@/lib/call-api";

// Thirteen lots that exercise both transitions: two non-acceptable four apart
// tighten the scheme at lot 6, and five consecutive acceptable lots earn normal
// inspection back at lot 12. Built here rather than taken from the standard's
// own worked example, which is a table capstat does not reproduce.
const EXAMPLE = "A A R A A R A A A A A A A";

export interface SwitchingSchemeInputs {
  outcomes: string;
  authorised: boolean;
}

export const EXAMPLE_SCHEME_INPUTS: SwitchingSchemeInputs = {
  outcomes: EXAMPLE,
  authorised: false,
};

type Status =
  | { kind: "idle" }
  | { kind: "computing" }
  | { kind: "done"; history: SchemeHistory }
  | { kind: "error"; message: string };

/** A/R, ticks, or 0/1 — whatever the inspector's notes actually look like. */
function parseOutcomes(text: string): boolean[] | null {
  const marks = text.toUpperCase().replace(/[\s,;|]+/g, "");
  if (marks.length === 0) return null;
  const outcomes: boolean[] = [];
  for (const mark of marks) {
    if (mark === "A" || mark === "1" || mark === "✓") outcomes.push(true);
    else if (mark === "R" || mark === "0" || mark === "✗") outcomes.push(false);
    else return null;
  }
  return outcomes;
}

const SEVERITY_LABEL: Record<InspectionSeverity, string> = {
  normal: "Normal",
  tightened: "Tightened",
  reduced: "Reduced",
  discontinued: "Discontinued",
};

/** Severity is a state, not a score: four states, four colours, no gradient. */
function severityTone(severity: InspectionSeverity): string {
  if (severity === "normal") return "text-foreground";
  if (severity === "reduced") return "text-emerald-600 dark:text-emerald-400";
  if (severity === "tightened") return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

export function SwitchingSchemePanel({
  initial = EXAMPLE_SCHEME_INPUTS,
  onInputsChange,
}: {
  initial?: SwitchingSchemeInputs;
  onInputsChange?: (inputs: SwitchingSchemeInputs) => void;
} = {}) {
  const [text, setText] = useState(initial.outcomes);
  const [authorised, setAuthorised] = useState(initial.authorised);
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  useEffect(() => {
    onInputsChange?.({ outcomes: text, authorised });
  }, [text, authorised, onInputsChange]);

  const outcomes = parseOutcomes(text);
  const valid = outcomes != null;
  const busy = status.kind === "computing";

  const compute = async () => {
    if (outcomes == null) return;
    setStatus({ kind: "computing" });
    const outcome = await callApi(
      () =>
        switchingRules(
          outcomes.map((accepted) => ({
            accepted,
            accepted_at_tighter_aql: null,
          })),
          authorised,
        ),
      "The series could not be judged.",
    );
    if (!outcome.ok) {
      setStatus({ kind: "error", message: outcome.message });
      return;
    }
    setStatus({ kind: "done", history: outcome.data });
  };

  const history = status.kind === "done" ? status.history : null;

  return (
    <section className="flex flex-col gap-6" aria-label="Switching rules">
      <div>
        <h2 className="text-lg font-medium">Switching rules</h2>
        <p className="text-sm text-foreground/60">
          A plan judges one lot; a scheme judges a supplier. Enter the lots in
          the order they were presented — &quot;A&quot; for an acceptable lot,
          &quot;R&quot; for one that is not — and capstat applies ISO
          2859-1&apos;s switching rules to the series. Original inspection only:
          a lot resubmitted after screening counts towards none of the rules.
        </p>
      </div>

      <label className="flex flex-col gap-1">
        <span className="text-xs uppercase tracking-wide text-muted">
          Lot outcomes
        </span>
        <textarea
          aria-label="Lot outcomes"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={2}
          className="rounded-lg border border-foreground/20 bg-transparent p-3 font-mono text-sm tracking-widest focus:border-foreground/50 focus:outline-none"
        />
      </label>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => void compute()}
          disabled={!valid || busy}
          className="h-10 rounded-lg bg-foreground px-4 text-sm font-medium text-background transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy ? "Computing…" : "Apply the switching rules"}
        </button>
        <label className="no-print flex items-center gap-2 text-sm text-foreground/70">
          <input
            type="checkbox"
            checked={authorised}
            onChange={(e) => setAuthorised(e.target.checked)}
            className="h-4 w-4"
          />
          Reduced inspection authorised
        </label>
        {!valid && (
          <span className="text-xs text-amber-600 dark:text-amber-400">
            Use A for an acceptable lot and R for one that is not.
          </span>
        )}
      </div>

      {status.kind === "error" && <ErrorAlert message={status.message} />}

      {history && (
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Card
              label="Ends on"
              value={SEVERITY_LABEL[history.final_severity]}
              tone={severityTone(history.final_severity)}
              emphasize
            />
            <Card label="Lots" value={String(history.steps.length)} />
            <Card
              label="Switches"
              value={String(history.steps.filter((s) => s.switched).length)}
            />
            <Card
              label="Reduced allowed"
              value={authorised ? "Yes" : "No"}
              tone={authorised ? undefined : "text-muted"}
            />
          </div>

          <div className="overflow-x-auto rounded-lg border border-foreground/15">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-foreground/15 text-left text-muted">
                  <th className="px-3 py-2 font-normal">Lot</th>
                  <th className="px-3 py-2 font-normal">Outcome</th>
                  <th className="px-3 py-2 font-normal">Inspected under</th>
                  <th className="px-3 py-2 font-normal">Switching score</th>
                </tr>
              </thead>
              <tbody className="tabular-nums">
                {history.steps.map((step) => (
                  <tr key={step.lot} className="border-t border-foreground/10">
                    <td className="px-3 py-1.5 font-mono">{step.lot}</td>
                    <td className="px-3 py-1.5 font-mono">
                      {step.accepted ? "A" : "R"}
                    </td>
                    <td
                      className={[
                        "px-3 py-1.5",
                        severityTone(step.severity),
                        step.switched ? "font-medium" : "",
                      ].join(" ")}
                    >
                      {SEVERITY_LABEL[step.severity]}
                      {step.switched &&
                        ` → ${SEVERITY_LABEL[step.severity_after]}`}
                    </td>
                    <td className="px-3 py-1.5 font-mono text-foreground/70">
                      {step.switching_score ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="text-xs text-muted">
            A switch takes effect on the lot <em>after</em> the one that
            triggered it — the trigger lot was already inspected under the old
            severity, which is where its sample size came from. The switching
            score is kept only on normal inspection; a dash means the standard
            does not maintain it there.
          </p>

          {history.warnings.length > 0 && (
            <ul className="list-disc space-y-1 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 pl-8 text-sm text-amber-800 dark:text-amber-200/90">
              {history.warnings.map((w, i) => (
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

function Card({
  label,
  value,
  tone,
  emphasize = false,
}: {
  label: string;
  value: string;
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
      </div>
    </div>
  );
}
