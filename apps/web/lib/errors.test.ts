import { describe, expect, it } from "vitest";

import { describeApiError } from "@/lib/errors";

describe("describeApiError", () => {
  it("returns a string detail verbatim (our HTTPExceptions)", () => {
    expect(describeApiError({ detail: "File too large." }, "fallback")).toBe(
      "File too large.",
    );
  });

  it("pulls the first message out of a validation-error array", () => {
    const body = { detail: [{ msg: "field required", loc: ["body", "x"] }] };
    expect(describeApiError(body, "fallback")).toBe("field required");
  });

  it("falls back for a network error (no body)", () => {
    expect(describeApiError(undefined, "Could not reach the API.")).toBe(
      "Could not reach the API.",
    );
  });

  it("falls back for an unexpected shape", () => {
    expect(describeApiError({ detail: 42 }, "fallback")).toBe("fallback");
    expect(describeApiError({ other: "x" }, "fallback")).toBe("fallback");
  });
});
