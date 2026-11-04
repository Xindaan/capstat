import type { Locator, Page } from "@playwright/test";

import { test, expect } from "./fixtures";

import { gotoReady, requestDuring } from "./support";

// T-0100. Hand-entered numbers: the formats the app accepts, in every browser
// locale. Each test answers the request with a 422 -- it asserts what the page
// SENT, and the contract fixture (./fixtures) checks that it was well formed.

async function refuse(page: Page, pattern: string) {
  await page.route(pattern, (r) =>
    r.fulfill({
      status: 422,
      contentType: "application/json",
      body: JSON.stringify({ detail: "not under test" }),
    }),
  );
}

/** Type like a person: key by key, so the input's own filtering applies. */
async function typeInto(field: Locator, text: string) {
  await field.click();
  await field.press("ControlOrMeta+a");
  await field.press("Backspace");
  await field.pressSequentially(text);
}

test.describe("readings with a decimal comma", () => {
  test("bias: '36,1' is one reading, and the page says how many it read", async ({
    page,
  }) => {
    await refuse(page, "**/compute/bias");
    await gotoReady(page, "/msa");
    const panel = page.getByLabel("Bias study");
    await panel
      .getByRole("textbox", { name: "Readings" })
      .fill("36,1\n35,9\n36,0\n36,05\n35,95");

    await expect(panel.getByText("5 readings read")).toBeVisible();
    await expect(panel.getByText(/decimal comma/)).toBeVisible();

    const body = await requestDuring<{ measurements: number[] }>(
      page,
      "**/compute/bias",
      () => panel.getByRole("button", { name: "Compute bias" }).click(),
    );
    expect(body.measurements).toEqual([36.1, 35.9, 36, 36.05, 35.95]);
  });

  test("stability: the same, spread over a row", async ({ page }) => {
    await refuse(page, "**/compute/stability");
    await gotoReady(page, "/msa");
    const panel = page.getByLabel("Stability study");
    await panel
      .getByRole("textbox", { name: "Readings" })
      .fill("10,02 9,98;10,01");

    const body = await requestDuring<{ measurements: number[] }>(
      page,
      "**/compute/stability",
      () => panel.getByRole("button", { name: "Check stability" }).click(),
    );
    expect(body.measurements).toEqual([10.02, 9.98, 10.01]);
  });

  test("linearity: a row of '7,1 7,2'", async ({ page }) => {
    await refuse(page, "**/compute/linearity");
    await gotoReady(page, "/msa");
    const panel = page.getByLabel("Linearity study");
    await panel.getByLabel("Readings for part 1").fill("7,1 7,2 7,05");

    const body = await requestDuring<{ measurements: number[][] }>(
      page,
      "**/compute/linearity",
      () => panel.getByRole("button", { name: "Compute linearity" }).click(),
    );
    expect(body.measurements[0]).toEqual([7.1, 7.2, 7.05]);
  });

  test("a text that could be read two ways is refused, with the reason", async ({
    page,
  }) => {
    let requests = 0;
    await page.route("**/compute/bias", (r) => {
      requests += 1;
      return r.abort();
    });
    await gotoReady(page, "/msa");
    const panel = page.getByLabel("Bias study");
    await panel.getByRole("textbox", { name: "Readings" }).fill("36,1, 35,9");

    await expect(panel.getByText(/could be read two ways/)).toBeVisible();
    await expect(
      panel.getByRole("button", { name: "Compute bias" }),
    ).toBeDisabled();
    expect(requests).toBe(0);
  });
});

