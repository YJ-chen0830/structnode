// Common Taiwan steel section sizes. H-beam dimensions/A/Ix/Iy are the
// "commonly used" (catalog-unmarked) sizes from 東和鋼鐵 CNS 1490/JIS G3192
// H 型鋼 standard dimension table. Square tube dimensions/A/Ix/Iy are from
// a Taiwan steel-tube supplier's 方形管 spec table (JIS/CNS not stated by
// the source; treat as commercial reference, not a cited standard).
//
// Neither catalog publishes the torsional constant J, so it is computed
// here via standard thin-wall approximations rather than left blank:
//   - H-beam (open, two flanges + web): J = (1/3) * sum(b_i * t_i^3)
//   - Square tube (closed, Bredt's formula, constant wall thickness):
//     J = (B-t)^3 * t
// Both are the standard engineering approximations for these shapes and
// are commonly within a few percent of the exact (warping-corrected)
// value for ordinary proportions -- good enough for linear-static framing,
// not a substitute for a code-committee torsion table.

interface RawHBeam {
  id: string;
  /** H, B, t1 (web), t2 (flange), all mm. */
  H: number;
  B: number;
  t1: number;
  t2: number;
  /** cm^2 */
  A: number;
  /** cm^4 */
  Ix: number;
  Iy: number;
}

const RAW_H_BEAMS: RawHBeam[] = [
  { id: "H-100x50x5x7", H: 100, B: 50, t1: 5, t2: 7, A: 11.85, Ix: 187, Iy: 14.8 },
  { id: "H-100x100x6x8", H: 100, B: 100, t1: 6, t2: 8, A: 21.59, Ix: 378, Iy: 134 },
  { id: "H-125x60x6x8", H: 125, B: 60, t1: 6, t2: 8, A: 16.19, Ix: 409, Iy: 29.1 },
  { id: "H-125x125x6.5x9", H: 125, B: 125, t1: 6.5, t2: 9, A: 30.0, Ix: 839, Iy: 293 },
  { id: "H-150x75x5x7", H: 150, B: 75, t1: 5, t2: 7, A: 17.85, Ix: 666, Iy: 49.5 },
  { id: "H-150x150x7x10", H: 150, B: 150, t1: 7, t2: 10, A: 39.65, Ix: 1620, Iy: 563 },
  { id: "H-175x90x5x8", H: 175, B: 90, t1: 5, t2: 8, A: 22.9, Ix: 1210, Iy: 98 },
  { id: "H-200x100x5.5x8", H: 200, B: 100, t1: 5.5, t2: 8, A: 26.67, Ix: 1810, Iy: 134 },
  { id: "H-200x150x6x9", H: 200, B: 150, t1: 6, t2: 9, A: 38.11, Ix: 2630, Iy: 507 },
  { id: "H-200x200x8x12", H: 200, B: 200, t1: 8, t2: 12, A: 63.53, Ix: 4720, Iy: 1600 },
  { id: "H-250x125x6x9", H: 250, B: 125, t1: 6, t2: 9, A: 36.97, Ix: 3960, Iy: 294 },
  { id: "H-250x175x7x11", H: 250, B: 175, t1: 7, t2: 11, A: 55.49, Ix: 6040, Iy: 984 },
  { id: "H-250x250x9x14", H: 250, B: 250, t1: 9, t2: 14, A: 91.43, Ix: 10700, Iy: 3650 },
  { id: "H-300x150x6.5x9", H: 300, B: 150, t1: 6.5, t2: 9, A: 46.78, Ix: 7210, Iy: 508 },
  { id: "H-300x200x8x12", H: 300, B: 200, t1: 8, t2: 12, A: 71.05, Ix: 11100, Iy: 1600 },
  { id: "H-350x175x7x11", H: 350, B: 175, t1: 7, t2: 11, A: 62.91, Ix: 13500, Iy: 984 },
  { id: "H-400x200x8x13", H: 400, B: 200, t1: 8, t2: 13, A: 83.37, Ix: 23500, Iy: 1740 },
  { id: "H-400x400x13x21", H: 400, B: 400, t1: 13, t2: 21, A: 218.7, Ix: 66600, Iy: 22400 },
  { id: "H-450x200x9x14", H: 450, B: 200, t1: 9, t2: 14, A: 95.43, Ix: 32900, Iy: 1870 },
  { id: "H-500x200x10x16", H: 500, B: 200, t1: 10, t2: 16, A: 112.3, Ix: 46800, Iy: 2140 },
  { id: "H-600x200x11x17", H: 600, B: 200, t1: 11, t2: 17, A: 131.7, Ix: 75600, Iy: 2270 },
];

interface RawSquareTube {
  id: string;
  /** Outer side B, mm. */
  B: number;
  /** Wall thickness t, mm. */
  t: number;
  /** cm^2 */
  A: number;
  /** cm^4 (Ix == Iy, doubly symmetric). */
  I: number;
}

