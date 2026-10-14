# ADR 0006: Rebar affects stiffness via the elastic transformed-section method, not RC capacity design

**Status:** Accepted (S9)

## Context

A user pointed out that `FrameSection` (A, Iy, Iz, J) has no way to
represent embedded reinforcement -- for an RC member, "the rebar isn't
considered at all" felt wrong. They asked for rebar to genuinely affect
analysis results, not just be decorative metadata.

The solver only supports `method = "linear_static"`, and
`docs/MASTER_PLAN.md`'s "CEM v0.1 exclusions" explicitly rules out
"detailed RC design" (capacity checks, M-N interaction diagrams). Any
path where rebar affects results has to both (a) actually change the
numbers a linear elastic solve produces, and (b) not quietly reopen
that exclusion.

## Decision

Rebar affects stiffness via the **elastic transformed-section method**:
each bar's area is scaled by `(n-1)` (`n = E_rebar / E_element`, the
modular ratio) and combined with the gross section to produce an
effective `A`/`Iy`/`Iz`, using the general parallel-axis form (shifting
to the composite centroid, not assuming it stays put). This is the
textbook-standard technique for *serviceability/deflection* calculations
under elastic assumptions -- categorically different from
strength/capacity design (rebar ratio limits, development length, M-N
interaction, etc.), which stays excluded.

`J` (torsional constant) is never adjusted: longitudinal rebar's
contribution to torsional stiffness is treated as negligible, standard
practice for this kind of elastic section-property calculation.

**Uncracked section only.** Real RC stiffness is load-magnitude- and
sign-dependent (cracked vs. uncracked), which is inherently nonlinear.
v1 always uses the full uncracked transformed section regardless of load
-- a known, stated simplification, not a hidden one. Cracked-section
analysis would be a `linear_static`-incompatible feature addition, not
something to approximate here.

**Mirror-symmetry requirement, not a "balanced centroid" check.** An
earlier draft of this feature checked only that the rebar layout's own
(`n-1`-weighted) centroid landed near the section's local origin. That
check is necessary but not sufficient: it doesn't rule out a nonzero
product of inertia `Iyz = Σ(n-1)·a_i·y_i·z_i` (e.g. bars placed only on
a diagonal). A nonzero `Iyz` means the transformed section's principal
axes are rotated relative to local y/z -- and this project's frame
elements (`frame2d.py`/`frame3d.py`) only implement decoupled Iy/Iz
bending, with no `Iyz` term anywhere. Silently accepting such a layout
would produce an `Iy_eff`/`Iz_eff` that quietly drops a real coupling
term -- exactly the "silently approximated" outcome
`docs/MASTER_PLAN.md`'s non-negotiables forbid.

Instead, `RebarLayout` requires mirror symmetry about *at least one*
local axis (every bar has a same-diameter partner at the reflected
position across y=0 or across z=0, or sits exactly on that axis). This
condition:

- Provably zeroes `Iyz`, and does so **independent of `n`** -- a mirror
  pair's contribution to the `Iyz` sum cancels regardless of the actual
  `(n-1)` value, since it's a common factor across the pair.
- Needs no section geometry (width/height/shape) -- `FrameSection` is
  shape-agnostic (only derived A/Iy/Iz, no width/height), so the check
  can only ever look at the bars themselves.
- Still allows the common real case of unequal top/bottom steel (e.g. 3
  bars bottom, 2 top in a beam), as long as the layout is left-right
  symmetric -- stricter than necessary would reject valid, common
  layouts; this is the loosest condition that's still provably correct.

Because the check needs no cross-reference to `cem.elements`/`cem.materials`,
it lives as a pydantic `model_validator` directly on `RebarLayout`
(`structnode/core/model/cem.py`), using exact coordinate/diameter
matching (not an `Iyz`-magnitude tolerance) -- simpler to reason about
and test.

**Computed at assembly time, not stored pre-computed.** A `FrameSection`
can be shared by elements with different materials (`Element.material_id`
and `.section_id` are independent fields), so the modular ratio --
and therefore the effective A/Iy/Iz -- can differ per element even for
the same section. `structnode/fem/rebar.py`'s
`effective_section_properties()` is called from both `assemble2d.py` and
`assemble3d.py` right where `section = sections[el.section_id]` is
already looked up, using the actual element's material.

**Truss elements may also reference a rebar-bearing section.** Only `A`
matters for truss stiffness, and a transformed axial area is
mathematically ordinary (composite-rod axial stiffness) -- no reason to
special-case reject it.

## Consequences

- `FrameSection.rebar` is optional and additive; omitting it reproduces
  the exact pre-existing behavior (plain A/Iy/Iz, no change).
- `RebarLayout.material_id` must reference an existing `Material`
  (checked in `core/validation/topology.py`, new `CEM-REF-REBAR-MATERIAL`
  finding) -- typically a steel grade, but nothing enforces that beyond a
  `CEM-REBAR-LOW-MODULUS` *warning* (not an error) when the rebar
  material's `E` isn't greater than the host element's own material `E`
  (`n <= 1`), which is almost always an accidentally-swapped material
  pick rather than a deliberately modeled case.
- **Self-weight forward-compat trap**: `gravity`/`member_distributed`
  loads are already rejected outright by both assemblers today, so there
  is no live conflict. But when gravity loads are eventually
  implemented, self-weight mass must be computed from the **gross** `A`
  (times concrete density), never `A_eff` -- the transformed area is a
  stiffness-equivalent abstraction, not a real quantity of material, and
  using it for mass would silently double-count the steel's weight.
