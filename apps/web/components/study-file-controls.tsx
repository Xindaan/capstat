"use client";

import { useId, useRef, useState } from "react";

import {
  buildStudyFile,
  parseStudyFile,
  serialiseStudyFile,
  studyFileName,
} from "@/lib/study-file";
import { ErrorAlert } from "./error-alert";

export interface StudyFileControlsProps<TInputs> {
  /** The route this study belongs to; a file from another page is refused. */
  page: string;
  /** The current inputs. Results are never passed here, and never saved. */
  inputs: TInputs;
  onLoad: (inputs: TInputs) => void;
  /**
   * Turn a loaded document's `inputs` into this page's typed inputs, or throw
   * to refuse the file.
   *
   * Required, deliberately. `parseStudyFile` still accepts documents without a
   * reader because it is a general parser, but every page that mounts these
   * controls loads a file a user can hand-edit -- and an unchecked one used to
   * crash the page it was loaded into (T-0055). Making it a prop rather than an
   * option means a new page cannot forget it: it will not compile.
   */
  readInputs: (inputs: Record<string, unknown>) => TInputs;
}

/**
 * Save the study to a file, or load one back.
 *
 * Both directions go through the browser: a download for saving, a file picker
 * for loading. Nothing is uploaded, and capstat still holds nothing between
 * requests — the file belongs to the user, on their own disk.
 */
export function StudyFileControls<TInputs>({
  page,
  inputs,
  onLoad,
  readInputs,
}: StudyFileControlsProps<TInputs>) {
  const inputId = useId();
  const fileRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  const save = () => {
    setError(null);
    const file = buildStudyFile(page, inputs);
    const blob = new Blob([serialiseStudyFile(file)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = studyFileName(page, file.saved);
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const load = async (file: File) => {
    setError(null);
    let text: string;
    try {
      text = await file.text();
    } catch {
      setError("That file could not be read.");
      return;
    }
    const result = parseStudyFile<TInputs>(text, page, readInputs);
    if (!result.ok) {
      setError(result.reason);
      return;
    }
    onLoad(result.file.inputs);
  };

  return (
    <div className="flex flex-col gap-2" aria-label="Study file">
      <div className="no-print flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={save}
          className="h-9 rounded-lg border border-foreground/25 px-3 text-sm font-medium transition-opacity hover:opacity-80"
        >
          Save study
        </button>
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          className="h-9 rounded-lg border border-foreground/25 px-3 text-sm font-medium transition-opacity hover:opacity-80"
        >
          Load study
        </button>
        <span className="text-xs text-muted">
          A file on your disk — nothing is uploaded, and only your inputs are
          stored. The numbers are recomputed on load.
        </span>
        <input
          ref={fileRef}
          id={inputId}
          type="file"
          accept="application/json,.json"
          className="sr-only"
          aria-label="Load study file"
          onChange={(e) => {
            const chosen = e.target.files?.[0];
            // Clear first: picking the same file twice must fire again.
            e.target.value = "";
            if (chosen) void load(chosen);
          }}
        />
      </div>
      {error && <ErrorAlert message={error} />}
    </div>
  );
}
