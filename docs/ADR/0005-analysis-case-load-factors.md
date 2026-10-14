# ADR 0005: Code load combinations are per-case factors on AnalysisCase, not duplicated load data

**Status:** Accepted (S8)

## Context

Taiwan building-code practice (LRFD/極限設計法 and ASD/容許應力法 alike)
expresses design loads as combinations of base load cases with scale
factors, e.g. `1.2D + 1.6L` or `0.9D + 1.0E`. Before this change,
`AnalysisCase.load_case_ids` only let a case *select* load cases, always
summed at 1.0 — expressing a weighted combination meant either
duplicating each `Load` under a pre-scaled copy (one scaled-D load case
per combination that uses D), or not supporting combinations at all.

Duplicating load data defeats the point of defining `D`/`L`/`E`/... once:
every combination would need its own scaled copy of every load that
participates, multiplying data entry and creating room for the copies to
drift from the original.

## Decision

`AnalysisCase` gets an optional `factors: tuple[float, ...] | None` field,
same length and order as `load_case_ids`. `None` (the default) preserves
the old unweighted-sum behavior. When present, `AnalysisCase.case_factors()`
returns a `{case_id: factor}` mapping that `fem/assembly/{assemble2d,
assemble3d}.py`'s `build_load_vector` and the OpenSees adapter multiply
each load's contribution by, before summing — exact linear superposition,
valid because `method` is `"linear_static"` only in v0.1.

This is additive and backward-compatible: existing CEM files without
`factors` validate and solve identically to before.

## Consequences

- A code load combination is data, not a web-UI-only concept: a combo
  generator (or a hand-written CEM file) just adds one `AnalysisCase`
  entry with `factors`, referencing the project's existing `D`/`L`/`Lr`/
  `W`/`E` load cases.
- `build_load_vector` in both 2D and 3D assembly now takes a
  `case_factors: Mapping[str, float]` instead of a bare sequence of case
  IDs — any future direct caller must build that mapping (typically via
  `analysis_case.case_factors()`) rather than passing `load_case_ids`.
- Still only linear superposition: this does not and must not generalize
  to nonlinear methods without separate review, since factored-then-summed
  loads are not equivalent to solving a nonlinear system under the
  combined load directly.
