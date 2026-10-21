/**
 * A small validator for request bodies against `apps/api/openapi.json`.
 *
 * Why this exists (T-0099, WEB-21 / ARCH-8): the e2e suite mocks every API call,
 * and a mock answers 200 to whatever it is sent. "Decide the lot" posted a body
 * with a field the endpoint forbids (`rejection_number`), the real API answered
 * 422 for every click, and tsc, vitest, the mocked e2e and CI stayed green for
 * six weeks. The generated `schema.d.ts` cannot catch this class: it types the
 * *intent* of the call site, while the bug was an object that flowed in from a
 * response with more keys than the request allows.
 *
 * So the e2e fixture (e2e/fixtures.ts) hands every request the browser makes to
 * the API to this module, and a body the schema would refuse fails the test --
 * whether or not the mock in front of it was polite enough to accept it.
 *
 * Scope, deliberately small: the JSON-Schema subset FastAPI/pydantic emits into
 * OpenAPI 3.1 and nothing more (`$ref`, `type`, `anyOf`/`oneOf`/`allOf`,
 * `properties`/`required`/`additionalProperties`, `items`/`prefixItems`,
 * `enum`/`const`, numeric and length bounds). An unsupported keyword is an
 * error rather than a silent pass: a validator that skips what it does not
 * understand is the same hole in a new place.
 */

export type Json = null | boolean | number | string | Json[] | JsonObject;
export interface JsonObject {
  [key: string]: Json;
}

interface Schema {
  $ref?: string;
  type?: string | string[];
  anyOf?: Schema[];
  oneOf?: Schema[];
  allOf?: Schema[];
  properties?: Record<string, Schema>;
  required?: string[];
  additionalProperties?: boolean | Schema;
  items?: Schema;
  prefixItems?: Schema[];
  enum?: Json[];
  const?: Json;
  minimum?: number;
  maximum?: number;
  exclusiveMinimum?: number;
  exclusiveMaximum?: number;
  minItems?: number;
  maxItems?: number;
  minLength?: number;
  maxLength?: number;
  [annotation: string]: unknown;
}

export interface OpenApiSpec {
  paths: Record<
    string,
    Record<
      string,
      {
        requestBody?: {
          required?: boolean;
          content: Record<string, { schema: Schema }>;
        };
      }
    >
  >;
  components: { schemas: Record<string, Schema> };
}

/** One reason a value does not fit its schema, with the JSON path it sits at. */
export interface Violation {
  path: string;
  message: string;
}

/** Keywords that carry documentation or defaults only, never a constraint. */
const ANNOTATIONS = new Set([
  "title",
  "description",
  "default",
  "examples",
  "example",
  "deprecated",
  "format",
  "contentMediaType",
]);

/** Every keyword this validator enforces. Anything else is refused loudly. */
const ENFORCED = new Set([
  "$ref",
  "type",
  "anyOf",
  "oneOf",
  "allOf",
  "properties",
  "required",
  "additionalProperties",
  "items",
  "prefixItems",
  "enum",
  "const",
  "minimum",
  "maximum",
  "exclusiveMinimum",
  "exclusiveMaximum",
  "minItems",
  "maxItems",
  "minLength",
  "maxLength",
]);

function resolve(spec: OpenApiSpec, ref: string): Schema {
  const prefix = "#/components/schemas/";
  if (!ref.startsWith(prefix)) throw new Error(`unsupported $ref ${ref}`);
  const target = spec.components.schemas[ref.slice(prefix.length)];
  if (!target) throw new Error(`dangling $ref ${ref}`);
  return target;
}

function typeOf(value: Json): string {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  return typeof value; // boolean | number | string | object
}

function matchesType(value: Json, type: string): boolean {
  switch (type) {
    case "integer":
      return typeof value === "number" && Number.isInteger(value);
    case "number":
      return typeof value === "number" && Number.isFinite(value);
    case "null":
      return value === null;
    case "array":
      return Array.isArray(value);
    case "object":
      return typeOf(value) === "object";
    default:
      return typeof value === type;
  }
}

