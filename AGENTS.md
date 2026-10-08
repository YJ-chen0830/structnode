# Agent operating boundary

Read this and `docs/MASTER_PLAN.md` before touching code.

## What CEM is

The Canonical Engineering Model (`structnode.core.model.CEM`) is the
engineering source of truth. Any solver deck, CAD drawing, BIM element,
or report is a *derived* representation. Never let a derived
representation silently become authoritative.

## What an agent may do

- Propose typed commands against the CEM service layer (`model.*`,
  `analysis.*`) — never hand-craft raw numerical results or bypass
  schema/topology validation.
- Implement or extend solver kernels, adapters, and tests, but must not
  claim convergence, stability, or safety that the deterministic checks
  in `core/validation` did not actually verify.
- Run `scripts/preflight.sh` before considering any change complete.

## What an agent must not do

- Must not push to `main`/`master` directly. Feature branches only
  (`feat/<slug>`), PR + CI required.
- Must not silently approximate an unsupported CEM feature (see
  `docs/MASTER_PLAN.md` §3 "CEM v0.1 exclusions"). Reject or ask.
- Must not fabricate engineering approval language. Alpha-stage output
  carries `EXPERIMENTAL — NOT FOR ENGINEERING DESIGN WITHOUT INDEPENDENT
  REVIEW`.
- Must not commit secrets, licensed MIDAS files, or client drawings.
- Must not run `git add -A` → commit → push unattended until the
  staged-file review / secret-scan safeguard called out in
  `docs/MASTER_PLAN.md` §9.3 is actually implemented, not just
  commented as a TODO.

## Current scope (S0)

Schema (`core/model`) + topology validation (`core/validation`) + CLI
(`structnode model validate`) only. No FEM solver, no MCP/REST, no GUI
yet — do not implement ahead of the roadmap in
`docs/MASTER_PLAN.md` §8 without discussing scope first.
