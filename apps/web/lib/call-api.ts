import { describeApiError } from "@/lib/errors";

/**
 * The result of one API call, as something a panel can branch on once.
 *
 * `ok: false` carries a sentence already fit to show a user -- the API's own
 * `detail` where there is one, the caller's wording otherwise.
 */
export type ApiOutcome<T> =
  { ok: true; data: T } | { ok: false; message: string };

/** The default wording for "the request never got there". */
export const UNREACHABLE = "Could not reach the API.";

/**
 * Run one API call and reduce its three outcomes to two.
 *
 * openapi-fetch reports a failure in two different ways -- a non-2xx fills
 * `error`, and a network failure rejects -- and every panel handled both, plus
 * the "2xx with no body" case, in its own copy of the same seven lines
 * (T-0059). Eleven copies in nine components, already drifting in wording.
 *
 * Deliberately *not* a `useApiCall` hook that owns the status state. The panels'
 * status unions are genuinely different -- one carries a result, one a report
 * *and* a curve, the control chart keeps a second state for its rule run -- so a
 * hook owning the shape would force nine components into one mould for the sake
 * of a shared try/catch. This shares the part that is actually identical and
 * leaves each panel its own state.
 *
 * @param request  the api-client call, unstarted
 * @param fallback what to say when the API failed but explained nothing usable
 * @param unreachable what to say when the request never arrived
 */
export async function callApi<T>(
  request: () => Promise<{ data?: T; error?: unknown }>,
  fallback: string,
  unreachable: string = UNREACHABLE,
): Promise<ApiOutcome<T>> {
  let response: { data?: T; error?: unknown };
  try {
    response = await request();
  } catch {
    return { ok: false, message: unreachable };
  }
  // `data` missing is a failure even on a 2xx: rendering "no results" from a
  // body that never arrived is the mistake T-0052 was about.
  if (response.error !== undefined || response.data === undefined) {
    return { ok: false, message: describeApiError(response.error, fallback) };
  }
  return { ok: true, data: response.data };
}
