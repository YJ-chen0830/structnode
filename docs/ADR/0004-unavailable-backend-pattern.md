# ADR 0004: Unavailable optional backends report honestly; they never crash, silently no-op, or fake a result

**Status:** Accepted (S4)

## Context

`openseespy`, the package behind the OpenSees cross-check adapter, does
not import in this project's development environment — confirmed
failing with a Windows DLL load error on both the project's own Python
3.14 virtualenv and the system's separately-installed Python 3.11, a
known class of issue for `openseespy` on Windows (missing MSVC runtime
or a wheel/Python-ABI mismatch), not a defect in this repository's own
code. See `docs/ROADMAP.md`'s S4 entry for the installation attempts.

This means the OpenSees adapter was written and must be maintained
without ever having been run against a live OpenSeesPy process. That's
a real risk to flag, not hide, and it also set the pattern for how any
future optional backend (a license-gated commercial solver, a
platform-specific tool) should behave when it isn't usable in a given
environment.

## Decision

1. **Lazy import.** `adapters/opensees/adapter.py` imports
   `openseespy.opensees` only inside `_import_ops()`, called on first
   use and cached (`functools.lru_cache`). The rest of structnode has
   zero OpenSees dependency at import time.
2. **Honest capability reporting.** `is_available()` and
   `capabilities()` report `available: False` truthfully when the
   import fails — never `True` by assumption, never silently swallowed.
3. **Typed, specific failure.** Every public function raises
   `OpenSeesUnavailableError` (carrying the underlying import error)
   rather than letting an `ImportError` propagate raw or returning an
   empty/default result that could be mistaken for "ran and found
   nothing."
4. **Surfaced, not swallowed, at every layer.** CLI's
   `analyze --solver opensees`, the MCP `analysis_run` tool, and the
   REST `/analysis/run` endpoint all return a typed error
   (`CEM-SOLVER-OPENSEESUNAVAILABLEERROR`) through the same
   `service.py` path real results use — not a different code path, not
   an HTTP 500, not a hang.
5. **Tests assert the unavailable path, not just the happy path.**
   `tests/unit/test_opensees_adapter.py` exists specifically to pin
   down that this environment's "doesn't work" case behaves correctly
   — it is not a placeholder for "real" tests to replace later; it's
   testing the actual behavior real users on this platform will see.
6. **The cross-solver benchmark is `skip`ped with a visible reason, not
   silently excluded.** `tests/analytical/test_cross_solver_opensees.py`
   uses `pytest.mark.skipif(not is_available(), reason=...)`, so
   `pytest -rs` shows exactly why it didn't run. Nothing claims this
   benchmark passed when it has, in fact, never executed.

## Consequences

- Anyone running this project on a platform where `openseespy` does
  import gets the adapter and its benchmark working with no code
  changes — the lazy-import/capability pattern means "unavailable here"
  and "works there" are the same code path with a different outcome,
  not two different code paths.
- The OpenSees adapter's CEM-to-OpenSees translation (element
  definitions, `geomTransf` orientation, load application) is reviewed
  against the documented API but **unverified by execution**. Treat it
  as a draft that happens to type-check and import-guard correctly,
  not as validated numerics, until someone runs it for real (see ADR
  0003 for one specific known-risky area: local-axis orientation for
  `Iy != Iz` sections).
- This pattern (lazy import + honest capabilities + typed
  unavailable-error + tested unavailable-path + visibly-skipped
  dependent benchmarks) is the template for any future optional,
  environment-dependent backend — not something to re-derive each time.
