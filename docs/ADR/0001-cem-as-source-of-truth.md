# ADR 0001: CEM is the engineering source of truth; everything else is derived

**Status:** Accepted (S0)

## Context

Structural models get represented in many forms across a project's
life: a solver input deck, a CAD/BIM export, a mesh, a generated
report. If any of those derived forms is allowed to become
authoritative even temporarily, a round-trip through it can silently
drop information (a release, a local-axis orientation, a load case)
that nothing downstream can recover.

## Decision

The Canonical Engineering Model (`structnode.core.model.CEM`) is the
single source of truth. Every other representation — a 2D/3D solver's
internal matrices, an OpenSees model, a Markdown report, the web
viewer's Three.js scene — is derived from it and is read-only /
disposable. Conversions into or out of CEM must be explicit and, where
they can lose information, must say so (see ADR 0003 for a concrete
example: the 3D frame element's local-axis fallback emits a warning
rather than silently picking an orientation).

Concretely, this shows up as:
- `core/model` has no dependency on `fem`, `adapters`, `api`, `mcp`,
  `cli`, or `web` — those depend on it, never the reverse.
- Solvers (`fem/solvers`) and the OpenSees adapter
  (`adapters/opensees`) never mutate a `CEM` object; they read it and
  return a separate results structure.
- The web viewer (`web/`) only displays files already produced by the
  Python side; it has no model-editing or validation logic of its own.

## Consequences

- Every new integration (a future IFC importer, a future GUI editor)
  has one clear contract to satisfy: produce or consume valid CEM.
- Validation logic (`core/validation`) only has to be correct in one
  place.
- The cost is indirection: nothing can shortcut straight from, say, an
  OpenSees model to a report without going back through CEM-shaped
  results. Accepted as the right trade for auditability.
