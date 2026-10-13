# Verification Matrix

Links each numerical/engineering-safety requirement to the benchmark
that checks it, where that benchmark lives, and its last known status.
Per `MASTER_PLAN.md` section 10. "Reviewer" is whoever last confirmed
the row is accurate — for an AI-assisted alpha, that's explicitly
named rather than left blank, since "reviewed" should mean a person (or
the agent, named as such) actually looked, not that review was implied.

| # | Requirement | Benchmark | Location | Tolerance | Last result | Reviewer |
|---|---|---|---|---|---|---|
| 1 | Axial bar: `u=PL/(EA)` | `test_benchmark_1_axial_bar` | `tests/analytical/test_benchmarks_2d.py` | rel. 1e-6 | Pass | Claude (agent), S2 |
| 1b | 3D axial element formula (off-axis bar) | `test_truss3d_element_matches_axial_formula` | `tests/analytical/test_benchmarks_3d.py` | rel. 1e-6 | Pass | Claude (agent), S3 |
| 2 | Simply supported beam, midspan load: `delta=PL^3/(48EI)`, reactions `P/2` | `test_benchmark_2_simply_supported_beam_midspan_load` | `tests/analytical/test_benchmarks_2d.py` | rel. 1e-6 | Pass | Claude (agent), S2 |
| 3 | Cantilever, tip load: `delta=PL^3/(3EI)`, tip rotation `PL^2/(2EI)` | `test_benchmark_3_cantilever_tip_load` | `tests/analytical/test_benchmarks_2d.py` | rel. 1e-6 | Pass | Claude (agent), S2 |
| 3b | Same, independently for both 3D bending planes (Iy vs Iz) | `test_cantilever_bending_about_local_z_uses_Iz`, `test_cantilever_bending_about_local_y_uses_Iy` | `tests/analytical/test_benchmarks_3d.py` | rel. 1e-6 | Pass | Claude (agent), S3 |
| 4 | Symmetric truss: reactions, member forces, displacement symmetry | `test_benchmark_4_symmetric_truss` | `tests/analytical/test_benchmarks_2d.py` | rel. 1e-6 | Pass | Claude (agent), S2 |
| 5 | 3D frame: local-to-global rotation invariance and member orientation | `test_benchmark_5_rotation_invariance` | `tests/analytical/test_benchmarks_3d.py` | rel. 1e-6 (translation + rotation) | Pass (holds only with `local_axis_hint` rotated along with geometry -- see docstring and ADR 0003) | Claude (agent), S3 |
| 6 | Rigid-body mode: correctly fail unstable models | `test_benchmark_6_rigid_body_mode_is_rejected` (2D), `test_benchmark_6_3d_rigid_body_mode_is_rejected` (3D) | `tests/analytical/test_benchmarks_{2d,3d}.py` | n/a (must raise `SingularStiffnessError`) | Pass | Claude (agent), S2/S3 |
| 7 | Mesh refinement / split-element invariance | `test_benchmark_7_mesh_refinement_invariance` | `tests/analytical/test_benchmarks_3d.py` | rel. 1e-6 | Pass | Claude (agent), S3 |
| 8 | Cross-solver OpenSees comparison, documented mapping and tolerances | `test_native_3d_matches_opensees_cantilever` | `tests/analytical/test_cross_solver_opensees.py` | rel. 1e-4 | **Skipped** -- `openseespy` doesn't import in this environment; never executed (see `docs/ROADMAP.md` S4 caveat and ADR 0004) | Claude (agent), S4 — unverified by execution |
| 9 (extra) | Global equilibrium on a non-axis-aligned 3D load path (bending-torsion coupling across two members) | `test_lframe_reactions_balance_applied_load_moment`, `test_lframe_internal_end_forces_match_reactions_at_base` | `tests/analytical/test_lframe_3d_equilibrium.py` | rel. 1e-6 | Pass | Claude (agent), S3 |
| 10 (extra) | Agent tool contract: no unsafe direct execution (`model_snapshot` never writes without `confirm=True`) | `test_model_snapshot_default_confirm_false_writes_nothing` (MCP), equivalent in `test_api.py` (REST) | `tests/unit/test_mcp_server.py`, `tests/unit/test_api.py` | n/a (asserts no file written) | Pass | Claude (agent), S5 |
| 11 (extra) | 2D and 3D solvers agree exactly on an equivalent planar model | `test_2d_and_3d_solvers_agree_on_equivalent_planar_cantilever` | `tests/analytical/test_2d_3d_agreement.py` | rel. 1e-9 (displacements/reactions only; `element_forces` naming differs by design, see test docstring) | Pass | Claude (agent), S6 |
| 12 (extra) | `AnalysisCase.factors`-weighted combination equals manual linear superposition of single-case solves, in both 2D and 3D | `test_2d_combo_equals_linear_superposition_of_factored_cases`, `test_3d_combo_equals_linear_superposition_of_factored_cases` | `tests/unit/test_load_combinations.py` | rel. (`pytest.approx` default) | Pass | Claude (agent), S8 — see ADR 0005 |

## Scope not covered by any benchmark (by design, not oversight)

Mixed truss/frame element types, `member_distributed`/`gravity` loads,
`coordinate_basis="local"` loads, shear deformation, plates/shells, any
nonlinearity. All of these are explicitly rejected by the solvers
(`UnsupportedModelError`) rather than silently approximated — there is
nothing to benchmark because there is no code path that produces a
result for them. See `docs/MASTER_PLAN.md` section 3, "CEM v0.1
exclusions."

## Follow-ups

- Row 8 needs a real execution once `openseespy` is available somewhere
  in CI or a contributor's environment.
