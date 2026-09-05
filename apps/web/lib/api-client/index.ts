import createClient from "openapi-fetch";

import type { paths } from "./schema";

// The base URL is build-time configurable; it defaults to the local API so
// `npm run dev` works with `uvicorn capstat_api.main:app` and no extra setup.
const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

/**
 * The single typed entry point to capstat-api. Every request and response is
 * typed from the committed OpenAPI schema, so a contract change surfaces as a
 * TypeScript error rather than a runtime surprise.
 */
export const api = createClient<paths>({ baseUrl });

export type { paths, components } from "./schema";

import type { components } from "./schema";

export type IngestResponse = components["schemas"]["IngestResponse"];
export type IngestColumn = components["schemas"]["IngestColumn"];
export type CapabilityAnalysis = components["schemas"]["CapabilityAnalysisOut"];
export type CapabilityReport = components["schemas"]["CapabilityReportOut"];
export type NormalityAssessment =
  components["schemas"]["NormalityAssessmentOut"];

/** Spec limits for a capability study; at least one of lsl/usl is required. */
export interface SpecLimits {
  lsl: number | null;
  usl: number | null;
  target: number | null;
  alpha?: number;
}

/**
 * Run the full capability decision path (`/compute/capability/analyze`):
 * normality assessment -> normal / Box-Cox / percentile -> Pp, Ppk. The core
 * rejects a call with no spec limits (surfaced here as the API's 422).
 */
export type ChartPair = components["schemas"]["ChartPairOut"];
export type ControlChartData = components["schemas"]["ControlChartOut"];
export type ControlLimits = components["schemas"]["ControlLimitsOut"];
export type RuleViolation = components["schemas"]["RuleViolationOut"];

/**
 * A known in-control centre and sigma, from a stable period.
 *
 * Both or neither: one without the other mixes a parameter from history with
 * one estimated from the data under test, which is neither phase. The API
 * rejects that with the core's own message (T-0076).
 */
export interface Baseline {
  center: number;
  sigma: number;
}

/** Individuals + moving-range chart from ungrouped measurements. */
export function imrChart(data: number[], baseline: Baseline | null = null) {
  return api.POST("/compute/control-chart/i-mr", {
    body: {
      data,
      center: baseline?.center ?? null,
      sigma: baseline?.sigma ?? null,
    },
  });
}

/**
 * Nelson run-rules over an already-computed chart. The rules read their sigma
 * zones from the chart's own limits, so the caller passes plotted points +
 * limits, not raw data. `rules` selects a subset (null = the whole set).
 */
export function nelsonRules(
  points: number[],
  limits: ControlLimits,
  rules: number[] | null = null,
) {
  return api.POST("/compute/rules/nelson", {
    body: { points, limits, rules },
  });
}

/**
 * The rule descriptions, keyed by number. Fetched rather than duplicated in the
 * front end: the wording belongs to the library that implements the rules, and
 * a second copy here would be free to drift from what is actually applied.
 */
export function rulesCatalogue() {
  return api.GET("/rules/catalogue");
}

export type BiasReport = components["schemas"]["BiasReportOut"];
export type LinearityReport = components["schemas"]["LinearityReportOut"];
export type StabilityReport = components["schemas"]["StabilityReportOut"];

/** Bias: repeated readings of one part against its known reference. */
export function biasStudy(measurements: number[], reference: number) {
  return api.POST("/compute/bias", {
    body: { measurements, reference, alpha: 0.05 },
  });
}

/** Linearity: readings of several masters spanning the range. */
export function linearityStudy(
  references: number[],
  measurements: number[][],
  processVariation: number | null,
) {
  return api.POST("/compute/linearity", {
    body: {
      references,
      measurements,
      process_variation: processVariation,
      alpha: 0.05,
    },
  });
}

/** Stability: time-ordered readings of one master (individuals or subgroups). */
export function stabilityStudy(measurements: number[]) {
  return api.POST("/compute/stability", { body: { measurements } });
}

export type GageRRReport = components["schemas"]["GageRRReportOut"];
export type GageRRMethod = GageRRReport["method"];
/** The AIAG band, decided by the core. Null means "not judged", not "good". */
export type GageRRVerdict = NonNullable<GageRRReport["verdict"]>;

export interface GageRROptions {
  method: GageRRMethod;
  tolerance: number | null;
}

/**
 * Gage R&R over a balanced 3-D layout (parts x operators x trials). `method`
 * selects the crossed ANOVA or the average-and-range estimator.
 */
export function gageRR(data: number[][][], opts: GageRROptions) {
  return api.POST("/compute/gage-rr", {
    body: {
      data,
      method: opts.method,
      tolerance: opts.tolerance,
      // openapi-typescript types defaulted fields as required, so pass the
      // server defaults explicitly (the UI does not expose these knobs).
      interaction_alpha: 0.25,
      study_var_multiplier: 6.0,
    },
  });
}

/**
 * Capability from subgroups (`/compute/capability`).
 *
 * The decision path is deliberately not available here: `analyze_capability`
 * takes a flat sample, because Box-Cox and the percentile fit both work on one.
 * With subgroups you get the classic report instead -- and a genuine
 * within-subgroup sigma, which is the whole reason to subgroup (T-0075).
 */
