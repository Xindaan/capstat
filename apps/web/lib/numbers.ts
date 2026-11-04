/**
 * Reading numbers the user typed, pasted or copied out of a spreadsheet.
 *
 * One module for every typed number in the app, because the failure it exists
 * for is the same wherever it happens (T-0100): a decimal comma that is read as
 * something else, silently. `<input type="number">` followed the browser's own
 * locale ("3,29" became 329 in an English browser, "5.000" became 5 in a German
 * one), and the readings textareas split "36,1" into 36 and 1 -- ten readings
 * turned into twenty and a verdict still came back. The CSV upload got this
 * right in T-0067; these are the typed paths.
 *
 * ## The accepted formats
 *
 * A number is an optional sign, digits with at most ONE decimal mark -- a point
 * or a comma, both mean the decimal mark -- and an optional exponent:
 *
 *     3.29   3,29   -0.5   +.5   5.   1e-3   2,5E2
 *
 * Not accepted, and refused with a message rather than guessed at:
 *
 * - **Thousands separators** (`1.234,5`, `1,234,567`, `1 234`). capstat never
 *   asks for a quantity big enough to need one, and "1.234" is 1.234 here, so a
 *   reader who meant 1234 must be told rather than obeyed. Whole-number fields
 *   (sample size, lot size, counts) are stricter still: `5.000` and `1,234`
 *   could be 5 or 5000, so they are refused.
 * - `NaN`, `Infinity`, hex (`0x10`), `1_000`, anything else `Number()` would
 *   have taken: the old `Number(text)` accepted `Infinity` as a reading.
 *
 * A U+2212 minus sign (Word, some spreadsheets) is read as an ordinary minus.
 *
 * ## Lists of readings
 *
 * Readings are separated by whitespace (spaces, tabs, new lines), semicolons or
 * commas. The comma is the hard case, because it is both a separator and a
 * decimal mark; it is decided like this:
 *
 * - a comma with a digit on **both** sides and no space (`36,1`) is a decimal
 *   comma. Every token may then hold at most one, and the readings must be
 *   separated by whitespace or semicolons (`36,1 35,9`, `36,1;35,9`);
 * - any other comma (`1, 2`, `1 ,2`, a trailing one) is a separator;
 * - a text with BOTH kinds (`36,1, 35,9`) or a token with several digit-flanked
 *   commas (`1,2,3`, `10.1,10.2`) could be read two ways, so it is refused.
 *
 * The rule never invents data: a text is either read exactly as written or
 * refused with the reason.
 */

export type Read<T> =
  | { ok: true; value: T }
  | {
      ok: false;
      reason: string;
      /** True when there was simply nothing to read (an empty field). */
      empty?: boolean;
    };

const NUMBER = /^[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][+-]?\d+)?$/;
/** 1.234  12,345  (a single mark, exactly three digits, a short head). */
const THOUSANDS_OR_DECIMAL = /^[+-]?\d{1,3}[.,]\d{3}$/;
/** Digit groups with separators between them: 1.234,5  1,234,567  1 234. */
const GROUPED = /^[+-]?\d{1,3}(?:[.,\s  ]\d{3})+(?:[.,]\d+)?$/;

function normalise(text: string): string {
  return text.replace(/−/g, "-").trim();
}

const EXAMPLE = "for example 3.29 or 3,29";

/** One number, in the formats described at the top of this file. */
export function readDecimal(text: string): Read<number> {
  const t = normalise(text);
  if (t === "") return { ok: false, empty: true, reason: "Enter a number." };
  if (!NUMBER.test(t)) {
    if (GROUPED.test(t)) {
      return {
        ok: false,
        reason: `"${t}" has a thousands separator. Write the number without one, ${EXAMPLE}.`,
      };
    }
    return {
      ok: false,
      reason: `"${t}" is not a number. Use digits with one decimal point or comma, ${EXAMPLE}.`,
    };
  }
  const value = Number(t.replace(",", "."));
  if (!Number.isFinite(value)) {
    return { ok: false, reason: `"${t}" is too large to use.` };
  }
  return { ok: true, value };
}

