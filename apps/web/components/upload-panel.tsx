"use client";

import { useCallback, useId, useRef, useState } from "react";

import { ingestFile, type IngestColumn, type IngestResponse } from "@/lib/api-client";

type Status =
  | { kind: "idle" }
  | { kind: "uploading"; filename: string }
  | { kind: "done"; filename: string; result: IngestResponse }
  | { kind: "error"; message: string };

const ACCEPT = ".csv,.xlsx,.xlsm";

const numberFormat = new Intl.NumberFormat(undefined, {
  maximumSignificantDigits: 6,
});

/** Min / max / mean of a column's kept values, for a quick sanity preview. */
function columnStats(values: number[]): { min: number; max: number; mean: number } {
  let min = values[0];
  let max = values[0];
  let sum = 0;
  for (const v of values) {
    if (v < min) min = v;
    if (v > max) max = v;
    sum += v;
  }
  return { min, max, mean: sum / values.length };
}

/** Turn an openapi-fetch error body into a single human-readable line. */
function describeError(error: unknown): string {
  if (error && typeof error === "object" && "detail" in error) {
    const detail = (error as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const first = detail[0] as { msg?: string } | undefined;
      if (first?.msg) return first.msg;
    }
  }
  return "The file could not be ingested.";
}

export function UploadPanel() {
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const [selected, setSelected] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const inputId = useId();

  const upload = useCallback(async (file: File) => {
    setSelected(null);
    setStatus({ kind: "uploading", filename: file.name });
    try {
      const { data, error } = await ingestFile(file);
      if (error || !data) {
        setStatus({ kind: "error", message: describeError(error) });
        return;
      }
      setStatus({ kind: "done", filename: file.name, result: data });
      // Preselect the first numeric column so the panel is immediately useful.
      setSelected(data.columns[0]?.name ?? null);
    } catch {
      setStatus({
        kind: "error",
        message:
          "Could not reach the API. Is it running on the configured URL?",
      });
    }
  }, []);

  const onFiles = useCallback(
    (files: FileList | null) => {
      const file = files?.[0];
      if (file) void upload(file);
    },
    [upload],
  );

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      setDragging(false);
      onFiles(event.dataTransfer.files);
    },
    [onFiles],
  );

  const reset = useCallback(() => {
    setStatus({ kind: "idle" });
    setSelected(null);
    if (inputRef.current) inputRef.current.value = "";
  }, []);

  const busy = status.kind === "uploading";
  const result = status.kind === "done" ? status.result : null;
  const selectedColumn =
    result?.columns.find((c) => c.name === selected) ?? null;

  return (
    <section className="flex flex-col gap-6" aria-label="Data upload">
      {/* Dropzone */}
      <label
        htmlFor={inputId}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={[
          "flex cursor-pointer flex-col items-center justify-center gap-2",
          "rounded-xl border-2 border-dashed px-6 py-12 text-center transition-colors",
          dragging
            ? "border-blue-500 bg-blue-500/5"
            : "border-foreground/20 hover:border-foreground/40",
          busy ? "pointer-events-none opacity-60" : "",
        ].join(" ")}
      >
        <input
          id={inputId}
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          className="sr-only"
          disabled={busy}
          onChange={(e) => onFiles(e.target.files)}
        />
        <span className="text-base font-medium">
          {busy
            ? `Ingesting ${status.filename}…`
            : "Drop a CSV or Excel file, or click to browse"}
        </span>
        <span className="text-sm text-foreground/50">
          .csv, .xlsx or .xlsm — parsed locally by your API, nothing is stored
        </span>
      </label>

      {/* Error */}
      {status.kind === "error" && (
        <div
          role="alert"
          className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-700 dark:text-red-300"
        >
          {status.message}
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="flex flex-col gap-5">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-sm font-medium text-foreground/70">
              Parsed{" "}
              <span className="font-mono text-foreground">
                {status.kind === "done" ? status.filename : ""}
              </span>{" "}
              — {result.n_rows} row{result.n_rows === 1 ? "" : "s"},{" "}
              {result.columns.length} numeric column
              {result.columns.length === 1 ? "" : "s"}
            </h2>
            <button
              type="button"
              onClick={reset}
              className="text-sm text-foreground/50 underline underline-offset-4 hover:text-foreground"
            >
              Upload another file
            </button>
          </div>

          {/* Ingestion warnings — the whole point of surfacing ingestion. */}
          {result.warnings.length > 0 && (
            <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3">
              <p className="mb-1 text-sm font-medium text-amber-700 dark:text-amber-300">
                Ingestion notes
              </p>
              <ul className="list-disc space-y-1 pl-5 text-sm text-amber-800 dark:text-amber-200/90">
                {result.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
              {result.ignored_columns.length > 0 && (
                <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs text-amber-800/80 dark:text-amber-200/70">
                  <span>Ignored:</span>
                  {result.ignored_columns.map((name) => (
                    <span
                      key={name}
                      className="rounded bg-amber-500/20 px-1.5 py-0.5 font-mono"
                    >
                      {name}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Column selection */}
          {result.columns.length > 0 ? (
            <fieldset className="flex flex-col gap-2">
              <legend className="mb-1 text-sm font-medium text-foreground/70">
                Choose the column to analyse
              </legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {result.columns.map((col) => (
                  <ColumnOption
                    key={col.name}
                    column={col}
                    checked={selected === col.name}
                    onSelect={() => setSelected(col.name)}
                  />
                ))}
              </div>
            </fieldset>
          ) : (
            <p className="text-sm text-foreground/60">
              No numeric columns were found in this file.
            </p>
          )}

          {selectedColumn && <ColumnSummary column={selectedColumn} />}
        </div>
      )}
    </section>
  );
}

function ColumnOption({
  column,
  checked,
  onSelect,
}: {
  column: IngestColumn;
  checked: boolean;
  onSelect: () => void;
}) {
  return (
    <label
      className={[
        "flex cursor-pointer items-center justify-between gap-3 rounded-lg border px-3 py-2.5 transition-colors",
        checked
          ? "border-blue-500 bg-blue-500/10"
          : "border-foreground/15 hover:border-foreground/30",
      ].join(" ")}
    >
      <span className="flex items-center gap-2.5 truncate">
        <input
          type="radio"
          name="analysis-column"
          className="accent-blue-500"
          checked={checked}
          onChange={onSelect}
        />
        <span className="truncate font-mono text-sm">{column.name}</span>
      </span>
      <span className="flex shrink-0 items-center gap-2 text-xs text-foreground/50">
        <span>{column.values.length} values</span>
        {column.dropped_missing > 0 && (
          <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-amber-700 dark:text-amber-300">
            −{column.dropped_missing}
          </span>
        )}
      </span>
    </label>
  );
}

function ColumnSummary({ column }: { column: IngestColumn }) {
  if (column.values.length === 0) {
    return (
      <p className="text-sm text-foreground/60">
        Column{" "}
        <span className="font-mono">{column.name}</span> has no usable values.
      </p>
    );
  }
  const { min, max, mean } = columnStats(column.values);
  return (
    <div className="rounded-lg border border-foreground/15 p-4">
      <p className="mb-3 text-sm font-medium">
        <span className="font-mono">{column.name}</span>{" "}
        <span className="text-foreground/50">— selected</span>
      </p>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-4">
        <Stat label="n" value={String(column.values.length)} />
        <Stat label="min" value={numberFormat.format(min)} />
        <Stat label="max" value={numberFormat.format(max)} />
        <Stat label="mean" value={numberFormat.format(mean)} />
      </dl>
      <p className="mt-3 text-xs text-foreground/50">
        Ready for the capability report and control charts — coming in the next
        increment.
      </p>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <dt className="text-xs uppercase tracking-wide text-foreground/40">
        {label}
      </dt>
      <dd className="font-mono tabular-nums">{value}</dd>
    </div>
  );
}
