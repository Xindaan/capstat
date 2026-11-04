"use client";

import { useId, type InputHTMLAttributes } from "react";

import {
  readCount,
  readDecimal,
  type NumberList,
  type Read,
} from "@/lib/numbers";

/**
 * Why a typed number cannot be used, or null when it can (or is empty).
 *
 * An empty field is not a format problem -- whether it is allowed is the
 * caller's business (optional limits, required counts) -- so it returns null
 * and the caller's own hint stays in charge.
 */
export function numberProblem(
  text: string,
  kind: "decimal" | "integer",
  bounds: { min?: number; max?: number } = {},
): string | null {
  if (text.trim() === "") return null;
  const read = kind === "integer" ? readCount(text, bounds) : readDecimal(text);
  return read.ok ? null : read.reason;
}

type PassThrough = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  "value" | "onChange" | "type" | "inputMode" | "min" | "max" | "step"
>;

/**
 * The one way a number is typed in this app.
 *
 * A text input, not `type="number"` (T-0100). A number input reads its text
 * through the browser's own locale: "3,29" became 329 in an English browser, a
 * German "5.000" became 5, a pasted Excel block collapsed into one number, and
 * the arrow keys and wheel stepped a measurement by 1. All of that is the
 * browser being helpful about a field whose values decide a verdict. A text
 * field has none of it: what is typed is what is read, by `lib/numbers`, in
 * every locale, and what cannot be read is said so beside the field (and to
 * assistive technology, through `aria-invalid` / `aria-describedby`).
 *
 * `inputMode` keeps the numeric keypad on a phone.
 */
export function NumericInput({
  value,
  onChange,
  kind = "decimal",
  min,
  max,
  showProblem = true,
  ...rest
}: PassThrough & {
  value: string;
  onChange: (value: string) => void;
  /** "integer" refuses fractions and the 5.000-or-5000 ambiguity. */
  kind?: "decimal" | "integer";
  min?: number;
  max?: number;
  /** Compact cells (a grid) show only the state; the panel explains. */
  showProblem?: boolean;
}) {
  const messageId = useId();
  const problem = numberProblem(value, kind, { min, max });
  return (
    <>
      <input
        {...rest}
        type="text"
        inputMode={kind === "integer" ? "numeric" : "decimal"}
        autoComplete="off"
        spellCheck={false}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-invalid={problem != null ? true : undefined}
        aria-describedby={
          problem != null && showProblem ? messageId : undefined
        }
        title={problem != null && !showProblem ? problem : rest.title}
      />
      {problem != null && showProblem && (
        <span
          id={messageId}
          role="note"
          className="max-w-56 text-[11px] leading-snug text-amber-600 dark:text-amber-400"
        >
          {problem}
        </span>
      )}
    </>
  );
}

/**
 * What the page made of a list of readings, said back to the person who typed
 * them: the count, and a decimal comma if one was read. A miscount is then
 * visible before any verdict is (it was the missing echo that let ten
 * decimal-comma readings become twenty, T-0100), and a refusal carries its
 * reason instead of a generic "need numeric readings".
 */
export function ReadingsNote({ read }: { read: Read<NumberList> }) {
  if (read.ok) {
    const n = read.value.values.length;
    return (
      <span className="text-xs text-muted" data-testid="readings-note">
        {n} {n === 1 ? "reading" : "readings"} read
        {read.value.decimalComma ? ", decimal comma" : ""}
      </span>
    );
  }
  if (read.empty) return null;
  return (
    <span
      role="note"
      className="max-w-xl text-xs text-amber-600 dark:text-amber-400"
    >
      {read.reason}
    </span>
  );
}