for (const locale of ["en-US", "de-DE"]) {
  test.describe(`numbers typed into fields, ${locale} browser`, () => {
    test.use({ locale });

    test("a percentage typed '2,5' is 2.5 %, not 25 %", async ({ page }) => {
      await refuse(page, "**/acceptance-sampling/design");
      await gotoReady(page, "/acceptance-sampling");
      await typeInto(page.getByLabel("LTPD %"), "7,5");
      await typeInto(page.getByLabel("AQL %"), "2,5");

      const body = await requestDuring<{ aql: number; ltpd: number }>(
        page,
        "**/acceptance-sampling/design",
        () => page.getByRole("button", { name: "Design the plan" }).click(),
      );
      expect(body.aql).toBeCloseTo(0.025, 12);
      expect(body.ltpd).toBeCloseTo(0.075, 12);
    });

    test("a lot size '5.000' is refused as ambiguous, not read as 5", async ({
      page,
    }) => {
      await gotoReady(page, "/acceptance-sampling");
      await typeInto(page.getByLabel("Lot size"), "5.000");

      await expect(page.getByText(/could mean 5 or 5000/)).toBeVisible();
      await expect(
        page.getByRole("button", { name: "Design the plan" }),
      ).toBeDisabled();

      await typeInto(page.getByLabel("Lot size"), "5000");
      await expect(
        page.getByRole("button", { name: "Design the plan" }),
      ).toBeEnabled();
    });

    test("a grid cell typed '3,29' is 3.29", async ({ page }) => {
      await refuse(page, "**/compute/gage-rr");
      await gotoReady(page, "/gage-rr");
      await typeInto(page.getByLabel("Part 1, operator A, trial 1"), "3,29");
      await typeInto(page.getByLabel("Part 1, operator A, trial 2"), "3,41");

      const body = await requestDuring<{ data: number[][][] }>(
        page,
        "**/compute/gage-rr",
        () => page.getByRole("button", { name: "Compute Gage R&R" }).click(),
      );
      expect(body.data[0][0].slice(0, 2)).toEqual([3.29, 3.41]);
    });

    test("a tolerance typed '0,5' is 0.5", async ({ page }) => {
      await refuse(page, "**/compute/gage-rr");
      await gotoReady(page, "/gage-rr");
      await typeInto(page.getByLabel("Tolerance"), "0,5");

      const body = await requestDuring<{ tolerance: number }>(
        page,
        "**/compute/gage-rr",
        () => page.getByRole("button", { name: "Compute Gage R&R" }).click(),
      );
      expect(body.tolerance).toBe(0.5);
    });

    test("a spec limit typed '9,85' is 9.85", async ({ page }) => {
      await page.route("**/ingest", (r) =>
        r.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            n_rows: 3,
            columns: [
              { name: "x", values: [10, 10.1, 9.9], dropped_missing: 0 },
            ],
            ignored_columns: [],
            warnings: [],
          }),
        }),
      );
      await page.route("**/control-chart/i-mr", (r) =>
        r.fulfill({ status: 422, body: '{"detail":"x"}' }),
      );
      await refuse(page, "**/compute/capability/analyze");
      await gotoReady(page, "/");
      await page.locator('input[type="file"]').setInputFiles({
        name: "s.csv",
        mimeType: "text/csv",
        buffer: Buffer.from("x\n10\n10.1\n9.9\n"),
      });
      await typeInto(page.getByLabel("LSL"), "9,85");
      await typeInto(page.getByLabel("USL"), "10,15");

      const body = await requestDuring<{ lsl: number; usl: number }>(
        page,
        "**/compute/capability/analyze",
        () => page.getByRole("button", { name: "Compute capability" }).click(),
      );
      expect([body.lsl, body.usl]).toEqual([9.85, 10.15]);
    });
  });
}

