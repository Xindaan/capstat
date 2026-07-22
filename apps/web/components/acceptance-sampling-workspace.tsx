"use client";

import { useCallback, useState } from "react";

import {
  AcceptanceSamplingPanel,
  EXAMPLE_PLAN_INPUTS,
  type SamplingPlanInputs,
} from "./acceptance-sampling-panel";
import { StudyFileControls } from "./study-file-controls";
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
      <StudyFileControls page={PAGE} inputs={study} onLoad={onLoad} />
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