export function capabilityFromSubgroups(
  subgroups: number[][],
  limits: SpecLimits,
) {
  return api.POST("/compute/capability", {
    body: {
      data: subgroups,
      lsl: limits.lsl,
      usl: limits.usl,
      target: limits.target,
      // openapi-typescript types defaulted fields as required; the UI does not
      // expose the estimator, so pass the server default explicitly.
      within_method: null,
      alpha: limits.alpha ?? 0.05,
    },
  });
}

/** X-bar and R charts: subgroup averages, spread from the range. */
export function xbarRChart(
  subgroups: number[][],
  baseline: Baseline | null = null,
) {
  return api.POST("/compute/control-chart/xbar-r", {
    body: {
      subgroups,
      center: baseline?.center ?? null,
      sigma: baseline?.sigma ?? null,
    },
  });
}

/** X-bar and s charts: subgroup averages, spread from the standard deviation. */
export function xbarSChart(
  subgroups: number[][],
  baseline: Baseline | null = null,
) {
  return api.POST("/compute/control-chart/xbar-s", {
    body: {
      subgroups,
      center: baseline?.center ?? null,
      sigma: baseline?.sigma ?? null,
    },
  });
}

export function analyzeCapability(data: number[], limits: SpecLimits) {
  return api.POST("/compute/capability/analyze", {
    body: {
      data,
      lsl: limits.lsl,
      usl: limits.usl,
      target: limits.target,
      alpha: limits.alpha ?? 0.05,
    },
  });
}

/**
 * POST a file to `/ingest` as multipart/form-data.
 *
 * `openapi-typescript` maps the binary body field to `string`, and
 * `openapi-fetch` JSON-serialises bodies by default; both are wrong for a file
 * upload. This helper is the single place that reconciles them — it builds a
 * `FormData` so the browser sets the multipart boundary, while the response
 * stays fully typed as {@link IngestResponse}.
 */
export function ingestFile(file: File) {
  return api.POST("/ingest", {
    // The field is typed `string` (binary); the File is what actually goes on
    // the wire via the serializer below.
    body: { file: file as unknown as string },
    bodySerializer() {
      const form = new FormData();
      form.set("file", file);
      return form;
    },
  });
}

export type SamplingPlan = components["schemas"]["SamplingPlanOut"];
export type SamplingPlanReport = components["schemas"]["SamplingPlanReportOut"];
export type OCCurve = components["schemas"]["OCCurveOut"];
export type LotDecision = components["schemas"]["LotDecisionOut"];
export type SamplingModel = SamplingPlanReport["model"];

export interface SamplingPlanInput {
  sample_size: number;
  acceptance_number: number;
  lot_size: number | null;
}

/**
 * Judge a sampling plan at the two quality levels it exists to discriminate.
 * `aql` and `ltpd` are fractions defective, not percentages — the API rejects
 * anything above 1, which is the mistake worth catching early.
 */
export function evaluateSamplingPlan(
  plan: SamplingPlanInput,
  aql: number,
  ltpd: number,
  model: SamplingModel,
) {
  return api.POST("/compute/acceptance-sampling/evaluate", {
    body: { plan, aql, ltpd, model },
  });
}

/** The smallest plan meeting both risk points, searched over the OC curve. */
export function designSamplingPlan(opts: {
  aql: number;
  ltpd: number;
  producerRisk: number;
  consumerRisk: number;
  model: SamplingModel;
  lotSize: number | null;
}) {
  return api.POST("/compute/acceptance-sampling/design", {
    body: {
      aql: opts.aql,
      ltpd: opts.ltpd,
      // openapi-typescript types defaulted fields as required, so pass the
      // server defaults explicitly.
      producer_risk: opts.producerRisk,
      consumer_risk: opts.consumerRisk,
      model: opts.model,
      lot_size: opts.lotSize,
    },
  });
}

/** The plan's OC curve. `null` grid lets the core derive a readable one. */
export function samplingOcCurve(
  plan: SamplingPlanInput,
  model: SamplingModel,
  fractionDefective: number[] | null = null,
) {
  return api.POST("/compute/acceptance-sampling/oc-curve", {
    body: { plan, model, fraction_defective: fractionDefective },
  });
}

/** Apply a plan to one observed sample. The answer is a decision, not a score. */
export function inspectLot(
  plan: SamplingPlanInput,
  defectives: number,
  model: SamplingModel,
) {
  return api.POST("/compute/acceptance-sampling/inspect", {
    body: { plan, defectives, model },
  });
}

export type SchemeHistory = components["schemas"]["SchemeHistoryOut"];
export type SchemeStep = components["schemas"]["SchemeStepOut"];
export type InspectionSeverity = SchemeHistory["final_severity"];

export interface LotOutcome {
  accepted: boolean;
  /**
   * The switching score's harder question (ISO 2859-1 clause 9.3.3.2): would
   * this lot still have been accepted one AQL step tighter? `null` means "not
   * answered", and the lot is then scored on the conservative rule.
   */
  accepted_at_tighter_aql: boolean | null;
}

/**
 * Run a series of lot outcomes through the ISO 2859-1 switching rules.
 *
 * `authorised` covers the two conditions of clause 9.3.3.1 that are not
 * statistics — steady production and the responsible authority judging reduced
 * inspection desirable. Left false, the scheme never relaxes.
 */
export function switchingRules(lots: LotOutcome[], authorised: boolean) {
  return api.POST("/compute/acceptance-sampling/switching-rules", {
    body: {
      lots,
      // openapi-typescript types defaulted fields as required, so pass the
      // server defaults explicitly.
      start: "normal",
      reduced_inspection_authorised: authorised,
      rules: null,
    },
  });
}
