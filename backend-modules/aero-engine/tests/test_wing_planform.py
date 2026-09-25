import pytest
from aero_engine.wing_planform import calculate_wing_planform, calculate_surface_planform


def test_calculate_wing_planform_matches_known_values():
    # These are the exact values already exercised by the repo's root
    # test_api.py smoke test (span=10, root=2, tip=1, sweep=15deg).
    result = calculate_wing_planform(10.0, 2.0, 1.0, 15.0)
    assert result["area"] == pytest.approx(15.0)
    assert result["taper_ratio"] == pytest.approx(0.5)
    assert result["aspect_ratio"] == pytest.approx(6.6667, abs=1e-3)


def test_calculate_wing_planform_wraps_shared_helper():
    wing_result = calculate_wing_planform(8.0, 1.5, 0.9, 10.0)
    surface_result = calculate_surface_planform(8.0, 1.5, 0.9, 10.0)
    assert wing_result == surface_result
