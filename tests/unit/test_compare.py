from __future__ import annotations

from structnode.reporting import compare_results


def _results(uy: float, fy: float) -> dict:
    return {
        "displacements": {"N2": {"Uy": uy}},
        "reactions": {"N1": {"Fy": fy}},
        "element_forces": {},
    }


def test_identical_results_compare_ok() -> None:
    result = compare_results(_results(-0.0002, 1000.0), _results(-0.0002, 1000.0))
    assert result.ok
    assert result.max_relative_diff == 0.0
    assert result.diffs


def test_small_difference_within_tolerance_is_ok() -> None:
    result = compare_results(
        _results(-0.0002, 1000.0), _results(-0.00020001, 1000.0), tolerance=1e-3
    )
    assert result.ok


def test_large_difference_exceeds_tolerance() -> None:
    result = compare_results(_results(-0.0002, 1000.0), _results(-0.0003, 1000.0), tolerance=1e-6)
    assert not result.ok
    uy_diff = next(d for d in result.diffs if d.component == "Uy")
    assert uy_diff.rel_diff is not None
    assert uy_diff.rel_diff > 1e-6


def test_missing_node_is_reported_not_silently_skipped() -> None:
    a = _results(-0.0002, 1000.0)
    b = _results(-0.0002, 1000.0)
    del b["displacements"]["N2"]
    result = compare_results(a, b)
    assert not result.ok
    assert "displacements.N2" in result.missing_in_b


def test_near_zero_values_have_no_relative_diff() -> None:
    result = compare_results(_results(1e-15, 1000.0), _results(-1e-15, 1000.0))
    uy_diff = next(d for d in result.diffs if d.component == "Uy")
    assert uy_diff.rel_diff is None
    assert result.ok
