# StructNode

AI-native, solver-neutral structural engineering platform. StructNode
Frame (the first product) is a trustworthy linear-elastic 2D/3D
frame/truss analysis tool built around an open **Canonical Engineering
Model (CEM)** — not a feature-complete commercial-solver clone.

> **Status: Alpha (S0–S10 implemented).** Linear-static 2D/3D truss and
> frame analysis (nodal, uniform member and self-weight loads; code load
> combinations; elastic transformed-section rebar), a model-builder
> wizard, a CLI, an MCP server, a REST API, Markdown reports, an
> (environment-dependent, unverified-by-execution) OpenSees cross-check
> adapter, and a minimal read-only web viewer. **Still experimental —
> nothing in this repository should be used for engineering design
> without independent review.**

## Non-negotiables

1. An LLM/agent is an untrusted intent translator, never the numerical
   solver or safety authority.
2. Every model edit is schema-validated, unit-checked, revisioned, and
   attributable.
3. Every analysis records model hash, solver name/version, settings,
   warnings, units, and load case.
4. `calculated`, `cross-checked`, `engineer-reviewed`, and
   `approved-for-design` are separate states — nothing defaults to
   design-fit.
5. CEM is open; export never requires a subscription or license.

See `docs/MASTER_PLAN.md` for the full plan, `docs/ROADMAP.md` for
what's done vs. not, and `docs/VERIFICATION_MATRIX.md` for how each
numerical claim is checked.

## Development

```bash
uv sync --all-extras --dev
uv run structnode model validate examples/cantilever.cem.json --json
uv run structnode analyze examples/cantilever_3d.cem.json --solver native-3d --output out/
bash scripts/preflight.sh
```

### MCP / REST

```bash
uv run structnode mcp serve --transport stdio
uv run structnode api serve --port 8000   # OpenAPI at /docs
```

### Web viewer

```bash
cd web && npm install && npm run dev
```

See `web/README.md`. Load a CEM file and (optionally) its matching
`analyze` results JSON to see the deformed shape — read-only, not the
source of truth for the model.

## Repository layout

See `docs/MASTER_PLAN.md` section 7 for the target layout;
`src/structnode/` mirrors it as modules are implemented. `web/` (the
viewer) is a separate Node/TypeScript project, not part of the Python
package.
