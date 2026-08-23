"use client";

import { useEffect, useState } from "react";

import {
  designSamplingPlan,
  evaluateSamplingPlan,
  inspectLot,
  samplingOcCurve,
  type LotDecision,
  type OCCurve,
  type SamplingModel,
  type SamplingPlanInput,
  type SamplingPlanReport,
} from "@/lib/api-client";
import { callApi } from "@/lib/call-api";

import { OcCurveChart } from "./oc-curve-chart";
import { ErrorAlert } from "./error-alert";

// The AccSamplingDesign vignette's worked example: 1 % acceptable at 2 %
// producer's risk, 5 % rejectable at 15 % consumer's risk. It designs to
// n = 144, Ac = 4 — a number the core's reference tests assert exactly, so the
// page reproduces a published result on first load rather than a plausible one.
export interface SamplingPlanInputs {
  aql: string;
  ltpd: string;
  producerRisk: string;
  consumerRisk: string;
  lotSize: string;
  sampleSize: string;
  acceptanceNumber: string;
  model: SamplingModel;
  defectives: string;
}

const EXAMPLE: SamplingPlanInputs = {
  aql: "1",
  ltpd: "5",
  producerRisk: "2",
  consumerRisk: "15",
  lotSize: "5000",
  sampleSize: "144",
  acceptanceNumber: "4",
  model: "binomial",
  defectives: "2",
};

export const EXAMPLE_PLAN_INPUTS = EXAMPLE;

type Status =
  | { kind: "idle" }
  | { kind: "computing" }
  | { kind: "done"; report: SamplingPlanReport; curve: OCCurve }
  | { kind: "error"; message: string };

function fmt(v: number | null | undefined, d = 4): string {
  return v == null || Number.isNaN(v) ? "—" : v.toFixed(d);
}

function pct(v: number | null | undefined, d = 2): string {
  return v == null || Number.isNaN(v) ? "—" : (v * 100).toFixed(d);
}