export function validate(
  spec: OpenApiSpec,
  schema: Schema,
  value: Json,
  path = "$",
): Violation[] {
  for (const keyword of Object.keys(schema)) {
    if (!ENFORCED.has(keyword) && !ANNOTATIONS.has(keyword)) {
      throw new Error(`unsupported schema keyword "${keyword}" at ${path}`);
    }
  }
  if (schema.$ref !== undefined) {
    return validate(spec, resolve(spec, schema.$ref), value, path);
  }

  const out: Violation[] = [];
  const fail = (message: string) => out.push({ path, message });

  if (schema.allOf) {
    for (const part of schema.allOf) {
      out.push(...validate(spec, part, value, path));
    }
  }
  for (const key of ["anyOf", "oneOf"] as const) {
    const branches = schema[key];
    if (!branches) continue;
    const results = branches.map((b) => validate(spec, b, value, path));
    const passing = results.filter((r) => r.length === 0).length;
    if (passing === 0) {
      // The most specific complaint is the one from the branch that got
      // furthest, i.e. the one with the fewest violations; list all branches
      // so a reader can see what each would have accepted.
      fail(
        `${key}: no branch accepts this value (${results
          .map((r) => r.map((v) => `${v.path}: ${v.message}`).join("; "))
          .join(" | ")})`,
      );
    } else if (key === "oneOf" && passing > 1) {
      fail("oneOf: more than one branch accepts this value");
    }
  }

  if (schema.type !== undefined) {
    const types = Array.isArray(schema.type) ? schema.type : [schema.type];
    if (!types.some((t) => matchesType(value, t))) {
      fail(`expected ${types.join(" or ")}, got ${typeOf(value)}`);
      return out; // the keywords below assume the right type
    }
  }
  if (
    schema.enum &&
    !schema.enum.some((e) => JSON.stringify(e) === JSON.stringify(value))
  ) {
    fail(`must be one of ${JSON.stringify(schema.enum)}`);
  }
  if (
    schema.const !== undefined &&
    JSON.stringify(schema.const) !== JSON.stringify(value)
  ) {
    fail(`must equal ${JSON.stringify(schema.const)}`);
  }

  if (typeof value === "number") {
    if (schema.minimum !== undefined && value < schema.minimum) {
      fail(`${value} is below the minimum ${schema.minimum}`);
    }
    if (schema.maximum !== undefined && value > schema.maximum) {
      fail(`${value} is above the maximum ${schema.maximum}`);
    }
    if (
      schema.exclusiveMinimum !== undefined &&
      value <= schema.exclusiveMinimum
    ) {
      fail(`${value} must be above ${schema.exclusiveMinimum}`);
    }
    if (
      schema.exclusiveMaximum !== undefined &&
      value >= schema.exclusiveMaximum
    ) {
      fail(`${value} must be below ${schema.exclusiveMaximum}`);
    }
  }
  if (typeof value === "string") {
    if (schema.minLength !== undefined && value.length < schema.minLength) {
      fail(`shorter than ${schema.minLength} characters`);
    }
    if (schema.maxLength !== undefined && value.length > schema.maxLength) {
      fail(`longer than ${schema.maxLength} characters`);
    }
  }
  if (Array.isArray(value)) {
    if (schema.minItems !== undefined && value.length < schema.minItems) {
      fail(`fewer than ${schema.minItems} items`);
    }
    if (schema.maxItems !== undefined && value.length > schema.maxItems) {
      fail(`more than ${schema.maxItems} items`);
    }
    const prefix = schema.prefixItems ?? [];
    value.forEach((item, i) => {
      const itemSchema = i < prefix.length ? prefix[i] : schema.items;
      if (itemSchema) {
        out.push(...validate(spec, itemSchema, item, `${path}[${i}]`));
      }
    });
  }
  if (typeOf(value) === "object") {
    const obj = value as JsonObject;
    for (const name of schema.required ?? []) {
      if (!(name in obj)) fail(`missing required field "${name}"`);
    }
    const known = schema.properties ?? {};
    for (const [name, member] of Object.entries(obj)) {
      if (name in known) {
        out.push(...validate(spec, known[name], member, `${path}.${name}`));
      } else if (schema.additionalProperties === false) {
        out.push({
          path: `${path}.${name}`,
          message: "extra field not permitted (additionalProperties: false)",
        });
      } else if (
        typeof schema.additionalProperties === "object" &&
        schema.additionalProperties !== null
      ) {
        out.push(
          ...validate(
            spec,
            schema.additionalProperties,
            member,
            `${path}.${name}`,
          ),
        );
      }
    }
  }
  return out;
}

