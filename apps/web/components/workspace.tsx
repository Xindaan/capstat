"use client";

import { useCallback, useState } from "react";

import type { IngestColumn } from "@/lib/api-client";
import {
  MAX_SUBGROUP_SIZE,
  intoSubgroups,
  parseSubgroupSize,
} from "@/lib/subgroups";
import { UploadPanel } from "./upload-panel";
import { CapabilityDashboard } from "./capability-dashboard";
import { ControlChartPanel } from "./control-chart-panel";

/**
 * Holds what the upload and the analyses share: the chosen column, and how it
 * is grouped.
 *
 * The subgroup size lives here rather than in either panel because both need
 * the same answer -- a capability report and a control chart computed on
 * different groupings of one column would be two studies presented as one.
 */
export function Workspace() {
  const [column, setColumn] = useState<IngestColumn | null>(null);
  const [sizeText, setSizeText] = useState("1");
  // A counter, not a fingerprint of the values: it makes the reset a property
  // of this component rather than a consequence of how UploadPanel sequences
  // its state (T-0071).
  const [generation, setGeneration] = useState(0);

  const onSelect = useCallback((c: IngestColumn | null) => {
    setColumn(c);
    setGeneration((n) => n + 1);
  }, []);

  const size = parseSubgroupSize(sizeText);
  const values = column?.values ?? [];
  const grouping = size == null ? null : intoSubgroups(values, size);
  const usable =
    size != null && (size === 1 || grouping!.subgroups.length >= 2);

  return (
    <div className="flex flex-col gap-10">
      <UploadPanel onSelect={onSelect} />
      {column && column.values.length > 0 && (
        <>
          <SubgroupControl
            value={sizeText}
            onChange={setSizeText}
            size={size}
            total={values.length}
            complete={grouping?.subgroups.length ?? 0}
            leftover={grouping?.leftover.length ?? 0}
          />
          {usable && (
            <>
              <CapabilityDashboard
                key={`cap:${generation}:${size}`}
                column={column}
                subgroupSize={size!}
              />
              <ControlChartPanel
                key={`ctl:${generation}:${size}`}
                column={column}
                subgroupSize={size!}
              />
            </>
          )}
        </>
      )}
    </div>
  );
}

function SubgroupControl({
  value,
  onChange,
  size,
  total,
  complete,
  leftover,
}: {
  value: string;
  onChange: (v: string) => void;
  size: number | null;
  total: number;
  complete: number;
  leftover: number;
}) {
  const tooFew = size != null && size > 1 && complete < 2;
  return (
    <section
      className="flex flex-col gap-2 rounded-lg border border-foreground/15 p-4"
      aria-label="Subgrouping"
    >
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs uppercase tracking-wide text-muted">
            Subgroup size
          </span>
          <input
            type="number"
            min={1}
            max={MAX_SUBGROUP_SIZE}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            aria-label="Subgroup size"
            className="h-10 w-24 rounded-lg border border-foreground/20 bg-transparent px-3 text-sm tabular-nums focus:border-foreground/50 focus:outline-none"
          />
        </label>
        <p className="max-w-xl text-xs text-muted">
          {size === 1
            ? "1 — individual measurements. The short-term sigma comes from the moving range, which assumes the rows are in time order, and Cp/Cpk rest on that assumption rather than on subgroup structure."
            : size == null
              ? `Enter a whole number from 1 to ${MAX_SUBGROUP_SIZE}.`
              : `Consecutive rows are grouped ${size} at a time, in file order: ${complete} subgroup${complete === 1 ? "" : "s"} from ${total} measurements. This is what makes the within-subgroup sigma — and therefore Cp and Cpk — mean something.`}
        </p>
      </div>
      {leftover > 0 && (
        <p
          data-testid="subgroup-leftover"
          className="rounded border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-800 dark:text-amber-200/90"
        >
          {total} measurements do not divide into subgroups of {size}: the last{" "}
          {leftover} {leftover === 1 ? "value is" : "values are"} not part of
          any subgroup and take no part in the analysis below. Drop them, or
          pick a size that divides the column.
        </p>
      )}
      {tooFew && (
        <p className="rounded border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-800 dark:text-amber-200/90">
          A subgroup size of {size} leaves fewer than two complete subgroups,
          which is not a study. Pick a smaller size.
        </p>
      )}
    </section>
  );
}
