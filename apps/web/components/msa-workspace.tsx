"use client";

import { useCallback, useState } from "react";

import { BiasPanel, EXAMPLE_BIAS_INPUTS, type BiasInputs } from "./bias-panel";
import {
  EXAMPLE_LINEARITY_INPUTS,
  LinearityPanel,
  type LinearityInputs,
} from "./linearity-panel";
import {
  EXAMPLE_STABILITY_INPUTS,
  StabilityPanel,
  type StabilityInputs,
} from "./stability-panel";
import { StudyFileControls } from "./study-file-controls";

/** The three MSA studies are independent, so the document keeps them apart. */
export interface MsaStudy {
  bias: BiasInputs;
  linearity: LinearityInputs;
  stability: StabilityInputs;
}

const PAGE = "msa";

const EXAMPLE: MsaStudy = {
  bias: EXAMPLE_BIAS_INPUTS,
  linearity: EXAMPLE_LINEARITY_INPUTS,
  stability: EXAMPLE_STABILITY_INPUTS,
};

/** Holds all three studies' inputs so the page can be saved and loaded. */
export function MsaWorkspace() {
  const [study, setStudy] = useState<MsaStudy>(EXAMPLE);
  const [loaded, setLoaded] = useState<MsaStudy | null>(null);
  const [generation, setGeneration] = useState(0);

  const onBias = useCallback((bias: BiasInputs) => {
    setStudy((current) => ({ ...current, bias }));
  }, []);
  const onLinearity = useCallback((linearity: LinearityInputs) => {
    setStudy((current) => ({ ...current, linearity }));
  }, []);
  const onStability = useCallback((stability: StabilityInputs) => {
    setStudy((current) => ({ ...current, stability }));
  }, []);

  const onLoad = useCallback((inputs: MsaStudy) => {
    // Per study, so a file written before one of them existed restores the
    // parts it does have rather than being refused outright.
    const restored: MsaStudy = {
      bias: { ...EXAMPLE.bias, ...inputs.bias },
      linearity: { ...EXAMPLE.linearity, ...inputs.linearity },
      stability: { ...EXAMPLE.stability, ...inputs.stability },
    };
    setLoaded(restored);
    setStudy(restored);
    setGeneration((n) => n + 1);
  }, []);

  const start = loaded ?? EXAMPLE;

  return (
    <div className="flex flex-col gap-10">
      <StudyFileControls page={PAGE} inputs={study} onLoad={onLoad} />
      <BiasPanel
        key={`bias-${generation}`}
        initial={start.bias}
        onInputsChange={onBias}
      />
      <hr className="border-foreground/10" />
      <LinearityPanel
        key={`lin-${generation}`}
        initial={start.linearity}
        onInputsChange={onLinearity}
      />
      <hr className="border-foreground/10" />
      <StabilityPanel
        key={`stab-${generation}`}
        initial={start.stability}
        onInputsChange={onStability}
      />
    </div>
  );
}
