import {
  validateRequest,
  type Json,
  type OpenApiSpec,
} from "./openapi-contract";

/** The parts of a Playwright `Request` the check reads; a test can fake them. */
export interface RequestLike {
  url: () => string;
  method: () => string;
  headers: () => Record<string, string>;
  postData: () => string | null;
}

/** One request the API's schema would have refused. */
export interface ContractBreak {
  request: string;
  problems: string[];
}

/**
 * Check one browser request against the contract.
 *
 * "The API" is every request to `apiOrigin`; anything else (the page itself,
 * fonts, Next's dev channel) is not this check's business. An unknown path on
 * the API's origin is a violation: a typo'd URL breaks the contract as much as
 * a typo'd field. Returns null for a request that conforms.
 */
export function checkRequest(
  spec: OpenApiSpec,
  apiOrigin: string,
  request: RequestLike,
): ContractBreak | null {
  const url = new URL(request.url());
  if (url.origin !== apiOrigin) return null;
  const label = `${request.method()} ${url.pathname}`;

  const contentType = request.headers()["content-type"];
  const raw = request.postData();
  let body: Json | undefined;
  if (raw === null || raw === "") {
    body = undefined;
  } else if ((contentType ?? "").startsWith("application/json")) {
    try {
      body = JSON.parse(raw) as Json;
    } catch {
      return { request: label, problems: ["$: body is not valid JSON"] };
    }
  } else {
    body = raw; // multipart and the like: presence only, see the validator
  }

  const problems = validateRequest(
    spec,
    request.method(),
    url.pathname,
    contentType,
    body,
  ).map((v) => `${v.path}: ${v.message}`);
  return problems.length === 0 ? null : { request: label, problems };
}