/**
 * Check one request the browser made against the contract.
 *
 * Returns the reasons it would be refused; an empty list means the API's schema
 * accepts it. `body` is the parsed JSON body, or `undefined` when there was none.
 * Multipart uploads are checked for the presence of a body only -- the one
 * endpoint that takes them (`/ingest`) is a single `file` part.
 */
export function validateRequest(
  spec: OpenApiSpec,
  method: string,
  pathname: string,
  contentType: string | undefined,
  body: Json | undefined,
): Violation[] {
  const operation = spec.paths[pathname]?.[method.toLowerCase()];
  if (!operation) {
    return [
      {
        path: "$",
        message: `${method} ${pathname} is not an operation in openapi.json`,
      },
    ];
  }
  const declared = operation.requestBody;
  if (!declared) {
    return body === undefined
      ? []
      : [{ path: "$", message: `${method} ${pathname} takes no body` }];
  }
  if (body === undefined) {
    return declared.required
      ? [{ path: "$", message: `${method} ${pathname} needs a body` }]
      : [];
  }
  const mime = (contentType ?? "").split(";")[0].trim().toLowerCase();
  const content = declared.content[mime];
  if (!content) {
    return [
      {
        path: "$",
        message: `${method} ${pathname} does not accept ${mime || "an untyped body"} (accepts ${Object.keys(declared.content).join(", ")})`,
      },
    ];
  }
  if (mime === "multipart/form-data") return []; // see the note above
  return validate(spec, content.schema, body);
}

/**
 * Every keyword reachable from a request body schema, minus the ones this
 * validator enforces or may ignore. A non-empty result means openapi.json grew
 * a constraint (`pattern`, `uniqueItems`, ...) the contract check would let
 * through unchecked -- the same silent hole as a mock that answers 200 to
 * anything, one level down. The unit test pins this list to empty.
 */
export function unsupportedKeywords(spec: OpenApiSpec): string[] {
  const seen = new Set<string>();
  const found = new Set<string>();
  const visit = (schema: Schema, where: string) => {
    for (const keyword of Object.keys(schema)) {
      if (!ENFORCED.has(keyword) && !ANNOTATIONS.has(keyword)) {
        found.add(`${keyword} (${where})`);
      }
    }
    if (schema.$ref !== undefined) {
      if (seen.has(schema.$ref)) return;
      seen.add(schema.$ref);
      visit(resolve(spec, schema.$ref), schema.$ref);
      return;
    }
    for (const key of ["anyOf", "oneOf", "allOf", "prefixItems"] as const) {
      for (const part of schema[key] ?? []) visit(part, where);
    }
    if (schema.items) visit(schema.items, where);
    for (const member of Object.values(schema.properties ?? {})) {
      visit(member, where);
    }
    if (
      typeof schema.additionalProperties === "object" &&
      schema.additionalProperties !== null
    ) {
      visit(schema.additionalProperties, where);
    }
  };
  for (const operations of Object.values(spec.paths)) {
    for (const operation of Object.values(operations)) {
      for (const content of Object.values(
        operation.requestBody?.content ?? {},
      )) {
        visit(content.schema, "request body");
      }
    }
  }
  return [...found].sort();
}