const RAW_SQUARE_TUBES: RawSquareTube[] = [
  { id: "SQ-50x50x3.2", B: 50, t: 3.2, A: 5.73, I: 20.4 },
  { id: "SQ-75x75x3.2", B: 75, t: 3.2, A: 8.93, I: 75.5 },
  { id: "SQ-100x100x4.5", B: 100, t: 4.5, A: 16.6, I: 249 },
  { id: "SQ-100x100x6", B: 100, t: 6, A: 21.6, I: 311 },
  { id: "SQ-125x125x6", B: 125, t: 6, A: 27.6, I: 641 },
  { id: "SQ-150x150x6", B: 150, t: 6, A: 33.6, I: 1150 },
  { id: "SQ-175x175x6", B: 175, t: 6, A: 39.6, I: 1860 },
  { id: "SQ-200x200x8", B: 200, t: 8, A: 59.8, I: 3620 },
  { id: "SQ-250x250x9", B: 250, t: 9, A: 84.7, I: 8090 },
  { id: "SQ-300x300x9", B: 300, t: 9, A: 103, I: 14300 },
  { id: "SQ-350x350x12", B: 350, t: 12, A: 159, I: 29800 },
];

export interface SteelSectionPreset {
  id: string;
  label: string;
  /** m^2, m^4 (SI, matching this wizard's Sections step). */
  A: number;
  Iy: number;
  Iz: number;
  /** Approximate -- see module comment. */
  J: number;
}

const CM2_TO_M2 = 1e-4;
const CM4_TO_M4 = 1e-8;
const MM4_TO_M4 = 1e-12;

function hBeamJ(b: RawHBeam): number {
  // Two flanges + web, thin-rectangle sum: J = (1/3) * sum(b_i * t_i^3).
  const webHeight = b.H - 2 * b.t2;
  return (2 * b.B * b.t2 ** 3 + webHeight * b.t1 ** 3) / 3;
}

function squareTubeJ(s: RawSquareTube): number {
  // Closed thin-wall square tube, Bredt's formula: J = (B-t)^3 * t.
  return (s.B - s.t) ** 3 * s.t;
}

export const H_BEAM_PRESETS: SteelSectionPreset[] = RAW_H_BEAMS.map((b) => ({
  id: b.id,
  label: `${b.id} (A=${b.A}cm², Ix=${b.Ix}cm⁴)`,
  A: b.A * CM2_TO_M2,
  Iz: b.Ix * CM4_TO_M4, // strong axis -> local z in this app's frame convention
  Iy: b.Iy * CM4_TO_M4,
  J: hBeamJ(b) * MM4_TO_M4,
}));

export const SQUARE_TUBE_PRESETS: SteelSectionPreset[] = RAW_SQUARE_TUBES.map((s) => ({
  id: s.id,
  label: `${s.id} (A=${s.A}cm², I=${s.I}cm⁴)`,
  A: s.A * CM2_TO_M2,
  Iz: s.I * CM4_TO_M4,
  Iy: s.I * CM4_TO_M4,
  J: squareTubeJ(s) * MM4_TO_M4,
}));

/** Solid rectangular section, for RC members with no off-the-shelf catalog
 * entry: just a plug-the-numbers calculator, not a preset list. `widthM`
 * is the local-y extent, `depthM` the local-z extent (matching
 * FrameSection's Iy=∫z²dA / Iz=∫y²dA convention) -- callers that also
 * place rebar (SectionDiagram, the rebar quick-generator) must use the
 * same two numbers as the bars' y/z coordinate range, unmodified.
 *
 * Iy/Iz are computed directly from width/depth, NOT reordered by
 * magnitude -- an earlier version picked `b=min, h=max` before computing
 * Iy/Iz, which silently swapped which dimension got cubed whenever the
 * user's width happened to exceed their depth (e.g. a wide shallow slab
 * got the stiffness of a narrow tall beam instead). `short`/`long` below
 * are used ONLY for J's approximation formula, which genuinely requires
 * short<=long for its correction term to behave -- that requirement
 * doesn't apply to Iy/Iz.
 *
 * J uses the standard closed-form approximation for a solid rectangle
 * (Timoshenko & Goodier, "Theory of Elasticity") -- exact only in the
 * thin-wall limit, otherwise accurate to a few percent for ordinary
 * depth/width ratios. */
export function rectangularSection(widthM: number, depthM: number) {
  const A = widthM * depthM;
  const Iz = (depthM * widthM ** 3) / 12;
  const Iy = (widthM * depthM ** 3) / 12;
  const short = Math.min(widthM, depthM);
  const long = Math.max(widthM, depthM);
  const J =
    ((long * short ** 3) / 3) * (1 - 0.63 * (short / long) * (1 - short ** 4 / (12 * long ** 4)));
  return { A, Iy, Iz, J };
}
