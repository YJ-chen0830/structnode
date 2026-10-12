// Minimal subset of the CEM v0.1 / analyze-results JSON shapes this
// viewer actually reads. Not a full schema mirror -- the Python side
// (src/structnode/core/model) is the source of truth; this is read-only
// display.

export interface CemNode {
  id: string;
  position: [number, number, number];
}

export interface CemElement {
  id: string;
  type: "truss" | "frame";
  node_ids: [string, string];
}

export interface CemModel {
  model_id: string;
  nodes: CemNode[];
  elements: CemElement[];
}

export type DisplacementComponents = Partial<{
  Ux: number;
  Uy: number;
  Uz: number;
  Rx: number;
  Ry: number;
  Rz: number;
}>;

export interface AnalysisResults {
  analysis_case_id: string;
  element_kind: string;
  solver_name: string;
  solver_version: string;
  model_hash?: string;
  displacements: Record<string, DisplacementComponents>;
  reactions: Record<string, Record<string, number>>;
  element_forces: Record<string, Record<string, number>>;
  warnings: string[];
}

export function isCemModel(value: unknown): value is CemModel {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return Array.isArray(v.nodes) && Array.isArray(v.elements) && typeof v.model_id === "string";
}

export function isAnalysisResults(value: unknown): value is AnalysisResults {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.displacements === "object" &&
    v.displacements !== null &&
    typeof v.solver_name === "string"
  );
}
