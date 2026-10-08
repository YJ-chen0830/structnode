# StructNode

AI-native, solver-neutral structural engineering platform. StructNode
Frame (the first product) is a trustworthy linear-elastic 3D frame/truss
analysis tool built around an open **Canonical Engineering Model (CEM)**
— not a feature-complete commercial-solver clone.

> **Status: S0 (foundation).** Schema + validation only. No solver yet.
> Nothing in this repository should be used for engineering design.

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

See `docs/MASTER_PLAN.md` for the full plan.

## Development

```bash
uv sync --all-extras --dev
uv run structnode model validate examples/cantilever.cem.json --json
bash scripts/preflight.sh
```

## Repository layout

See `docs/MASTER_PLAN.md` section 7 for the target layout; `src/structnode/`
mirrors it as modules are implemented.
