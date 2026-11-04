import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { checkRequest, type RequestLike } from "./check-request";
import type { OpenApiSpec } from "./openapi-contract";

const spec = JSON.parse(
  readFileSync(
    fileURLToPath(new URL("../../../api/openapi.json", import.meta.url)),
    "utf8",
  ),
) as OpenApiSpec;

const API = "http://127.0.0.1:8000";

function request(
  url: string,
  method: string,
  body: unknown = undefined,
  contentType = "application/json",
): RequestLike {
  const raw =
    body === undefined
      ? null
      : typeof body === "string"
        ? body
        : JSON.stringify(body);
  return {
    url: () => url,
    method: () => method,
    headers: (): Record<string, string> =>
      raw === null ? {} : { "content-type": contentType },
    postData: () => raw,
  };
}

const PLAN = { sample_size: 144, acceptance_number: 4, lot_size: 5000 };

describe("checkRequest", () => {
  it("passes a conforming API request", () => {
    const ok = request(`${API}/compute/acceptance-sampling/inspect`, "POST", {
      plan: PLAN,
      defectives: 2,
    });
    expect(checkRequest(spec, API, ok)).toBeNull();
  });

  it("reports the request the API would have refused", () => {
    const bad = request(`${API}/compute/acceptance-sampling/inspect`, "POST", {
      plan: { ...PLAN, rejection_number: 5 },
      defectives: 2,
    });
    expect(checkRequest(spec, API, bad)).toEqual({
      request: "POST /compute/acceptance-sampling/inspect",
      problems: [
        "$.plan.rejection_number: extra field not permitted (additionalProperties: false)",
      ],
    });
  });

  it("ignores requests that are not to the API", () => {
    const page = request("http://localhost:3104/gage-rr", "GET");
    const other = request("http://localhost:3104/compute/nonsense", "POST", {});
    expect(checkRequest(spec, API, page)).toBeNull();
    expect(checkRequest(spec, API, other)).toBeNull();
  });

  it("reports an unknown path on the API's origin", () => {
    const typo = request(
      `${API}/compute/acceptance-sampling/inspekt`,
      "POST",
      {},
    );
    expect(checkRequest(spec, API, typo)?.problems).toEqual([
      "$: POST /compute/acceptance-sampling/inspekt is not an operation in openapi.json",
    ]);
  });

  it("reports a body that is not JSON", () => {
    const broken = request(
      `${API}/compute/acceptance-sampling/inspect`,
      "POST",
      "{not json",
    );
    expect(checkRequest(spec, API, broken)?.problems).toEqual([
      "$: body is not valid JSON",
    ]);
  });

  it("treats a missing body on a body endpoint as a break", () => {
    const empty = request(`${API}/compute/acceptance-sampling/inspect`, "POST");
    expect(checkRequest(spec, API, empty)?.problems).toEqual([
      "$: POST /compute/acceptance-sampling/inspect needs a body",
    ]);
  });

  it("treats an empty body string like no body at all", () => {
    const empty = request(
      `${API}/compute/acceptance-sampling/inspect`,
      "POST",
      "",
    );
    expect(checkRequest(spec, API, empty)?.problems).toEqual([
      "$: POST /compute/acceptance-sampling/inspect needs a body",
    ]);
  });

  it("accepts an upload without parsing its parts", () => {
    const upload = request(
      `${API}/ingest`,
      "POST",
      "--x\r\ncontent-disposition: form-data; name=file\r\n\r\n1\r\n--x--",
      "multipart/form-data; boundary=x",
    );
    expect(checkRequest(spec, API, upload)).toBeNull();
  });
});
