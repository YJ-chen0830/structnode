# ADR 0002: Keep separate native-2d and native-3d solvers rather than one unified engine

**Status:** Accepted (S3)

## Context

`MASTER_PLAN.md`'s Phase 1 numerical methods sequence is "2D truss → 2D
frame → 3D truss → 3D frame," implemented in that order (S2, then S3).
By the end of S3, the 3D solver is a strict superset of what the 2D
solver can represent — any planar model with explicit out-of-plane
restraints solves correctly under the 3D engine too. The question was
whether to deprecate `native-2d` once `native-3d` existed.

## Decision

Keep both as separate, explicit solver backends
(`fem/solvers/linear_static_2d.py`, `fem/solvers/linear_static_3d.py`),
selectable via `--solver native-2d` / `native-3d` (and `native` as an
alias for `native-2d`, preserved for backward compatibility with
S2-era CLI usage).

The reason is the DOF model, not convenience: `native-2d` only ever
creates 2 (truss) or 3 (frame) DOF per node and never creates the
out-of-plane ones at all, so a purely 2D structure is stable by
construction. `native-3d` creates the full 6 DOF per node — including
transverse translation and out-of-plane rotations a truss element has
*zero* stiffness against. Lifting a "2D-looking" model into the 3D
engine without the modeler explicitly adding out-of-plane restraints at
every node produces a singular system, correctly rejected by
`SingularStiffnessError` rather than solved. That's not a limitation to
paper over; real 3D FEA tools have the identical requirement. Keeping
`native-2d` means a genuinely 2D problem doesn't force the modeler to
reason about restraints their structure doesn't conceptually have.

## Consequences

- Two element-stiffness/assembly/solver code paths to maintain in
  parallel (`fem/elements/{truss,frame}{2d,3d}.py`,
  `fem/assembly/assemble{2d,3d}.py`,
  `fem/solvers/linear_static_{2d,3d}.py`). Mitigated by sharing what
  can be shared: `fem/assembly/errors.py` and `fem/solvers/errors.py`
  hold exception types used by both, so callers (CLI/MCP/REST) only
  ever catch one type per failure mode regardless of which engine ran.
- `tests/analytical/test_2d_3d_agreement.py` exists specifically
  because two independent implementations are supposed to agree on
  their overlapping domain (planar models, in-plane loads) — that
  agreement is now a regression-tested invariant, not just an
  assumption.
- A future "auto" solver mode that picks 2D vs. 3D based on model
  geometry was considered and rejected: CEM has no declared
  dimensionality field, so "this model happens to be planar" is a
  geometric coincidence, not stated modeler intent, and silently acting
  on it would violate the "no unsupported feature is silently
  approximated" principle in spirit even though it's not literally an
  unsupported feature.
