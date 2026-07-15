/**
 * Reduce an openapi-fetch error body to a single human-readable line. FastAPI
 * sends either `{detail: string}` (our HTTPExceptions) or `{detail: [{msg}...]}`
 * (request-validation errors); this handles both, with a caller-provided
 * fallback for the network-error / unknown-shape case.
 */
export function describeApiError(error: unknown, fallback: string): string {
  if (error && typeof error === "object" && "detail" in error) {
    const detail = (error as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const first = detail[0] as { msg?: string } | undefined;
      if (first?.msg) return first.msg;
    }
  }
  return fallback;
}
