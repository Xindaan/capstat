import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

/**
 * Text contrast, computed rather than eyeballed (T-0057).
 *
 * The card labels are the names of the numbers -- "Producer risk", "ndc" --
 * not decoration, so WCAG 2.1 AA's 4.5:1 for small text applies to them. It was
 * not met: a 40 % opacity of the foreground resolves to #a2a2a2 on white,
 * 2.55:1. (Spelled out rather than written as the class, so Tailwind does not
 * scan this file and emit the very utility the guard below forbids.)
 *
 * These tests read the actual token values out of globals.css and do the WCAG
 * arithmetic, so a future edit to a colour is checked rather than trusted.
 */

const ROOT = join(__dirname, "..");
const CSS = readFileSync(join(ROOT, "app", "globals.css"), "utf8");

type RGB = [number, number, number];

function parseHex(hex: string): RGB {
  const h = hex.replace("#", "");
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ];
}

/** WCAG 2.1 relative luminance. */
function luminance([r, g, b]: RGB): number {
  const channel = (v: number) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

function contrast(a: RGB, b: RGB): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

/** Composite `foreground` at `alpha` over `background`, as the browser does. */
function blend(fg: RGB, bg: RGB, alpha: number): RGB {
  return fg.map((c, i) => Math.round(alpha * c + (1 - alpha) * bg[i])) as RGB;
}

/** The value of a custom property inside the nth `:root` block of the file. */
function token(name: string, occurrence: number): RGB {
  const matches = [
    ...CSS.matchAll(new RegExp(`${name}:\\s*(#[0-9a-f]{6})`, "gi")),
  ];
  const found = matches[occurrence];
  if (!found) throw new Error(`no ${name} #${occurrence} in globals.css`);
  return parseHex(found[1]);
}

const THEMES = [
  { name: "light", background: 0, foreground: 0, muted: 0 },
  { name: "dark", background: 1, foreground: 1, muted: 1 },
  { name: "print", background: 2, foreground: 2, muted: 2 },
];

describe("the muted text token meets WCAG AA", () => {
  for (const theme of THEMES) {
    it(`is at least 4.5:1 in ${theme.name}`, () => {
      const bg = token("--background", theme.background);
      const muted = token("--muted", theme.muted);
      expect(contrast(muted, bg)).toBeGreaterThanOrEqual(4.5);
    });

    it(`stays visibly quieter than the full foreground in ${theme.name}`, () => {
      // A token that just equals the foreground would pass the check above and
      // defeat its own purpose.
      const bg = token("--background", theme.background);
      const fg = token("--foreground", theme.foreground);
      const muted = token("--muted", theme.muted);
      expect(contrast(muted, bg)).toBeLessThan(contrast(fg, bg));
    });
  }
});

describe("no component leans on an opacity step that fails AA", () => {
  it("documents which steps of text-foreground/N are usable", () => {
    // Recorded because the boundary is not obvious: /50 passes in dark and
    // fails in light, so "it looks fine" is not evidence either way.
    const usable: Record<number, boolean> = {};
    for (const step of [40, 45, 50, 60, 70]) {
      const light = contrast(
        blend(token("--foreground", 0), token("--background", 0), step / 100),
        token("--background", 0),
      );
      const dark = contrast(
        blend(token("--foreground", 1), token("--background", 1), step / 100),
        token("--background", 1),
      );
      usable[step] = Math.min(light, dark) >= 4.5;
    }
    expect(usable).toEqual({
      40: false,
      45: false,
      50: false,
      60: true,
      70: true,
    });
  });

  it("and no component uses one of them", () => {
    // The guard that keeps this fixed. Replacing 51 occurrences once is worth
    // little if the 52nd can be added without anything noticing -- and the
    // failing steps look identical in source to the passing ones.
    const offenders: string[] = [];
    const walk = (dir: string) => {
      for (const item of readdirSync(dir, { withFileTypes: true })) {
        const path = join(dir, item.name);
        if (item.isDirectory()) {
          walk(path);
        } else if (item.name.endsWith(".tsx")) {
          // .tsx only: class names live there. globals.css names the old value
          // in a comment on purpose, as the record of what was wrong.
          const source = readFileSync(path, "utf8");
          for (const hit of source.matchAll(/text-foreground\/(\d+)/g)) {
            if (Number(hit[1]) < 60) offenders.push(`${path}: ${hit[0]}`);
          }
        }
      }
    };
    walk(join(ROOT, "components"));
    walk(join(ROOT, "app"));
    expect(offenders).toEqual([]);
  });
});
