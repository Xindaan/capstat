"use client";

import { useCallback, useState } from "react";

import {
  AcceptanceSamplingPanel,
  EXAMPLE_PLAN_INPUTS,
  type SamplingPlanInputs,
} from "./acceptance-sampling-panel";
import { StudyFileControls } from "./study-file-controls";
import { readChoice, readFlag, readSection, readText } from "@/lib/study-file";
import {
  EXAMPLE_SCHEME_INPUTS,
  SwitchingSchemePanel,
  type SwitchingSchemeInputs,
} from "./switching-scheme-panel";

/** Everything this page's two panels hold that a user typed. No results. */
export interface AcceptanceSamplingStudy {
  plan: SamplingPlanInputs;
  scheme: SwitchingSchemeInputs;
}

const PAGE = "acceptance-sampling";

/** Typed reading of a loaded document's `inputs`, or a refusal (T-0055). */
function readAcceptanceSamplingStudy(
  inputs: Record<string, unknown>,
): AcceptanceSamplingStudy {
  return {
    plan: readSection(inputs, "plan", (plan) => ({
      aql: readText(plan, "aql", EXAMPLE_PLAN_INPUTS.aql),
      ltpd: readText(plan, "ltpd", EXAMPLE_PLAN_INPUTS.ltpd),
      producerRisk: readText(
        plan,
        "producerRisk",
        EXAMPLE_PLAN_INPUTS.producerRisk,
      ),
      consumerRisk: readText(
        plan,
        "consumerRisk",
        EXAMPLE_PLAN_INPUTS.consumerRisk,
      ),
      lotSize: readText(plan, "lotSize", EXAMPLE_PLAN_INPUTS.lotSize),
      sampleSize: readText(plan, "sampleSize", EXAMPLE_PLAN_INPUTS.sampleSize),
      acceptanceNumber: readText(
        plan,
        "acceptanceNumber",
        EXAMPLE_PLAN_INPUTS.acceptanceNumber,
      ),
      model: readChoice(
        plan,
        "model",
        ["binomial", "hypergeometric", "poisson"] as const,
        EXAMPLE_PLAN_INPUTS.model,
      ),
      defectives: readText(plan, "defectives", EXAMPLE_PLAN_INPUTS.defectives),
    })),
    scheme: readSection(inputs, "scheme", (scheme) => ({
      outcomes: readText(scheme, "outcomes", EXAMPLE_SCHEME_INPUTS.outcomes),
      authorised: readFlag(
        scheme,
        "authorised",
        EXAMPLE_SCHEME_INPUTS.authorised,
      ),
    })),
  };
}

/**
 * Holds the page's inputs so a study can be saved and loaded.
 *
 * The panels stay in charge of their own state; they merely report it upward
 * and accept a starting value. Loading therefore remounts them with a new
 * `key` rather than pushing state into them mid-life, which keeps every panel
 * an ordinary uncontrolled component and leaves no half-restored state on the
 * screen if a file turns out to be unreadable.
 */
export function AcceptanceSamplingWorkspace() {
  const [study, setStudy] = useState<AcceptanceSamplingStudy>({
    plan: EXAMPLE_PLAN_INPUTS,
    scheme: EXAMPLE_SCHEME_INPUTS,
  });
  const [loaded, setLoaded] = useState<AcceptanceSamplingStudy | null>(null);
  const [generation, setGeneration] = useState(0);

  const onPlanChange = useCallback((plan: SamplingPlanInputs) => {
    setStudy((current) => ({ ...current, plan }));
  }, []);
  const onSchemeChange = useCallback((scheme: SwitchingSchemeInputs) => {
    setStudy((current) => ({ ...current, scheme }));
  }, []);

  const onLoad = useCallback((inputs: AcceptanceSamplingStudy) => {
    // Fall back per panel: a file written before a panel existed should restore
    // the half it does have rather than being refused outright.
    const restored: AcceptanceSamplingStudy = {
      plan: { ...EXAMPLE_PLAN_INPUTS, ...inputs.plan },
      scheme: { ...EXAMPLE_SCHEME_INPUTS, ...inputs.scheme },
    };
    setLoaded(restored);
    setStudy(restored);
    setGeneration((n) => n + 1);
  }, []);

  const start = loaded ?? {
    plan: EXAMPLE_PLAN_INPUTS,
    scheme: EXAMPLE_SCHEME_INPUTS,
  };

  return (
    <div className="flex flex-col gap-10">
      <StudyFileControls
        page={PAGE}
        inputs={study}
        onLoad={onLoad}
        readInputs={readAcceptanceSamplingStudy}
      />
      <AcceptanceSamplingPanel
        key={`plan-${generation}`}
        initial={start.plan}
        onInputsChange={onPlanChange}
      />
      <hr className="border-foreground/10" />
      <SwitchingSchemePanel
        key={`scheme-${generation}`}
        initial={start.scheme}
        onInputsChange={onSchemeChange}
      />
    </div>
  );
}
