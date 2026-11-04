import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import {
  unsupportedKeywords,
  validate,
  validateRequest,
  type Json,
  type OpenApiSpec,
} from "./openapi-contract";

const real = JSON.parse(
  readFileSync(
    fileURLToPath(new URL("../../../api/openapi.json", import.meta.url)),
    "utf8",
  ),
) as OpenApiSpec;

/** The messages of every violation, "path: message", for readable asserts. */
function messages(
  method: string,
  path: string,
  body: Json | undefined,
  contentType: string | undefined = "application/json",
): string[] {
  return validateRequest(real, method, path, contentType, body).map(
    (v) => `${v.path}: ${v.message}`,
  );
}

const INSPECT = "/compute/acceptance-sampling/inspect";

describe("against the real openapi.json", () => {
  it("understands every keyword a request body schema uses", () => {
    // If this fails, openapi.json grew a constraint the validator would let
    // through unchecked. Teach the validator the keyword (and test it).
    expect(unsupportedKeywords(real)).toEqual([]);
  });

  it("accepts the body the lot-decision call is meant to send", () => {
    expect(
      messages("POST", INSPECT, {
        plan: { sample_size: 144, acceptance_number: 4, lot_size: 5000 },
        defectives: 2,
        model: "binomial",
      }),
    ).toEqual([]);
  });

  it("refuses the body T-0099 shipped: the report's plan, with rejection_number", () => {
    expect(
      messages("POST", INSPECT, {
        plan: {
          sample_size: 144,
          acceptance_number: 4,
          lot_size: 5000,
          rejection_number: 5,
        },
        defectives: 2,
        model: "binomial",
      }),
    ).toEqual([
      "$.plan.rejection_number: extra field not permitted (additionalProperties: false)",
    ]);
  });

  it("refuses a missing required field, a wrong type and a bound", () => {
    expect(
      messages("POST", INSPECT, { plan: { sample_size: 144 }, defectives: 2 }),
    ).toEqual(['$.plan: missing required field "acceptance_number"']);
    expect(
      messages("POST", INSPECT, {
        plan: { sample_size: 144, acceptance_number: 4 },
        defectives: "2",
      }),
    ).toEqual(["$.defectives: expected integer, got string"]);
    expect(
      messages("POST", INSPECT, {
        plan: { sample_size: 0, acceptance_number: 4 },
        defectives: -1,
      }),
    ).toEqual([
      "$.plan.sample_size: 0 is below the minimum 1",
      "$.defectives: -1 is below the minimum 0",
    ]);
  });

  it("refuses a fractional value for an integer field", () => {
    expect(
      messages("POST", INSPECT, {
        plan: { sample_size: 144.5, acceptance_number: 4 },
        defectives: 2,
      }),
    ).toEqual(["$.plan.sample_size: expected integer, got number"]);
  });

  it("refuses a value outside an enum", () => {
    expect(
      messages("POST", INSPECT, {
        plan: { sample_size: 144, acceptance_number: 4 },
        defectives: 2,
        model: "normal",
      }),
    ).toHaveLength(1);
  });

  it("accepts null where the schema allows it and refuses it elsewhere", () => {
    const base = { sample_size: 144, acceptance_number: 4 };
    expect(
      messages("POST", INSPECT, {
        plan: { ...base, lot_size: null },
        defectives: 2,
      }),
    ).toEqual([]);
    expect(
      messages("POST", INSPECT, {
        plan: { ...base, sample_size: null },
        defectives: 2,
      }),
    ).toHaveLength(1);
  });

  it("refuses a request to a path or method the API does not have", () => {
    expect(messages("POST", "/compute/nonsense", {})).toEqual([
      "$: POST /compute/nonsense is not an operation in openapi.json",
    ]);
    expect(messages("GET", INSPECT, undefined)).toEqual([
      `$: GET ${INSPECT} is not an operation in openapi.json`,
    ]);
  });

  it("refuses a missing body, an unexpected body and a wrong content type", () => {
    expect(messages("POST", INSPECT, undefined)).toEqual([
      `$: POST ${INSPECT} needs a body`,
    ]);
    expect(messages("GET", "/health", {})).toEqual([
      "$: GET /health takes no body",
    ]);
    expect(messages("GET", "/health", undefined)).toEqual([]);
    expect(messages("POST", INSPECT, {}, "text/plain").join(" ")).toContain(
      "does not accept text/plain",
    );
  });

  it("checks that an upload has a body but does not parse the file", () => {
    expect(
      messages("POST", "/ingest", "binary", "multipart/form-data; boundary=x"),
    ).toEqual([]);
    expect(messages("POST", "/ingest", undefined)).toEqual([
      "$: POST /ingest needs a body",
    ]);
  });
});

