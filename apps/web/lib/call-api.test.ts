import { describe, expect, it } from "vitest";

import { callApi } from "@/lib/call-api";

describe("callApi (T-0059)", () => {
  it("passes the data through when the call succeeds", async () => {
    const outcome = await callApi(
      async () => ({ data: { n: 3 }, error: undefined }),
      "Bias could not be computed.",
    );
    expect(outcome).toEqual({ ok: true, data: { n: 3 } });
  });

  it("prefers the API's own detail over the caller's fallback", async () => {
    const outcome = await callApi(
      async () => ({
        data: undefined,
        error: { detail: "lsl must be below usl" },
      }),
      "Capability could not be computed.",
    );
    expect(outcome).toEqual({ ok: false, message: "lsl must be below usl" });
  });

  it("falls back to the caller's wording when the error body says nothing useful", async () => {
    const outcome = await callApi(
      async () => ({ data: undefined, error: { something: "else" } }),
      "Capability could not be computed.",
    );
    expect(outcome).toEqual({
      ok: false,
      message: "Capability could not be computed.",
    });
  });

  it("treats a thrown request as unreachable, not as a computation failure", async () => {
    // The distinction matters to the reader: "the API said no" and "the API is
    // not there" call for different actions.
    const outcome = await callApi(async () => {
      throw new TypeError("fetch failed");
    }, "Capability could not be computed.");
    expect(outcome).toEqual({ ok: false, message: "Could not reach the API." });
  });

  it("lets a caller say more about being unreachable", async () => {
    // The upload panel is a user's first contact with the API, so it is the one
    // place where "is it running?" is worth saying. That wording had drifted
    // into a private copy of the whole error path; now it is an argument.
    const outcome = await callApi(
      async () => {
        throw new TypeError("fetch failed");
      },
      "Upload failed.",
      "Could not reach the API. Is it running on the configured URL?",
    );
    expect(outcome).toEqual({
      ok: false,
      message: "Could not reach the API. Is it running on the configured URL?",
    });
  });

  it("treats a 2xx with no body as a failure rather than as empty data", async () => {
    const outcome = await callApi(
      async () => ({ data: undefined, error: undefined }),
      "Bias could not be computed.",
    );
    expect(outcome).toEqual({
      ok: false,
      message: "Bias could not be computed.",
    });
  });
});
