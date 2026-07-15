import createClient from "openapi-fetch";

import type { paths } from "./schema";

// The base URL is build-time configurable; it defaults to the local API so
// `npm run dev` works with `uvicorn capstat_api.main:app` and no extra setup.
const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

/**
 * The single typed entry point to capstat-api. Every request and response is
 * typed from the committed OpenAPI schema, so a contract change surfaces as a
 * TypeScript error rather than a runtime surprise.
 */
export const api = createClient<paths>({ baseUrl });

export type { paths, components } from "./schema";
