/**
 * Pure, framework-free numerics for the charts. Kept out of the components so
 * they can be unit-tested directly -- the binning and density maths are exactly
 * the kind of thing a reference-validated project should pin down.
 */

export interface NormalFit {
  mean: number;
  sigma: number;
}

export interface Bins {
  edges: number[];
  /** One [x0, x1, density] triple per bin, density = count / (n * width). */
  bars: [number, number, number][];
}

/** Min / max / mean in a single pass. Assumes a non-empty array. */
export function columnStats(values: number[]): {
  min: number;
  max: number;
  mean: number;
} {
  let min = values[0];
  let max = values[0];
  let sum = 0;
  for (const v of values) {
    if (v < min) min = v;
    if (v > max) max = v;
    sum += v;
  }
  return { min, max, mean: sum / values.length };
}

/** Freedman-Diaconis bin count, with a Sturges fallback and a sane clamp. */
export function binCount(values: number[], min: number, max: number): number {
  const n = values.length;
  const sorted = [...values].sort((a, b) => a - b);
  const q = (p: number) => {
    const idx = (n - 1) * p;
    const lo = Math.floor(idx);
    const hi = Math.ceil(idx);
    return sorted[lo] + (sorted[hi] - sorted[lo]) * (idx - lo);
  };
  const iqr = q(0.75) - q(0.25);
  const sturges = Math.ceil(Math.log2(n) + 1);
  if (iqr <= 0 || max <= min) return Math.max(5, Math.min(sturges, 40));
  const width = (2 * iqr) / Math.cbrt(n);
  const fd = Math.ceil((max - min) / width);
  return Math.max(5, Math.min(fd, 40));
}

/** Density histogram: bars integrate to 1, so a PDF overlays on the same axis. */
export function histogram(values: number[]): Bins {
  const n = values.length;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const k = binCount(values, min, max);
  const width = (max - min) / k || 1;
  const edges = Array.from({ length: k + 1 }, (_, i) => min + i * width);
  const counts = new Array<number>(k).fill(0);
  for (const v of values) {
    // The last edge is inclusive so the maximum lands in the final bin.
    const raw = Math.floor((v - min) / width);
    const bin = Math.min(raw, k - 1);
    counts[bin] += 1;
  }
  const bars = counts.map(
    (c, i): [number, number, number] => [edges[i], edges[i + 1], c / (n * width)],
  );
  return { edges, bars };
}

export function normalPdf(x: number, mean: number, sigma: number): number {
  const z = (x - mean) / sigma;
  return Math.exp(-0.5 * z * z) / (sigma * Math.sqrt(2 * Math.PI));
}

/**
 * The x-range for the capability chart. It must always span the spec limits,
 * even when a limit sits well outside the data (a capable process, or a USL far
 * above the sample) -- otherwise the spec line is clipped and silently vanishes.
 */
export function capabilityDomain(
  edges: number[],
  specLimits: Array<number | null>,
  fit: NormalFit | null,
): { lo: number; hi: number } {
  const specs = specLimits.filter((v): v is number => v != null);
  const edgeLo = edges[0];
  const edgeHi = edges[edges.length - 1];
  const fitSpan = fit ? [fit.mean - 4 * fit.sigma, fit.mean + 4 * fit.sigma] : [];
  const lo = Math.min(edgeLo, ...specs, ...fitSpan);
  const hi = Math.max(edgeHi, ...specs, ...fitSpan);
  const pad = (hi - lo) * 0.03 || 1;
  return { lo: lo - pad, hi: hi + pad };
}
