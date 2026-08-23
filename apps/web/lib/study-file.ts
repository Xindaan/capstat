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

/**
 * A field in a loaded document was present but of the wrong type.
 *
 * Refused rather than coerced, and refused as a *whole document*: a study that
 * is half itself is worse than one that did not load, because nothing on screen
 * distinguishes a restored value from a substituted one. Absent fields are the
 * one tolerated case -- a file written before a later version added a section
 * restores the parts it does have (the MSA page depends on that) -- but a field
 * that *is* there and is not what it claims stops the load.
 *
 * The path is built on the way *out*: each reader that descends re-throws with
 * its own key in front, so a bad cell reports "grid.2.0.1" rather than "grid",
 * and the reader that wrote it never had to know where it sits.
 */
class DamagedInputs extends Error {
  constructor(
    readonly path: string,
    readonly expected: string,
  ) {
    super(`"${path}" should be ${expected}`);
  }

  under(prefix: string): DamagedInputs {
    return new DamagedInputs(
      this.path ? `${prefix}.${this.path}` : prefix,
      this.expected,
    );
  }
}

function refuse(path: string, expected: string): never {
  throw new DamagedInputs(path, expected);
}

function descend<T>(prefix: string, read: () => T): T {
  try {
    return read();
  } catch (error) {
    if (error instanceof DamagedInputs) throw error.under(prefix);
    throw error;
  }
}

function at(source: unknown, key: string): unknown {
  return isRecord(source) ? source[key] : undefined;
}

/** A string field, or the fallback when the document does not carry it. */
export function readText(
  source: unknown,
  key: string,
  fallback: string,
): string {
  const value = at(source, key);
  if (value === undefined) return fallback;
  if (typeof value !== "string") refuse(key, "text");
  return value;
}

/** A boolean field, or the fallback when absent. */
export function readFlag(
  source: unknown,
  key: string,
  fallback: boolean,
): boolean {
  const value = at(source, key);
  if (value === undefined) return fallback;
  if (typeof value !== "boolean") refuse(key, "true or false");
  return value;
}

/** A whole-number field, or the fallback when absent. */
export function readCount(
  source: unknown,
  key: string,
  fallback: number,
): number {
  const value = at(source, key);
  if (value === undefined) return fallback;
  if (typeof value !== "number" || !Number.isInteger(value)) {
    refuse(key, "a whole number");
  }
  return value;
}

/** A field restricted to a known set of words, or the fallback when absent. */
export function readChoice<T extends string>(
  source: unknown,
  key: string,
  allowed: readonly T[],
  fallback: T,
): T {
  const value = at(source, key);
  if (value === undefined) return fallback;
  if (
    typeof value !== "string" ||
    !(allowed as readonly string[]).includes(value)
  ) {
    refuse(key, `one of ${allowed.join(", ")}`);
  }
  return value as T;
}

/**
 * A list field, each entry read by `entry`.
 *
 * When the field is absent the caller's `fallback` stands in -- `[]` by
 * default, but a page whose empty state is unusable (a Gage R&R grid with no
 * cells) should pass its example instead, so an old file missing the field
 * restores something a user can work with rather than an empty table.
 */
export function readList<T>(
  source: unknown,
  key: string,
  entry: (item: unknown) => T,
  fallback: T[] = [],
): T[] {
  const value = at(source, key);
  if (value === undefined) return fallback;
  if (!Array.isArray(value)) refuse(key, "a list");
  return value.map((item, i) => descend(`${key}.${i}`, () => entry(item)));
}

/** A list that is itself an item of a list -- one more level of a grid. */
export function readItems<T>(value: unknown, entry: (item: unknown) => T): T[] {
  if (!Array.isArray(value)) refuse("", "a list");
  return value.map((item, i) => descend(String(i), () => entry(item)));
}

/** A string that is an item of a list rather than a field of a record. */
export function readTextItem(value: unknown): string {
  if (typeof value !== "string") refuse("", "text");
  return value;
}

/** Read a sub-record with its own reader, keeping the path prefix in faults. */
export function readSection<T>(
  source: unknown,
  key: string,
  read: (section: unknown) => T,
): T {
  const value = at(source, key);
  if (value !== undefined && !isRecord(value)) refuse(key, "a group of fields");
  return descend(key, () => read(value));
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
  readInputs?: (inputs: Record<string, unknown>) => TInputs,
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
  // not merely ignored downstream. The same applies *inside* `inputs` when the
  // page supplies a reader: without one, `inputs` was cast unchecked and a
  // hand-edited file could hand a number to something that expected a grid,
  // which reached the render as an unhandled TypeError (T-0055).
  let inputs: TInputs;
  try {
    inputs = readInputs
      ? readInputs(parsed.inputs)
      : (parsed.inputs as TInputs);
  } catch (error) {
    if (error instanceof DamagedInputs) {
      return {
        ok: false,
        reason:
          `That study file is damaged: ${error.message}. Nothing was ` +
          "loaded -- a study restored from half a file would look like a whole " +
          "one.",
      };
    }
    throw error;
  }

  return {
    ok: true,
    file: {
      format: FORMAT,
      schema_version: version,
      page: expectedPage,
      saved: typeof parsed.saved === "string" ? parsed.saved : "",
      inputs,
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
