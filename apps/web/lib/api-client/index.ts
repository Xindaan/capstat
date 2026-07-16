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

/** Individuals + moving-range chart from ungrouped measurements. */
export function imrChart(data: number[]) {
  return api.POST("/compute/control-chart/i-mr", { body: { data } });
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
