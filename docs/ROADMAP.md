# Roadmap

Tracks the 90-day plan in `MASTER_PLAN.md` section 8 against what's
actually implemented. Updated at the end of each sprint branch, not
aspirationally — if a box isn't checked, it isn't done.

## Sprints

| Sprint | Deliverable | Status | PR |
|---|---|---|---|
| S0 | Repo, AGENTS.md, CI, package skeleton, CEM schema | Done | #1 |
| S1 | Units, model editing commands, topology validator, versioned snapshots | Done | #2 |
| S2 | 2D truss/frame solver + analytic benchmarks | Done | #3 |
| S3 | 3D truss/frame solver, sparse assembly | Done | #4 |
| S4 | CLI, result schema, Markdown reports, OpenSees adapter | Done, with a caveat (below) | #5 |
| S5 | MCP server, REST API, permissions, model diff/dry-run | Done | #6 |
| S6 | Minimal web viewer, examples, docs, alpha release | This PR | #7 |

**S4 caveat:** the OpenSees adapter (`src/structnode/adapters/opensees/`)
is implemented against the documented OpenSeesPy API but has never
executed against a live OpenSeesPy process — `openseespy` doesn't
import in this project's development environment (Windows; confirmed
failing on both the project's Python 3.14 and the system's Python
3.11, a known class of issue for openseespy on Windows, not a bug in
this repo). `capabilities()`/`is_available()` report this honestly, the
CLI/MCP/REST surfaces return a typed "unavailable" error instead of
crashing, and the cross-solver benchmark
(`tests/analytical/test_cross_solver_opensees.py`) is `skip`ped with
that reason rather than faking a pass. Whoever next runs this where
`openseespy` actually imports (Linux/WSL is more reliable) should treat
that first run as the real verification.

**Stretch items (Master Plan: "only after core gates") not attempted:**
DXF import, IFC mapping, auto load combinations, section library,
MIDAS REST adapter. Explicitly out of scope for the alpha.

## Alpha exit criteria (Master Plan section 8)

| Criterion | Status |
|---|---|
| 10+ deterministic benchmark models; all required tests green | Met — see `docs/VERIFICATION_MATRIX.md`; `tests/analytical/` + `examples/` together exceed 10 distinct models |
| 2D/3D linear frame and truss supported with explicit assumptions and warnings | Met — scope guards in `fem/assembly/*` reject rather than approximate; `frame3d.py`'s local-axis fallback warns |
| Full pipeline reproducible on fresh clone without paid MIDAS | Met for the Python/CLI/MCP/REST/viewer path (`uv sync && bash scripts/preflight.sh`, `cd web && npm ci && npm run build`); MIDAS adapter was never implemented (P1+ scope), so nothing here depends on it |
| CLI and MCP expose equivalent validated commands | Met — both are thin adapters over `src/structnode/service.py`; `tests/unit/test_mcp_server.py` exercises the real tool-calling path |
| Every analysis output records input/solver provenance and errors | Met — `model_hash`, `solver_name`/`solver_version`, `warnings`, typed `errors` on every `analyze`/`analysis_run` result |
| No unsupported feature is silently approximated | Met by design throughout — every scope guard (mixed element types, non-planar 2D models, `member_distributed`/`gravity` loads, unavailable OpenSees) raises a typed error instead of a silent fallback |
| At least one third-party agent can create, analyze, and report a model using only published tools | **Not independently verified.** The MCP/REST tool contract exists and is tested via `MCPServer.call_tool`/FastAPI `TestClient`, but no agent outside this development process has exercised it end-to-end. Flagged as the one unmet/unverified criterion for this alpha. |

## What's next (post-alpha, not committed to a sprint)

- Independent third-party agent trial against the MCP/REST surface (the
  one unmet exit criterion above).
- Run the OpenSees adapter somewhere it actually imports; fix whatever
  the first real run surfaces.
- Mixed truss/frame element types in one model (currently rejected by
  every solver as a documented S2-era scope guard).
- `member_distributed` and `gravity` loads (currently rejected, not
  approximated).
- Code-splitting the web viewer bundle (Three.js dominates the current
  ~775 KB bundle; fine for a local dev-server viewer, worth revisiting
  before any hosted deployment).
