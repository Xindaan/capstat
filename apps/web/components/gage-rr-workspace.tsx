"use client";

import { useCallback, useState } from "react";

import {
  EXAMPLE_GAGE_RR_INPUTS,
  GageRRPanel,
  type GageRRInputs,
} from "./gage-rr-panel";
import { StudyFileControls } from "./study-file-controls";
import {
  readChoice,
  readCount,
  readItems,
  readList,
  readText,
  readTextItem,
} from "@/lib/study-file";

const PAGE = "gage-rr";

/**
 * Turn a loaded document's `inputs` into typed inputs, or refuse it.
 *
 * Without this the object was cast unchecked and handed to the panel, so a
 * hand-edited file with `"grid": 1` reached `grid.map` and took the page down
 * with an unhandled TypeError (T-0055).
 */
function readGageRRInputs(inputs: Record<string, unknown>): GageRRInputs {
  return {
    parts: readCount(inputs, "parts", EXAMPLE_GAGE_RR_INPUTS.parts),
    operators: readCount(inputs, "operators", EXAMPLE_GAGE_RR_INPUTS.operators),
    trials: readCount(inputs, "trials", EXAMPLE_GAGE_RR_INPUTS.trials),
    grid: readList(
      inputs,
      "grid",
      (part) =>
        readItems(part, (operator) => readItems(operator, readTextItem)),
      EXAMPLE_GAGE_RR_INPUTS.grid,
    ),
    method: readChoice(
      inputs,
      "method",
      ["anova", "average_range"] as const,
      EXAMPLE_GAGE_RR_INPUTS.method,
    ),
    tolerance: readText(inputs, "tolerance", EXAMPLE_GAGE_RR_INPUTS.tolerance),
  };
}

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
      <StudyFileControls
        page={PAGE}
        inputs={study}
        onLoad={onLoad}
        readInputs={readGageRRInputs}
      />
      <GageRRPanel
        key={generation}
        initial={loaded ?? EXAMPLE_GAGE_RR_INPUTS}
        onInputsChange={onInputsChange}
      />
    </div>
  );
}
