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
  const onSelect = useCallback((c: IngestColumn | null) => setColumn(c), []);

  // Remount the analyses (resetting them) when the underlying data changes,
  // even across two files that happen to share a column name.
  const sig =
    column &&
    `${column.name}:${column.values.length}:${column.values[0]}:${column.values.at(-1)}`;

  return (
    <div className="flex flex-col gap-10">
      <UploadPanel onSelect={onSelect} />
      {column && column.values.length > 0 && (
        <>
          <CapabilityDashboard key={`cap:${sig}`} column={column} />
          <ControlChartPanel key={`ctl:${sig}`} column={column} />
        </>
      )}
    </div>
  );
}
