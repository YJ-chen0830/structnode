# StructNode Viewer

A minimal, read-only 3D viewer for CEM models and `structnode analyze`
results. Per `docs/MASTER_PLAN.md` section 2: "Web-first 3D viewer; not
source of truth" -- it only displays files produced elsewhere; it never
edits or validates a model (that's the Python CLI/MCP/REST).

> **Status:** S6 alpha scope. No remote backend, no persistence -- you
> load local JSON files in the browser and nothing leaves your machine.

## Run it

```bash
npm install
npm run dev
```

Open the printed `localhost` URL, then:

1. Load a CEM model file (e.g. `examples/cantilever_3d.cem.json` or
   `examples/l_frame_3d.cem.json` from the repo root).
2. Optionally load the matching `structnode analyze` results JSON
   (`out/.../results_<case>.json`) to overlay the deformed shape
   (dashed grey = undeformed, solid red = deformed) with an adjustable
   displacement scale.

Drag to orbit, scroll to zoom (standard Three.js `OrbitControls`).

## Develop

```bash
npm run lint   # oxlint
npm run build  # tsc -b && vite build
npm run test   # vitest run
```

`src/cem/geometry.ts` holds the pure coordinate/displacement math
(unit-tested in `geometry.test.ts`); `src/components/SceneViewer.tsx`
is the only file that touches Three.js, kept as a thin imperative
rendering layer over that math rather than its own framework
(deliberately not `@react-three/fiber`, to keep the dependency surface
small for a "minimal" viewer).