describe("responses the page feeds back as requests", () => {
  // The T-0099 class: an output object passed on as an input. Hand-written e2e
  // mocks only contain the keys their author remembered, so a key the real
  // response gains (like `rejection_number`) never reaches the contract check.
  // The pairs the app really chains are compared by their schemas instead.
  const members = (name: string) => {
    const schema = real.components.schemas[name];
    return Object.keys(schema.properties ?? {}).sort();
  };

  it("the sampling plan: only the derived field is extra", () => {
    const extra = members("SamplingPlanOut").filter(
      (k) => !members("SamplingPlanIn").includes(k),
    );
    // Panels must pick fields by name (asPlanInput) -- this is the one extra.
    expect(extra).toEqual(["rejection_number"]);
  });

  it("the control limits go back unchanged", () => {
    // nelsonRules(points, limits) sends the chart's limits as they came.
    expect(members("ControlLimitsOut")).toEqual(members("ControlLimitsIn"));
  });
});

describe("validate on small schemas", () => {
  const spec = { paths: {}, components: { schemas: {} } } as OpenApiSpec;
  const run = (schema: Parameters<typeof validate>[1], value: Json) =>
    validate(spec, schema, value).map((v) => v.message);

  it("enforces enum and const", () => {
    expect(run({ enum: ["a", "b"] }, "c")).toHaveLength(1);
    expect(run({ enum: ["a", "b"] }, "b")).toEqual([]);
    expect(run({ const: 3 }, 4)).toHaveLength(1);
    expect(run({ const: 3 }, 3)).toEqual([]);
  });

  it("enforces numeric bounds, both inclusive and exclusive", () => {
    expect(run({ type: "number", minimum: 1 }, 0)).toHaveLength(1);
    expect(run({ type: "number", maximum: 1 }, 2)).toHaveLength(1);
    expect(run({ type: "number", exclusiveMinimum: 0 }, 0)).toHaveLength(1);
    expect(run({ type: "number", exclusiveMaximum: 1 }, 1)).toHaveLength(1);
    expect(run({ type: "number", minimum: 0, exclusiveMaximum: 1 }, 0)).toEqual(
      [],
    );
  });

  it("enforces string and array lengths", () => {
    expect(run({ type: "string", minLength: 2 }, "a")).toHaveLength(1);
    expect(run({ type: "string", maxLength: 1 }, "ab")).toHaveLength(1);
    expect(run({ type: "array", minItems: 2 }, [1])).toHaveLength(1);
    expect(run({ type: "array", maxItems: 1 }, [1, 2])).toHaveLength(1);
  });

  it("checks array items and tuple positions", () => {
    expect(
      run({ type: "array", items: { type: "number" } }, [1, "x"]),
    ).toHaveLength(1);
    const tuple = {
      type: "array",
      prefixItems: [{ type: "number" }, { type: "string" }],
    };
    expect(run(tuple, [1, "a"])).toEqual([]);
    expect(run(tuple, [1, 2])).toHaveLength(1);
  });

  it("treats additionalProperties as a schema for map-like objects", () => {
    const map = { type: "object", additionalProperties: { type: "number" } };
    expect(run(map, { a: 1, b: 2 })).toEqual([]);
    expect(run(map, { a: 1, b: "x" })).toHaveLength(1);
  });

  it("anyOf needs one branch, oneOf exactly one, allOf every one", () => {
    const a = { type: "integer" };
    const b = { type: "number" };
    expect(run({ anyOf: [a, { type: "null" }] }, "x")).toHaveLength(1);
    expect(run({ anyOf: [a, { type: "null" }] }, null)).toEqual([]);
    expect(run({ oneOf: [a, b] }, 1)).toHaveLength(1); // both accept 1
    expect(run({ oneOf: [a, b] }, 1.5)).toEqual([]);
    expect(run({ allOf: [b, { minimum: 2 }] }, 1)).toHaveLength(1);
  });

  it("follows $ref and fails on a dangling or foreign one", () => {
    const withRef = {
      paths: {},
      components: { schemas: { N: { type: "number" } } },
    } as unknown as OpenApiSpec;
    expect(
      validate(withRef, { $ref: "#/components/schemas/N" }, "x"),
    ).toHaveLength(1);
    expect(() =>
      validate(withRef, { $ref: "#/components/schemas/Missing" }, 1),
    ).toThrow(/dangling/);
    expect(() => validate(withRef, { $ref: "other.json#/N" }, 1)).toThrow(
      /unsupported \$ref/,
    );
  });

  it("refuses to pass a keyword it does not understand", () => {
    expect(() => run({ type: "string", pattern: "^a" }, "b")).toThrow(
      /unsupported schema keyword "pattern"/,
    );
  });

  it("does not let NaN or Infinity pass as a number", () => {
    // JSON.stringify turns both into null, so this is what the wire carries.
    expect(run({ type: "number" }, null)).toHaveLength(1);
  });
});
