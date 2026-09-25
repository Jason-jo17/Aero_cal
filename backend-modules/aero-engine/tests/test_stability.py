import math
import pytest
from aero_engine.aircraft.stability import estimate_cl_alpha_3d, project_v_tail_equivalent_areas


def test_estimate_cl_alpha_3d_matches_helmbold_equation():
    # Pure Helmbold's equation (eta=1, no sweep, incompressible):
    # CL_alpha = 2*pi*AR / (2 + sqrt(4 + AR^2))
    result = estimate_cl_alpha_3d(aspect_ratio=8.0, sweep_half_chord_deg=0.0, eta=1.0)
    assert result == pytest.approx(4.906, abs=1e-3)


def test_estimate_cl_alpha_3d_rejects_non_positive_aspect_ratio():
    with pytest.raises(ValueError):
        estimate_cl_alpha_3d(aspect_ratio=0)


def test_project_v_tail_equivalent_areas_pure_vertical_at_90_degrees():
    s_h_eff, s_v_eff = project_v_tail_equivalent_areas(total_area=2.0, dihedral_v_deg=90.0)
    assert s_h_eff == pytest.approx(0.0, abs=1e-9)
    assert s_v_eff == pytest.approx(2.0, abs=1e-9)


def test_project_v_tail_equivalent_areas_pure_horizontal_at_0_degrees():
    s_h_eff, s_v_eff = project_v_tail_equivalent_areas(total_area=2.0, dihedral_v_deg=0.0)
    assert s_h_eff == pytest.approx(2.0, abs=1e-9)
    assert s_v_eff == pytest.approx(0.0, abs=1e-9)


def test_project_v_tail_equivalent_areas_at_45_degrees_splits_evenly():
    s_h_eff, s_v_eff = project_v_tail_equivalent_areas(total_area=2.0, dihedral_v_deg=45.0)
    assert s_h_eff == pytest.approx(1.0, abs=1e-6)
    assert s_v_eff == pytest.approx(1.0, abs=1e-6)