test.describe("the Gage R&R grid", () => {
  test.use({ permissions: ["clipboard-read", "clipboard-write"] });

  const cell = (page: Page, p: number, o: string, t: number) =>
    page.getByLabel(`Part ${p}, operator ${o}, trial ${t}`);

  async function paste(page: Page, target: Locator, text: string) {
    await page.evaluate((t) => navigator.clipboard.writeText(t), text);
    await target.click();
    await page.keyboard.press("ControlOrMeta+v");
  }

  test("an Excel block fills the grid from the cell it was pasted into", async ({
    page,
  }) => {
    await refuse(page, "**/compute/gage-rr");
    await gotoReady(page, "/gage-rr");
    // Two rows, three columns, decimal commas, starting at trial 2: it runs
    // A2, A3 and on into operator B's first trial, like the columns of the
    // sheet it came from.
    await paste(
      page,
      cell(page, 1, "A", 2),
      "9,01\t9,02\t9,03\n9,11\t9,12\t9,13\n",
    );

    await expect(cell(page, 1, "A", 2)).toHaveValue("9,01");
    await expect(cell(page, 1, "A", 3)).toHaveValue("9,02");
    await expect(cell(page, 1, "B", 1)).toHaveValue("9,03");
    await expect(cell(page, 2, "A", 2)).toHaveValue("9,11");
    await expect(cell(page, 2, "B", 1)).toHaveValue("9,13");
    // Cells outside the block are untouched.
    await expect(cell(page, 1, "A", 1)).toHaveValue("3.29");
    await expect(cell(page, 1, "B", 2)).toHaveValue("3.25");
    await expect(cell(page, 3, "A", 2)).toHaveValue("4.17");

    const body = await requestDuring<{ data: number[][][] }>(
      page,
      "**/compute/gage-rr",
      () => page.getByRole("button", { name: "Compute Gage R&R" }).click(),
    );
    expect(body.data[0][0]).toEqual([3.29, 9.01, 9.02]);
    expect(body.data[0][1][0]).toBe(9.03);
    expect(body.data[1][0].slice(1)).toEqual([9.11, 9.12]);
  });

  test("a block that does not fit is refused whole, and says so", async ({
    page,
  }) => {
    await gotoReady(page, "/gage-rr");
    const rows = Array.from({ length: 6 }, () => "1\t2\t3").join("\n");
    await paste(page, cell(page, 1, "A", 1), rows);

    await expect(page.getByText(/6 rows/)).toBeVisible();
    await expect(page.getByText(/Nothing was pasted/)).toBeVisible();
    await expect(cell(page, 1, "A", 1)).toHaveValue("3.29");
    await expect(cell(page, 5, "A", 1)).toHaveValue("2.20");
  });

  test("a block with uneven rows is refused whole", async ({ page }) => {
    await gotoReady(page, "/gage-rr");
    await paste(page, cell(page, 1, "A", 1), "1\t2\n3\n");

    await expect(page.getByText(/different numbers of columns/)).toBeVisible();
    await expect(cell(page, 1, "A", 1)).toHaveValue("3.29");
    await expect(cell(page, 2, "A", 1)).toHaveValue("2.44");
  });

  test("a block with a header row is refused, naming the cell", async ({
    page,
  }) => {
    await gotoReady(page, "/gage-rr");
    await paste(page, cell(page, 1, "A", 1), "Trial 1\tTrial 2\n3,1\t3,2\n");

    await expect(page.getByText(/Nothing was pasted/)).toBeVisible();
    await expect(page.getByText(/row 1, column 1/)).toBeVisible();
    await expect(cell(page, 1, "A", 1)).toHaveValue("3.29");
  });

  test("arrow keys and the wheel move around; they never change a reading", async ({
    page,
  }) => {
    await gotoReady(page, "/gage-rr");
    const first = cell(page, 1, "A", 1);
    await first.focus();

    await page.keyboard.press("ArrowDown");
    // The reading first: a number input would have stepped it to 2.29.
    await expect(first).toHaveValue("3.29");
    await expect(cell(page, 2, "A", 1)).toBeFocused();
    await expect(cell(page, 2, "A", 1)).toHaveValue("2.44");

    await page.keyboard.press("ArrowUp");
    await expect(first).toBeFocused();
    await expect(first).toHaveValue("3.29");

    await first.hover();
    await page.mouse.wheel(0, -200);
    await expect(first).toHaveValue("3.29");

    await page.keyboard.press("Enter");
    await expect(cell(page, 2, "A", 1)).toBeFocused();
  });
});
