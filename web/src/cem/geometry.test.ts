import { describe, expect, it } from "vitest";
import {
  bounds,
  deformedNodePositions,
  elementSegments,
  nodePositions,
  suggestedScale,
} from "./geometry";
import type { AnalysisResults, CemModel } from "./types";

const cantilever: CemModel = {
  model_id: "cantilever-demo",
  nodes: [
    { id: "N1", position: [0, 0, 0] },
    { id: "N2", position: [1, 0, 0] },
  ],
  elements: [{ id: "E1", type: "frame", node_ids: ["N1", "N2"] }],
};

const results: AnalysisResults = {
  analysis_case_id: "AC1",
  element_kind: "frame",
  solver_name: "structnode-native-2d",
  solver_version: "0.1.0",
  displacements: {
    N1: { Ux: 0, Uy: 0 },
    N2: { Ux: 0, Uy: -0.0002, Rz: -0.0003 },
  },
  reactions: {},
  element_forces: {},
  warnings: [],
};

describe("nodePositions", () => {
  it("maps node ids to their (x,y,z) position", () => {
    const positions = nodePositions(cantilever);
    expect(positions.get("N2")).toEqual({ x: 1, y: 0, z: 0 });
  });
});

describe("deformedNodePositions", () => {
  it("applies scaled displacements", () => {
    const deformed = deformedNodePositions(cantilever, results, 100);
    expect(deformed.get("N2")).toEqual({ x: 1, y: -0.02, z: 0 });
  });

  it("leaves nodes with no displacement entry at their undeformed position", () => {
    const sparse: AnalysisResults = { ...results, displacements: {} };
    const deformed = deformedNodePositions(cantilever, sparse, 100);
    expect(deformed.get("N1")).toEqual({ x: 0, y: 0, z: 0 });
    expect(deformed.get("N2")).toEqual({ x: 1, y: 0, z: 0 });
  });

  it("treats a missing Uz (2D results) as zero rather than NaN", () => {
    const deformed = deformedNodePositions(cantilever, results, 1);
    expect(deformed.get("N2")?.z).toBe(0);
  });
});

describe("elementSegments", () => {
  it("builds a segment per element from its two node positions", () => {
    const positions = nodePositions(cantilever);
    const segments = elementSegments(cantilever, positions);
    expect(segments).toEqual([
      { elementId: "E1", a: { x: 0, y: 0, z: 0 }, b: { x: 1, y: 0, z: 0 } },
    ]);
  });

  it("skips elements with a dangling node reference instead of throwing", () => {
    const broken: CemModel = {
      ...cantilever,
      elements: [{ id: "E2", type: "truss", node_ids: ["N1", "N404"] }],
    };
    const positions = nodePositions(broken);
    expect(elementSegments(broken, positions)).toEqual([]);
  });
});

describe("bounds", () => {
  it("computes min/max/center/span across all points", () => {
    const positions = nodePositions(cantilever);
    const b = bounds(positions.values());
    expect(b.min).toEqual({ x: 0, y: 0, z: 0 });
    expect(b.max).toEqual({ x: 1, y: 0, z: 0 });
    expect(b.center).toEqual({ x: 0.5, y: 0, z: 0 });
    expect(b.span).toBe(1);
  });

  it("never returns a zero span, even for a single point", () => {
    const b = bounds([{ x: 5, y: 5, z: 5 }]);
    expect(b.span).toBeGreaterThan(0);
  });

  it("handles an empty iterable without throwing", () => {
    const b = bounds([]);
    expect(b.span).toBe(1);
  });
});

describe("suggestedScale", () => {
  it("returns 1 when there are no results to scale against", () => {
    expect(suggestedScale(cantilever, null)).toBe(1);
  });

  it("scales so the largest displacement is ~15% of the model span", () => {
    const scale = suggestedScale(cantilever, results);
    // model span = 1 (N1 to N2 along x); max |displacement| = 0.0003 (Uy's not it -- Rz
    // is a rotation, not a translation, so the relevant max is |Uy|=0.0002)
    expect(scale).toBeCloseTo((0.15 * 1) / 0.0002, 6);
  });

  it("falls back to 1 when the response is effectively zero", () => {
    const zeroResults: AnalysisResults = {
      ...results,
      displacements: { N1: { Ux: 0, Uy: 0 }, N2: { Ux: 0, Uy: 0 } },
    };
    expect(suggestedScale(cantilever, zeroResults)).toBe(1);
  });
});
