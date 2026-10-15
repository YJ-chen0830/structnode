# CEM v0.1 Model Format

The Canonical Engineering Model (CEM) is the engineering source of
truth (see `docs/ADR/0001-cem-as-source-of-truth.md`). The Pydantic
models in `src/structnode/core/model/cem.py` are the authoritative
definition; this file is a map of that definition, not a duplicate of
it — when the two disagree, the code wins.

A machine-readable JSON Schema export lives at
`schemas/cem/v0.1/cem.schema.json`, regenerated with:

```bash
uv run python -c "
import json
from pathlib import Path
from structnode.core.model import CEM
Path('schemas/cem/v0.1/cem.schema.json').write_text(
    json.dumps(CEM.model_json_schema(), indent=2, sort_keys=True) + '\n'
)
"
```

Regenerate it whenever `cem.py` changes and the two drift.

## Top-level document

| Field | Type | Notes |
|---|---|---|
| `schema_version` | `"0.1"` | Only value accepted in v0.1. |
| `model_id` | string | |
| `revision` | int, >= 0 | Bumped by every `core.editing.apply_command` call. |
| `units` | `{length, force}` | Declares the *source* unit convention; stored values are always SI internally. |
| `coordinate_system` | `"global_cartesian_rh"` | Only value in v0.1. |
| `nodes`, `materials`, `sections`, `elements`, `constraints`, `load_cases`, `loads`, `analysis_cases` | lists | See below. IDs must be unique within each list. |
| `metadata` | object | Freeform. |
| `provenance` | `{created_by, created_at, parent_revision, tool_version}` | `created_by` is `"human"`, `"agent:<name>"`, or `"import:<source>"`. |

## Collections

- **`nodes`**: `id`, `position` (SI meters, `[x, y, z]`).
- **`materials`**: `id`, `E` (Pa, required), `G` (Pa, optional — if
  absent, solvers needing shear modulus derive it from `E`/`nu`; see
  `fem/assembly/assemble3d.py:resolve_shear_modulus`), `rho`
  (kg/m³, optional), `nu` (optional). If both `G` and `nu` are given
  they must be mutually consistent (checked at validation time).
- **`sections`**: `id`, `A`, `Iy`, `Iz`, `J` (SI, all > 0),
  `local_axis_hint` (optional 3-vector; see
  `docs/ADR/0003-local-axis-fallback-convention.md` for what happens
  when it's omitted), `rebar` (optional: `material_id` + `bars` (each
  `y`, `z`, `diameter`) -- transformed-section stiffness contribution
  only, not a strength/capacity-design representation; see
  `docs/ADR/0006-rebar-transformed-section.md`). `bars` must be
  mirror-symmetric about the local y=0 or z=0 axis (checked at
  validation time) -- an asymmetric layout would have a nonzero
  product of inertia this project's decoupled Iy/Iz frame elements
  can't represent.
- **`elements`**: `id`, `type` (`"truss"` or `"frame"`), `node_ids`
  (exactly 2, distinct), `material_id`, `section_id`, `releases`
  (optional; `None` for truss, 12 booleans for frame -- no solver
  supports a `true` release yet, so any is rejected at analysis time;
  see ADR 0007).
- **`constraints`** (supports): `node_id`, `dofs` (6 booleans:
  `Tx,Ty,Tz,Rx,Ry,Rz`).
- **`load_cases`**: `id`, `description` (optional).
- **`loads`**: `id`, `case_id`, `kind`
  (`"nodal_force" | "nodal_moment" | "member_distributed" | "gravity"`),
  `target_id`, `values` (3-tuple), `coordinate_basis`
  (`"global" | "local"`). Nodal loads target a node and must be
  `"global"`. `member_distributed` targets an element: uniform N/m per
  unit member length, in global or member-local axes. `gravity` targets
  an element id or `"*"` (all elements): `values` is an acceleration
  (m/s², global only) applied to `rho * A` (gross `A`). See
  `docs/ADR/0007-uniform-member-loads.md`, including that truss elements
  get these lumped to their end nodes, with a result warning.
- **`analysis_cases`**: `id`, `load_case_ids`, `method`
  (`"linear_static"` only in v0.1), `factors` (optional, same length/order
  as `load_case_ids` — per-case scale factors for linear superposition,
  e.g. `[1.2, 1.6]` over `["D", "L"]` for a "1.2D + 1.6L" code load
  combination; omitted or `null` means every case contributes at 1.0),
  `solver_options`.

## What's intentionally excluded from v0.1

Plates/shells, soil springs, geometric/material nonlinearity, staged
construction, seismic code design, moving loads, temperature gradients,
detailed RC design. Adding any of these is a schema migration, not a
silent extension — see `docs/MASTER_PLAN.md` section 3.
