// Full CEM v0.1 shape, for the model-builder UI -- unlike types.ts
// (the viewer's read-only subset), this needs every field the REST API
// expects to construct a valid payload. Manually mirrors
// structnode.core.model.cem on the Python side, which remains the
// actual source of truth and the only place that validates (see
// docs/ADR/0001-cem-as-source-of-truth.md, docs/MODEL_FORMAT.md). If
// this drifts from the Python schema, the REST API's own validation
// errors are what to trust, not this file.

import type { CemElement, CemNode } from "./types";

export interface Units {
  length: "m" | "mm" | "cm" | "ft" | "in";
  force: "N" | "kN" | "lbf" | "kip";
}

export interface Material {
  id: string;
  E: number;
  G?: number;
  rho?: number;
  nu?: number;
}

export interface FrameSection {
  id: string;
  A: number;
  Iy: number;
  Iz: number;
  J: number;
  local_axis_hint?: [number, number, number];
}

export interface FullElement extends CemElement {
  material_id: string;
  section_id: string;
  releases?: boolean[] | null;
}

export interface Support {
  node_id: string;
  dofs: [boolean, boolean, boolean, boolean, boolean, boolean];
}

export interface LoadCase {
  id: string;
  description?: string;
}

export type LoadKind = "nodal_force" | "nodal_moment" | "member_distributed" | "gravity";

export interface Load {
  id: string;
  case_id: string;
  kind: LoadKind;
  target_id: string;
  values: [number, number, number];
  coordinate_basis: "global" | "local";
}

export interface AnalysisCase {
  id: string;
  load_case_ids: string[];
  method: "linear_static";
  /** Optional per-load-case scale factors, same length/order as
   * load_case_ids -- lets one AnalysisCase represent a code load
   * combination (e.g. "1.2D + 1.6L") instead of duplicating load data. */
  factors?: number[];
  solver_options?: Record<string, never>;
}

export interface Provenance {
  created_by: string;
  created_at: string;
  parent_revision: string | null;
  tool_version: string;
}

export interface FullCemModel {
  schema_version: "0.1";
  model_id: string;
  revision: number;
  units: Units;
  coordinate_system: "global_cartesian_rh";
  nodes: CemNode[];
  materials: Material[];
  sections: FrameSection[];
  elements: FullElement[];
  constraints: Support[];
  load_cases: LoadCase[];
  loads: Load[];
  analysis_cases: AnalysisCase[];
  metadata: Record<string, never>;
  provenance: Provenance;
}

export function emptyModel(modelId: string): FullCemModel {
  return {
    schema_version: "0.1",
    model_id: modelId,
    revision: 0,
    units: { length: "m", force: "N" },
    coordinate_system: "global_cartesian_rh",
    nodes: [],
    materials: [],
    sections: [],
    elements: [],
    constraints: [],
    load_cases: [],
    loads: [],
    analysis_cases: [],
    metadata: {},
    provenance: {
      created_by: "human",
      created_at: new Date().toISOString(),
      parent_revision: null,
      tool_version: "web-builder-0.1.0",
    },
  };
}
