"use client";

import { useCallback, useState } from "react";

import {
  EXAMPLE_GAGE_RR_INPUTS,
  GageRRPanel,
  type GageRRInputs,
} from "./gage-rr-panel";
import { StudyFileControls } from "./study-file-controls";

const PAGE = "gage-rr";

/** Holds the page's inputs so a Gage R&R study can be saved and loaded. */
export function GageRRWorkspace() {
  const [study, setStudy] = useState<GageRRInputs>(EXAMPLE_GAGE_RR_INPUTS);
  const [loaded, setLoaded] = useState<GageRRInputs | null>(null);
  const [generation, setGeneration] = useState(0);

  const onInputsChange = useCallback((inputs: GageRRInputs) => {
    setStudy(inputs);
  }, []);

  const onLoad = useCallback((inputs: GageRRInputs) => {
    const restored = { ...EXAMPLE_GAGE_RR_INPUTS, ...inputs };
    setLoaded(restored);
    setStudy(restored);
    setGeneration((n) => n + 1);
  }, []);

  return (
    <div className="flex flex-col gap-8">
      <StudyFileControls page={PAGE} inputs={study} onLoad={onLoad} />
      <GageRRPanel
        key={generation}
        initial={loaded ?? EXAMPLE_GAGE_RR_INPUTS}
        onInputsChange={onInputsChange}
      />
    </div>
  );
}
