# ADR 0007: Uniform member loads via fixed-end forces; end releases rejected

**Status:** Accepted (S10)

## Context

`member_distributed` and `gravity` have been valid `LoadKind`s since CEM
v0.1, but every solver rejected them. Real frame models (beam dead/live
load, self-weight) need both. Separately, `Element.releases` was accepted
by the schema but read by no solver: a released end was silently
assembled as rigid.

## Decision

### Load semantics

- **`member_distributed`**: `target_id` is an element id. `values` is a
  uniform force per unit **member length** (N/m) over the whole member --
  not per unit projected length, and no partial or trapezoidal spans.
  `coordinate_basis="global"` gives the vector in global axes; `"local"`
  gives it in member axes (x = node1 to node2; y/z as in ADR 0003 for 3D;
  in 2D, local y is local x rotated +90 degrees about global Z).
- **`gravity`**: `values` is an acceleration vector (m/s^2, e.g.
  `[0, -9.80665, 0]`), global axes only. `target_id` is one element id or
  `"*"` for every element. The resulting `w = rho * A * g` uses the
  element material's `rho` (missing: rejected) and the section's
  **gross** `A`, never the rebar-transformed `A_eff` (ADR 0006: `A_eff` is
  a stiffness abstraction, not real material). For RC, set `rho` to the
  reinforced-concrete unit mass so rebar weight is included.

Both kinds are scaled by `AnalysisCase.factors` like any other load
(ADR 0005).

### Frames: consistent fixed-end loads

Each loaded frame element contributes the standard fixed-fixed
equivalent nodal loads in local axes (`wL/2` forces at each end,
`wL^2/12` end moments; local-y-plane moments carry the opposite sign to
local-z-plane ones, mirroring frame3d's stiffness block), rotated to
global and added to the load vector. End-force recovery subtracts them
back out: `F_local = k_local @ u_local - f_fixed_end`. For
Euler-Bernoulli members this makes nodal displacements, reactions and
member end forces exact. Results still report end forces only, so the
parabolic moment between nodes is not tabulated (a midspan node gives it
exactly).

### Trusses: lumped, with a warning

A truss element has no rotational DOF, so `w` is lumped as `wL/2` to
each end node. Reactions and nodal displacements are those of the
pin-jointed idealization; the reported `N` is the mean axial force, and
any transverse bending of the member is not represented. Every such
element adds a result warning saying so -- an explicit, reported
approximation rather than a silent one. 3D truss elements have no
defined local y/z, so `coordinate_basis="local"` loads on them are
rejected.

### End releases: rejected until implemented

Any element whose `releases` contains `true` is rejected by both native
solvers and the OpenSees adapter (`UnsupportedModelError`). Supporting
them properly (static condensation of the released DOFs, plus
release-aware fixed-end forces) is future work.

## Consequences

- Out-of-plane member-load components (global or local z) are rejected by
  the 2D solver, like out-of-plane nodal loads.
- The OpenSees adapter still rejects both load kinds: it can't run in
  this environment, so an `eleLoad` mapping couldn't be verified.
- Verification: `tests/analytical/test_member_loads.py` checks each
  bending plane against closed-form cantilever and fixed-fixed results,
  local vs. global basis, 2D vs. 3D, gravity, load factors, and the truss
  lumping warning.
