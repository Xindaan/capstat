import { describe, expect, it } from "vitest";

import {
  STUDY_SCHEMA_VERSION,
  buildStudyFile,
  parseStudyFile,
  serialiseStudyFile,
  studyFileName,
} from "@/lib/study-file";

interface Inputs {
  aql: string;
  ltpd: string;
}

const INPUTS: Inputs = { aql: "1", ltpd: "5" };

describe("buildStudyFile", () => {
  it("stamps the format, the version and the page", () => {
    const file = buildStudyFile(
      "acceptance-sampling",
      INPUTS,
      new Date("2026-07-22"),
    );
    expect(file.format).toBe("capstat-study");
    expect(file.schema_version).toBe(STUDY_SCHEMA_VERSION);
    expect(file.page).toBe("acceptance-sampling");
    expect(file.saved).toBe("2026-07-22");
    expect(file.inputs).toEqual(INPUTS);
  });

  it("round-trips through serialisation", () => {
    const file = buildStudyFile("acceptance-sampling", INPUTS);
    const result = parseStudyFile<Inputs>(
      serialiseStudyFile(file),
      "acceptance-sampling",
    );
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.file.inputs).toEqual(INPUTS);
  });
});

describe("parseStudyFile", () => {
  it("drops anything that is not an input — a stale results block above all", () => {
    // The dangerous failure this prevents: a hand-edited or older file carrying
    // computed numbers, displayed as though this version had produced them.
    const doctored = JSON.stringify({
      format: "capstat-study",
      schema_version: 1,
      page: "acceptance-sampling",
      saved: "2026-07-22",
      inputs: INPUTS,
      results: { ppk: 99 },
    });
    const result = parseStudyFile<Inputs>(doctored, "acceptance-sampling");
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.file).not.toHaveProperty("results");
      expect(Object.keys(result.file).sort()).toEqual([
        "format",
        "inputs",
        "page",
        "saved",
        "schema_version",
      ]);
    }
  });

  it("refuses a newer format instead of dropping fields it cannot read", () => {
    const future = JSON.stringify({
      format: "capstat-study",
      schema_version: STUDY_SCHEMA_VERSION + 1,
      page: "acceptance-sampling",
      inputs: INPUTS,
    });
    const result = parseStudyFile<Inputs>(future, "acceptance-sampling");
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.reason).toContain("newer capstat");
      expect(result.reason).toContain(String(STUDY_SCHEMA_VERSION + 1));
    }
  });

  it("refuses a study belonging to another page, and names both", () => {
    const elsewhere = serialiseStudyFile(buildStudyFile("gage-rr", INPUTS));
    const result = parseStudyFile<Inputs>(elsewhere, "acceptance-sampling");
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.reason).toContain("gage-rr");
      expect(result.reason).toContain("acceptance-sampling");
    }
  });

  it("refuses a file that is not JSON", () => {
    const result = parseStudyFile<Inputs>(
      "not json at all",
      "acceptance-sampling",
    );
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toContain("not JSON");
  });

  it("refuses JSON that is not a capstat study", () => {
    const result = parseStudyFile<Inputs>(
      JSON.stringify({ aql: "1" }),
      "acceptance-sampling",
    );
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toContain("not saved by capstat");
  });

  it("refuses a document with no version, rather than assuming version 1", () => {
    const result = parseStudyFile<Inputs>(
      JSON.stringify({ format: "capstat-study", page: "acceptance-sampling" }),
      "acceptance-sampling",
    );
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toContain("which version");
  });

  it("refuses a document whose inputs are missing or not an object", () => {
    for (const inputs of [undefined, null, [], "nope", 3]) {
      const result = parseStudyFile<Inputs>(
        JSON.stringify({
          format: "capstat-study",
          schema_version: 1,
          page: "acceptance-sampling",
          inputs,
        }),
        "acceptance-sampling",
      );
      expect(result.ok).toBe(false);
      if (!result.ok) expect(result.reason).toContain("no inputs");
    }
  });
});

describe("studyFileName", () => {
  it("names the page and the date, so a folder of them sorts usefully", () => {
    expect(studyFileName("gage-rr", "2026-07-22")).toBe(
      "capstat-gage-rr-2026-07-22.json",
    );
  });
});
