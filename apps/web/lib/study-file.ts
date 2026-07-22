/**
 * Save and reload a study as a file the user owns.
 *
 * This is a *file format*, not persistence. Nothing is stored on a server,
 * nothing is held between requests, and capstat still keeps no data of yours —
 * the document goes to your disk through the browser's own download, and comes
 * back through a file picker. That is what makes it compatible with the
 * decision not to host anything (TASK.md T-0026).
 *
 * Two rules shape the format, and both are load-bearing:
 *
 * **Only inputs are stored, never results.** A file records what you typed —
 * the measurements, the limits, the options — and the numbers are recomputed
 * from the validated core when it is loaded. A document carrying saved results
 * could show figures this version of capstat would no longer produce, and there
 * would be nothing on screen to reveal it. So results are not merely omitted:
 * {@link parseStudyFile} drops anything else the file contains, which means a
 * hand-edited `results` block is ignored rather than displayed.
 *
 * **The version is checked, never guessed.** A document from a future version
 * is refused with a message that says so. Reading it optimistically would mean
 * silently discarding fields whose meaning we do not know.
 */

/** Bumped when the shape of a page's `inputs` changes incompatibly. */
export const STUDY_SCHEMA_VERSION = 1;

const FORMAT = "capstat-study";

export interface StudyFile<TInputs> {
  format: typeof FORMAT;
  schema_version: number;
  /** Which analysis page the inputs belong to; loading checks it. */
  page: string;
  /** ISO date, for the reader's benefit only — nothing keys off it. */
  saved: string;
  inputs: TInputs;
}

export type ParseResult<TInputs> =
  { ok: true; file: StudyFile<TInputs> } | { ok: false; reason: string };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Build the document for a page. Pass inputs only — results do not belong. */
export function buildStudyFile<TInputs>(
  page: string,
  inputs: TInputs,
  now: Date = new Date(),
): StudyFile<TInputs> {
  return {
    format: FORMAT,
    schema_version: STUDY_SCHEMA_VERSION,
    page,
    saved: now.toISOString().slice(0, 10),
    inputs,
  };
}

/**
 * Parse a document, refusing anything we cannot honestly read.
 *
 * `expectedPage` is checked because the inputs of one page mean nothing on
 * another: loading a Gage R&R grid into the capability form would either throw
 * or, worse, half-populate it.
 */
export function parseStudyFile<TInputs>(
  text: string,
  expectedPage: string,
): ParseResult<TInputs> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    return {
      ok: false,
      reason: "That file is not JSON, so it is not a saved study.",
    };
  }

  if (!isRecord(parsed) || parsed.format !== FORMAT) {
    return {
      ok: false,
      reason:
        "That file was not saved by capstat — it has no capstat-study marker.",
    };
  }

  const version = parsed.schema_version;
  if (
    typeof version !== "number" ||
    !Number.isInteger(version) ||
    version < 1
  ) {
    return {
      ok: false,
      reason: "That study file does not say which version it is.",
    };
  }
  if (version > STUDY_SCHEMA_VERSION) {
    return {
      ok: false,
      reason:
        `That study was saved by a newer capstat (format version ${version}; ` +
        `this one reads up to ${STUDY_SCHEMA_VERSION}). Loading it would mean ` +
        "quietly dropping fields whose meaning this version does not know.",
    };
  }

  if (parsed.page !== expectedPage) {
    return {
      ok: false,
      reason:
        `That study belongs to the "${String(parsed.page)}" page, and this is ` +
        `"${expectedPage}". Open it there instead.`,
    };
  }

  if (!isRecord(parsed.inputs)) {
    return { ok: false, reason: "That study file has no inputs to restore." };
  }

  // Rebuilt field by field rather than passed through: whatever else the
  // document contains -- a stale `results` block above all -- is dropped here,
  // not merely ignored downstream.
  return {
    ok: true,
    file: {
      format: FORMAT,
      schema_version: version,
      page: expectedPage,
      saved: typeof parsed.saved === "string" ? parsed.saved : "",
      inputs: parsed.inputs as TInputs,
    },
  };
}

/** Serialise for download: indented, because a user may well read it. */
export function serialiseStudyFile<TInputs>(file: StudyFile<TInputs>): string {
  return `${JSON.stringify(file, null, 2)}\n`;
}

/** A filename that sorts by date and says what it is. */
export function studyFileName(page: string, saved: string): string {
  return `capstat-${page}-${saved}.json`;
}
