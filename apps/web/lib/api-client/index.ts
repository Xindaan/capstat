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

import type { components } from "./schema";

export type IngestResponse = components["schemas"]["IngestResponse"];
export type IngestColumn = components["schemas"]["IngestColumn"];

/**
 * POST a file to `/ingest` as multipart/form-data.
 *
 * `openapi-typescript` maps the binary body field to `string`, and
 * `openapi-fetch` JSON-serialises bodies by default; both are wrong for a file
 * upload. This helper is the single place that reconciles them — it builds a
 * `FormData` so the browser sets the multipart boundary, while the response
 * stays fully typed as {@link IngestResponse}.
 */
export function ingestFile(file: File) {
  return api.POST("/ingest", {
    // The field is typed `string` (binary); the File is what actually goes on
    // the wire via the serializer below.
    body: { file: file as unknown as string },
    bodySerializer() {
      const form = new FormData();
      form.set("file", file);
      return form;
    },
  });
}