/** A risk is comfortable, borderline, or bad — never an inline conditional. */
function riskTone(risk: number | null, allowed: number): string {
  if (risk == null || Number.isNaN(risk)) return "text-muted";
  if (risk <= allowed) return "text-emerald-600 dark:text-emerald-400";
  if (risk <= allowed * 1.5) return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

/** Percent in the box, fraction on the wire. Returns null when unusable. */
function asFraction(text: string): number | null {
  if (text.trim() === "") return null;
  const value = Number(text);
  if (!Number.isFinite(value) || value < 0 || value > 100) return null;
  return value / 100;
}

function asCount(text: string, minimum: number): number | null {
  if (text.trim() === "") return null;
  const value = Number(text);
  if (!Number.isInteger(value) || value < minimum) return null;
  return value;
}

export function AcceptanceSamplingPanel({
  initial = EXAMPLE,
  onInputsChange,
}: {
  initial?: SamplingPlanInputs;
  onInputsChange?: (inputs: SamplingPlanInputs) => void;
} = {}) {
  const [aqlText, setAqlText] = useState(initial.aql);
  const [ltpdText, setLtpdText] = useState(initial.ltpd);
  const [producerText, setProducerText] = useState(initial.producerRisk);
  const [consumerText, setConsumerText] = useState(initial.consumerRisk);
  const [lotText, setLotText] = useState(initial.lotSize);
  const [sampleText, setSampleText] = useState(initial.sampleSize);
  const [acceptText, setAcceptText] = useState(initial.acceptanceNumber);
  const [model, setModel] = useState<SamplingModel>(initial.model);
  const [defectivesText, setDefectivesText] = useState(initial.defectives);
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const [decision, setDecision] = useState<LotDecision | null>(null);

  useEffect(() => {
    onInputsChange?.({
      aql: aqlText,
      ltpd: ltpdText,
      producerRisk: producerText,
      consumerRisk: consumerText,
      lotSize: lotText,
      sampleSize: sampleText,
      acceptanceNumber: acceptText,
      model,
      defectives: defectivesText,
    });
  }, [
    aqlText,
    ltpdText,
    producerText,
    consumerText,
    lotText,
    sampleText,
    acceptText,
    model,
    defectivesText,
    onInputsChange,
  ]);

  const aql = asFraction(aqlText);
  const ltpd = asFraction(ltpdText);
  const producerRisk = asFraction(producerText);
  const consumerRisk = asFraction(consumerText);
  const lotSize = lotText.trim() === "" ? null : asCount(lotText, 1);
  const sampleSize = asCount(sampleText, 1);
  const acceptanceNumber = asCount(acceptText, 0);
  const defectives = asCount(defectivesText, 0);

  const levelsOrdered = aql != null && ltpd != null && aql < ltpd;
  const risksValid =
    producerRisk != null &&
    consumerRisk != null &&
    producerRisk > 0 &&
    producerRisk < 1 &&
    consumerRisk > 0 &&
    consumerRisk < 1;
  const lotValid = lotText.trim() === "" || lotSize != null;
  const canDesign = levelsOrdered && risksValid && lotValid;
  const planValid = sampleSize != null && acceptanceNumber != null;
  const canEvaluate = planValid && levelsOrdered && lotValid;
  const busy = status.kind === "computing";

  const plan = planValid
    ? {
        sample_size: sampleSize,
        acceptance_number: acceptanceNumber,
        lot_size: lotSize,
      }
    : null;

  const fail = (message: string) => setStatus({ kind: "error", message });

  const evaluate = async () => {
    if (plan == null || aql == null || ltpd == null) return;
    setStatus({ kind: "computing" });
    setDecision(null);
    const [evaluated, curved] = await Promise.all([
      callApi(
        () => evaluateSamplingPlan(plan, aql, ltpd, model),
        "The plan could not be judged.",
      ),
      callApi(
        () => samplingOcCurve(plan, model),
        "The OC curve could not be drawn.",
      ),
    ]);
    if (!evaluated.ok) {
      fail(evaluated.message);
      return;
    }
    if (!curved.ok) {
      fail(curved.message);
      return;
    }
    setStatus({ kind: "done", report: evaluated.data, curve: curved.data });
  };

  const design = async () => {
    if (!canDesign || aql == null || ltpd == null) return;
    if (producerRisk == null || consumerRisk == null) return;
    setStatus({ kind: "computing" });
    setDecision(null);
    const plan_ = await callApi(
      () =>
        designSamplingPlan({
          aql,
          ltpd,
          producerRisk,
          consumerRisk,
          model,
          lotSize,
        }),
      "No plan could be designed.",
    );
    if (!plan_.ok) {
      fail(plan_.message);
      return;
    }
    setSampleText(String(plan_.data.sample_size));
    setAcceptText(String(plan_.data.acceptance_number));
    const designed = {
      sample_size: plan_.data.sample_size,
      acceptance_number: plan_.data.acceptance_number,
      lot_size: lotSize,
    };
    const [evaluated, curved] = await Promise.all([
      callApi(
        () => evaluateSamplingPlan(designed, aql, ltpd, model),
        "The designed plan could not be judged.",
      ),
      callApi(
        () => samplingOcCurve(designed, model),
        "The designed plan could not be judged.",
      ),
    ]);
    if (!evaluated.ok) {
      fail(evaluated.message);
      return;
    }
    if (!curved.ok) {
      fail(curved.message);
      return;
    }
    setStatus({ kind: "done", report: evaluated.data, curve: curved.data });
  };

  /**
   * Judge a lot against the plan the report describes -- not against a plan
   * rebuilt from the live fields.
   *
   * Those two used to be the same thing until the user touched an input, and
   * then they were not: clearing "Sample size n" made the derived plan null, so
   * the click returned silently while the button stayed enabled (T-0061). The
   * decision belongs to the plan on screen; taking it from the report also
   * means there is no null case left to fall through.
   */
  const decide = async (judged: SamplingPlanInput) => {
    if (defectives == null) return;
    const outcome = await callApi(
      () => inspectLot(judged, defectives, model),
      "The lot could not be judged.",
    );
    if (!outcome.ok) {
      fail(outcome.message);
      return;
    }
    setDecision(outcome.data);
  };

  const report = status.kind === "done" ? status.report : null;
  const curve = status.kind === "done" ? status.curve : null;

  return (
    <section className="flex flex-col gap-6" aria-label="Acceptance sampling">
      <div className="flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Field
            label="AQL %"
            value={aqlText}
            onChange={setAqlText}
            hint="Acceptable quality"
          />
          <Field
            label="LTPD %"
            value={ltpdText}
            onChange={setLtpdText}
            hint="Rejectable quality"
          />
          <Field
            label="Producer risk %"
            value={producerText}
            onChange={setProducerText}
            hint="Alpha"
          />
          <Field
            label="Consumer risk %"
            value={consumerText}
            onChange={setConsumerText}
            hint="Beta"
          />
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Field
            label="Lot size"
            value={lotText}
            onChange={setLotText}
            hint="Blank = treat as large"
          />
          <Field
            label="Sample size n"
            value={sampleText}
            onChange={setSampleText}
          />
          <Field
            label="Accept on Ac"
            value={acceptText}
            onChange={setAcceptText}
          />
          <label className="no-print flex flex-col gap-1">
            <span className="text-xs uppercase tracking-wide text-muted">
              Model
            </span>
            <select
              aria-label="Sampling model"
              value={model}
              onChange={(e) => setModel(e.target.value as SamplingModel)}
              className="h-10 rounded-lg border border-foreground/20 bg-transparent px-2 text-sm focus:border-foreground/50 focus:outline-none"
            >
              <option value="binomial">Binomial (Type B)</option>
              <option value="hypergeometric">Hypergeometric (Type A)</option>
              <option value="poisson">Poisson</option>
            </select>
          </label>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => void design()}
          disabled={!canDesign || busy}
          className="h-10 rounded-lg bg-foreground px-4 text-sm font-medium text-background transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy ? "Computing…" : "Design the plan"}
        </button>
        <button
          type="button"
          onClick={() => void evaluate()}
          disabled={!canEvaluate || busy}
          className="h-10 rounded-lg border border-foreground/25 px-4 text-sm font-medium transition-opacity hover:opacity-80 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Judge this plan
        </button>
        {!levelsOrdered && (
          <span className="text-xs text-amber-600 dark:text-amber-400">
            The AQL must be a percentage below the LTPD.
          </span>
        )}
        {levelsOrdered && !risksValid && (
          <span className="text-xs text-amber-600 dark:text-amber-400">
            Both risks must be percentages above 0 and below 100.
          </span>
        )}
      </div>

      {status.kind === "error" && <ErrorAlert message={status.message} />}

      {report && curve && (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Card
              label="Sample size"
              value={String(report.plan.sample_size)}
              emphasize
            />
            <Card
              label="Accept on"
              value={`${report.plan.acceptance_number} or fewer`}
            />
            <Card
              label="Producer risk"
              value={pct(report.producer_risk)}
              suffix=" %"
              tone={riskTone(report.producer_risk, producerRisk ?? 0.05)}
            />
            <Card
              label="Consumer risk"
              value={pct(report.consumer_risk)}
              suffix=" %"
              tone={riskTone(report.consumer_risk, consumerRisk ?? 0.1)}
            />
          </div>

          <div className="rounded-lg border border-foreground/15 p-4">
            <OcCurveChart
              fractionDefective={curve.fraction_defective}
              probabilityAccept={curve.probability_accept}
              aql={report.aql}
              ltpd={report.ltpd}
            />
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Card
              label="Indifference quality"
              value={pct(report.indifference_quality)}
              suffix=" %"
            />
            <Card
              label="Limiting quality"
              value={pct(report.limiting_quality)}
              suffix=" %"
              tone={
                report.limiting_quality > report.ltpd
                  ? "text-amber-600 dark:text-amber-400"
                  : undefined
              }
            />
            <Card
              label="AOQL"
              value={report.aoql ? pct(report.aoql.aoql) : "—"}
              suffix={report.aoql ? " %" : ""}
            />
            <Card label="Inspected per lot" value={fmt(report.ati_at_aql, 1)} />
          </div>

          <p className="text-xs text-muted">
            At the AQL the plan accepts {pct(report.probability_accept_at_aql)}{" "}
            % of lots; at the LTPD it still accepts{" "}
            {pct(report.probability_accept_at_ltpd)} %. It is a coin flip at{" "}
            {pct(report.indifference_quality)} % defective. Its limiting quality
            — ISO 2859-1&apos;s LQ, the quality it still accepts one time in ten
            — is {pct(report.limiting_quality)} %.
            {report.aoql &&
              ` The AOQL occurs at ${pct(report.aoql.at_fraction_defective)} % incoming.`}
          </p>

          <div className="flex flex-col gap-2 rounded-lg border border-foreground/15 p-4">
            <span className="text-xs uppercase tracking-wide text-muted">
              Decide a lot
            </span>
            <div className="flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-2 text-sm">
                <span className="text-foreground/60">Defectives found</span>
                <input
                  aria-label="Defectives found in the sample"
                  type="number"
                  min={0}
                  value={defectivesText}
                  onChange={(e) => setDefectivesText(e.target.value)}
                  className="h-9 w-24 rounded-lg border border-foreground/20 bg-transparent px-3 text-sm tabular-nums focus:border-foreground/50 focus:outline-none"
                />
              </label>
              <button
                type="button"
                onClick={() => void decide(report.plan)}
                disabled={defectives == null}
                className="h-9 rounded-lg border border-foreground/25 px-3 text-sm font-medium transition-opacity hover:opacity-80 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Decide the lot
              </button>
              {decision && (
                <span
                  className={[
                    "font-mono text-sm",
                    decision.accepted
                      ? "text-emerald-600 dark:text-emerald-400"
                      : "text-red-600 dark:text-red-400",
                  ].join(" ")}
                >
                  {decision.accepted ? "Accept" : "Reject"}
                </span>
              )}
            </div>
            {decision && (
              <ul className="list-disc space-y-1 pl-5 text-xs text-foreground/60">
                {decision.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            )}
          </div>

          {report.warnings.length > 0 && (
            <ul className="list-disc space-y-1 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 pl-8 text-sm text-amber-800 dark:text-amber-200/90">
              {report.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

function Field({
  label,
  value,
  onChange,
  hint,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  hint?: string;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-muted">
        {label}
      </span>
      <input
        aria-label={label}
        type="number"
        step="any"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-10 rounded-lg border border-foreground/20 bg-transparent px-3 text-sm tabular-nums focus:border-foreground/50 focus:outline-none"
      />
      {hint && <span className="text-[11px] text-muted">{hint}</span>}
    </label>
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
