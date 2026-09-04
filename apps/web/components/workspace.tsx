"use client";

import { useCallback, useState } from "react";

import type { IngestColumn } from "@/lib/api-client";
import { UploadPanel } from "./upload-panel";
import { CapabilityDashboard } from "./capability-dashboard";
import { ControlChartPanel } from "./control-chart-panel";

/**
 * Holds the one piece of state the upload and the analysis share: the chosen
 * column. Keeping it here (rather than in a store) is enough while the app has
 * a single linear flow — upload, pick a column, analyse it.
 */
export function Workspace() {
  const [column, setColumn] = useState<IngestColumn | null>(null);
  // A counter, not a fingerprint of the data.
  //
  // The key used to be name + length + first value + last value, and two
  // different columns can share all four — the same column re-uploaded after an
  // edit that touched neither end of it does. **That collision was not reachable
  // in practice**, and saying so is the point of this note: UploadPanel clears
  // its selection before every request, so `column` passes through null and both
  // panels unmount on the way, whatever the key says. Measured, not argued — the
  // e2e test in smoke.spec.ts covering it passes against the old key too.
  //
  // The counter is kept anyway because it is the simpler thing to be right
  // about: it makes the reset a property of this component rather than a
  // consequence of how another one happens to sequence its state, and there is
  // no longer a fingerprint to reason about at all (T-0071).
  const [generation, setGeneration] = useState(0);
  const onSelect = useCallback((c: IngestColumn | null) => {
    setColumn(c);
    setGeneration((n) => n + 1);
  }, []);

  return (
    <div className="flex flex-col gap-10">
      <UploadPanel onSelect={onSelect} />
      {column && column.values.length > 0 && (
        <>
          <CapabilityDashboard key={`cap:${generation}`} column={column} />
          <ControlChartPanel key={`ctl:${generation}`} column={column} />
        </>
      )}
    </div>
  );
}
