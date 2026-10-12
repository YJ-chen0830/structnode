// Pure geometry helpers: turn a CEM model (+ optional analysis results)
// into plain coordinate data. No Three.js here on purpose, so these are
// cheaply unit-testable without a WebGL context.

import type { AnalysisResults, CemModel } from "./types";

export interface Vec3 {
  x: number;
  y: number;
  z: number;
}

export interface Segment {
  elementId: string;
  a: Vec3;
  b: Vec3;
}

export interface Bounds {
  min: Vec3;
  max: Vec3;
  center: Vec3;
  /** Largest extent across all three axes; never zero, so cameras can
   * safely divide by it even for a single-point or degenerate model. */
  span: number;
}

export function nodePositions(model: CemModel): Map<string, Vec3> {
  const map = new Map<string, Vec3>();
  for (const node of model.nodes) {
    const [x, y, z] = node.position;
    map.set(node.id, { x, y, z });
  }
  return map;
}

/** Applies `results.displacements` to each node, scaled by `scale`.
 * Nodes with no entry in `displacements` (e.g. a 2D result applied to a
 * model loaded for 3D viewing) are left at their undeformed position --
 * never dropped, since that would silently misrepresent the model. */
export function deformedNodePositions(
  model: CemModel,
  results: AnalysisResults,
  scale: number,
): Map<string, Vec3> {
  const base = nodePositions(model);
  const deformed = new Map<string, Vec3>();
  for (const [id, pos] of base) {
    const disp = results.displacements[id];
    deformed.set(id, {
      x: pos.x + scale * (disp?.Ux ?? 0),
      y: pos.y + scale * (disp?.Uy ?? 0),
      z: pos.z + scale * (disp?.Uz ?? 0),
    });
  }
  return deformed;
}

export function elementSegments(model: CemModel, positions: Map<string, Vec3>): Segment[] {
  const segments: Segment[] = [];
  for (const el of model.elements) {
    const [n1, n2] = el.node_ids;
    const a = positions.get(n1);
    const b = positions.get(n2);
    if (!a || !b) continue; // dangling reference -- the Python validator rejects this; the viewer just skips it
    segments.push({ elementId: el.id, a, b });
  }
  return segments;
}

export function bounds(positions: Iterable<Vec3>): Bounds {
  let min: Vec3 = { x: Infinity, y: Infinity, z: Infinity };
  let max: Vec3 = { x: -Infinity, y: -Infinity, z: -Infinity };
  let any = false;
  for (const p of positions) {
    any = true;
    min = { x: Math.min(min.x, p.x), y: Math.min(min.y, p.y), z: Math.min(min.z, p.z) };
    max = { x: Math.max(max.x, p.x), y: Math.max(max.y, p.y), z: Math.max(max.z, p.z) };
  }
  if (!any) {
    return { min: { x: 0, y: 0, z: 0 }, max: { x: 0, y: 0, z: 0 }, center: { x: 0, y: 0, z: 0 }, span: 1 };
  }
  const center: Vec3 = {
    x: (min.x + max.x) / 2,
    y: (min.y + max.y) / 2,
    z: (min.z + max.z) / 2,
  };
  const span = Math.max(max.x - min.x, max.y - min.y, max.z - min.z, 1e-6);
  return { min, max, center, span };
}

/** A displacement scale that makes the largest single-axis
 * displacement roughly 15% of the model's own span -- enough to see,
 * not so much the deformed shape dwarfs the model. Falls back to 1 when
 * there's no results (or an all-zero response) to scale against. */
export function suggestedScale(model: CemModel, results: AnalysisResults | null): number {
  if (!results) return 1;
  const modelBounds = bounds(nodePositions(model).values());
  let maxDisp = 0;
  for (const disp of Object.values(results.displacements)) {
    maxDisp = Math.max(
      maxDisp,
      Math.abs(disp.Ux ?? 0),
      Math.abs(disp.Uy ?? 0),
      Math.abs(disp.Uz ?? 0),
    );
  }
  if (maxDisp < 1e-12) return 1;
  return (0.15 * modelBounds.span) / maxDisp;
}
