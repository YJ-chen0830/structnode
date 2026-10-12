# ADR 0003: 3D frame local-axis fallback is tied to a fixed global reference, and must warn when used

**Status:** Accepted (S3)

## Context

A 3D frame element's cross-section has two bending stiffnesses (`Iy`,
`Iz`), so resolving its local y/z axes from the member's direction
alone is ambiguous — you need a reference vector. `CEM.FrameSection`
has an optional `local_axis_hint` for this; when it's absent, something
must still be chosen.

While writing the rotation-invariance benchmark
(`test_benchmark_5_rotation_invariance`,
`tests/analytical/test_benchmarks_3d.py`), the first version of the
test rigidly rotated a cantilever's geometry and load but *not* its
(absent) `local_axis_hint`, and failed: the rotated case's deflection
differed from the un-rotated case's by a few percent, not to floating
point. This was not a bug in the stiffness matrix (which was already
independently verified via the `Iy`-vs-`Iz` bending benchmarks) — it
was a product of the design decision below, discovered empirically
rather than planned in advance.

## Decision

`frame3d_local_axes` (`src/structnode/fem/elements/frame3d.py`) resolves
the local y/z axes from `local_axis_hint` when given. When it's absent,
it falls back to global Z as the reference vector (or global Y if the
member itself is near-parallel to global Z), and — per
`MASTER_PLAN.md` section 3's "adapters/solvers fall back to a default
rule ... and MUST report that fallback as a warning" — returns a
warning string that `fem/assembly/assemble3d.py` collects and
`solve_linear_static_3d` surfaces in the result payload's `warnings`.

The consequence worth stating explicitly: **this fallback reference is
a fixed direction in global space, not a property that travels with
the member.** Rigidly rotating a model without also rotating its
members' `local_axis_hint` values changes each member's cross-section
orientation relative to that fixed reference — a different physical
setup (the beam's "up" direction relative to its own axis has
changed), not the same beam viewed from a different angle. For a
doubly-symmetric section (`Iy == Iz`) this is invisible, since bending
stiffness doesn't depend on the y/z labeling. For anything else, it
matters.

## Consequences

- The rotation-invariance benchmark passes `local_axis_hint` explicitly
  on both the baseline and rotated cases, rotating the hint by the same
  transform as the geometry — and its docstring states why, so a future
  reader doesn't "fix" the test by removing that explicit hint.
- Any caller that cares about true rotation/orientation invariance
  (notably: the OpenSees adapter's cross-check, and any future
  mesh-generation or model-transformation tool) must propagate
  `local_axis_hint` through whatever transform it applies, not drop it.
- The OpenSees adapter (`adapters/opensees/adapter.py`) passes a
  reference vector to OpenSees's own `geomTransf` using a *different*
  cross-product convention than this project's own — flagged in that
  adapter's docstring as unverified for `Iy != Iz` sections, and the
  cross-solver benchmark deliberately uses a doubly-symmetric section to
  sidestep the question until someone can verify it by execution (see
  ADR 0004).