/**
 * A whole number, optionally bounded.
 *
 * Stricter than `readDecimal` about the one shape that is ambiguous for a
 * count: a single point or comma followed by exactly three digits (`5.000`).
 * A German reader means 5000, an English one 5; either guess silently designs
 * the wrong plan.
 */
export function readCount(
  text: string,
  { min = 0, max }: { min?: number; max?: number } = {},
): Read<number> {
  const t = normalise(text);
  if (THOUSANDS_OR_DECIMAL.test(t)) {
    const asDecimal = Number(t.replace(",", "."));
    const asThousands = Number(t.replace(/[.,]/, ""));
    return {
      ok: false,
      reason: `"${t}" could mean ${asDecimal} or ${asThousands}. Write the whole number without a separator.`,
    };
  }
  const read = readDecimal(t);
  if (!read.ok) return read;
  if (!Number.isInteger(read.value)) {
    return { ok: false, reason: `"${t}" must be a whole number.` };
  }
  if (read.value < min) {
    return { ok: false, reason: `"${t}" must be at least ${min}.` };
  }
  if (max !== undefined && read.value > max) {
    return { ok: false, reason: `"${t}" must be at most ${max}.` };
  }
  return read;
}

export interface NumberList {
  values: number[];
  /** True when the text used decimal commas (so the page can say so). */
  decimalComma: boolean;
}

const DIGIT_COMMA_DIGIT = /(?<=\d),(?=\d)/g;

/** A list of readings; see "Lists of readings" at the top of this file. */
export function readNumberList(text: string): Read<NumberList> {
  // (A typographic minus is handled per token, by readDecimal.)
  const src = text;
  if (src.trim() === "") {
    return { ok: false, empty: true, reason: "Enter at least one reading." };
  }
  const total = (src.match(/,/g) ?? []).length;
  const decimal = (src.match(DIGIT_COMMA_DIGIT) ?? []).length;
  const separators = total - decimal;

  if (decimal > 0 && separators > 0) {
    return {
      ok: false,
      reason:
        "This mixes decimal commas (like 36,1) with commas between readings, " +
        "so it could be read two ways. Separate the readings with spaces, " +
        "semicolons or new lines and use commas only as decimal marks.",
    };
  }

  const tokens = (decimal > 0 ? src.split(/[\s;]+/) : src.split(/[\s,;]+/))
    .map((t) => t.trim())
    .filter((t) => t !== "");

  const values: number[] = [];
  for (const token of tokens) {
    if (
      (token.match(/,/g) ?? []).length > 1 ||
      (decimal > 0 && /[.].*,|,.*[.]/.test(token))
    ) {
      return {
        ok: false,
        reason:
          `"${token}" could be one number or several. Separate readings with ` +
          "spaces, semicolons or new lines, and use one comma per number at most.",
      };
    }
    const read = readDecimal(token);
    if (!read.ok) return read;
    values.push(read.value);
  }
  return { ok: true, value: { values, decimalComma: decimal > 0 } };
}

export type Block = string[][];

/**
 * A block of cells copied from a spreadsheet: rows on new lines, columns on
 * tabs. Returns null for text with neither (a single value), which a text
 * input takes in unaided.
 *
 * Every cell is checked with `readDecimal` and the whole block is refused if any
 * fails, naming the cell: a pasted header row or a part-number column would
 * otherwise land in the study as invalid cells nobody asked for.
 */
export function readPastedBlock(text: string): Read<Block> | null {
  // (A "\r" left at the end of a row is whitespace to readDecimal.)
  const trimmed = text.replace(/\n+$/, "");
  if (!/[\t\n]/.test(trimmed)) return null;
  const rows = trimmed.split("\n").map((line) => line.split("\t"));
  for (const [r, row] of rows.entries()) {
    for (const [c, cell] of row.entries()) {
      const read = readDecimal(cell);
      if (!read.ok) {
        return {
          ok: false,
          reason: `Nothing was pasted: row ${r + 1}, column ${c + 1} (${JSON.stringify(cell.trim())}) is not a measurement. ${read.reason}`,
        };
      }
    }
  }
  return {
    ok: true,
    value: rows.map((row) => row.map((cell) => normalise(cell))),
  };
}
