import math
import pytest
from aero_engine.aircraft.stability import (
    estimate_cl_alpha_3d, project_v_tail_equivalent_areas, _le_sweep_to_half_chord_sweep,
)
from aero_engine.aircraft.geometry import generate_aircraft_geometry
from aero_engine.aircraft.stability import calculate_longitudinal_stability
from tests.conftest import (
    make_conventional_config, make_flying_wing_config, make_canard_config, make_v_tail_config,
)
from aero_engine.aircraft.models import Surface, Fuselage, MassProperties, AircraftConfig
from aero_engine.aircraft.stability import calculate_lateral_stability


def test_estimate_cl_alpha_3d_matches_helmbold_equation():
    # Pure Helmbold's equation (eta=1, no sweep, incompressible):
    # CL_alpha = 2*pi*AR / (2 + sqrt(4 + AR^2))
    result = estimate_cl_alpha_3d(aspect_ratio=8.0, sweep_half_chord_deg=0.0, eta=1.0)
    assert result == pytest.approx(4.906, abs=1e-3)


def test_estimate_cl_alpha_3d_rejects_non_positive_aspect_ratio():
    with pytest.raises(ValueError):
        estimate_cl_alpha_3d(aspect_ratio=0)


def test_le_sweep_to_half_chord_sweep_zero_for_untapered_unswept_wing():
    # taper_ratio=1 makes the (1-taper)/(1+taper) correction term vanish
    # regardless of AR, so LE sweep and half-chord sweep coincide.
    result = _le_sweep_to_half_chord_sweep(sweep_le_deg=0.0, aspect_ratio=6.0, taper_ratio=1.0)
    assert result == pytest.approx(0.0, abs=1e-9)


def test_le_sweep_to_half_chord_sweep_reduced_for_tapered_swept_wing():
    # LE sweep 20deg, AR=6, taper=0.5:
    # tan(20deg) = 0.3639702343
    # correction = (2/6) * (1-0.5)/(1+0.5) = 0.3333333 * 0.3333333 = 0.1111111
    # tan(half-chord sweep) = 0.3639702343 - 0.1111111 = 0.2528591
    # half-chord sweep = atan(0.2528591) in degrees ~= 14.19 deg
    result = _le_sweep_to_half_chord_sweep(sweep_le_deg=20.0, aspect_ratio=6.0, taper_ratio=0.5)
    assert result == pytest.approx(14.19, abs=0.05)
    assert result < 20.0


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


def test_conventional_static_margin_in_typical_range():
    config = make_conventional_config()  # default cg_x_position=2.56
    geometry = generate_aircraft_geometry(config)
    result = calculate_longitudinal_stability(config, geometry)
    assert 5.0 <= result["static_margin_percent"] <= 15.0
    assert result["static_margin_classification"] == "stable"
    assert result["cm_alpha"] < 0
    assert result["tail_volume_coefficient"] > 0


def test_cg_aft_of_neutral_point_is_unstable():
    config = make_conventional_config(cg_x_position=2.8)
    geometry = generate_aircraft_geometry(config)
    result = calculate_longitudinal_stability(config, geometry)
    assert result["static_margin_percent"] < 0
    assert result["static_margin_classification"] == "unstable"


def test_flying_wing_neutral_point_equals_wing_aerodynamic_center():
    config = make_flying_wing_config()  # cg_x_position defaults to the wing AC -> static margin ~0
    geometry = generate_aircraft_geometry(config)
    result = calculate_longitudinal_stability(config, geometry)
    assert result["neutral_point_mac"] == pytest.approx(0.25, abs=1e-6)
    assert result["tail_volume_coefficient"] is None
    assert result["static_margin_percent"] == pytest.approx(0.0, abs=1e-3)
    assert result["static_margin_classification"] == "marginal"


def test_canard_produces_finite_negative_moment_arm():
    config = make_canard_config()
    geometry = generate_aircraft_geometry(config)
    result = calculate_longitudinal_stability(config, geometry)
    assert result["tail_volume_coefficient"] < 0  # canard AC is forward of wing AC
    assert math.isfinite(result["neutral_point_mac"])
    assert math.isfinite(result["static_margin_percent"])


def test_v_tail_longitudinal_stability_is_finite_and_positive_volume_coefficient():
    # No dedicated V-tail longitudinal test existed before (deferred gap
    # from Task 8's review). The V-tail's projected horizontal-equivalent
    # area sits aft of the wing (like a conventional tail), so the moment
    # arm and tail volume coefficient should be positive here, unlike the
    # canard case above.
    config = make_v_tail_config()
    geometry = generate_aircraft_geometry(config)
    result = calculate_longitudinal_stability(config, geometry)
    assert math.isfinite(result["neutral_point_mac"])
    assert math.isfinite(result["static_margin_percent"])
    assert result["tail_volume_coefficient"] is not None
    assert math.isfinite(result["tail_volume_coefficient"])
    assert result["tail_volume_coefficient"] > 0


def test_dihedral_dominates_lateral_stability_when_unswept():
    config = make_conventional_config()  # wing sweep_deg=0.0, dihedral_deg=5.0
    geometry = generate_aircraft_geometry(config)
    result = calculate_lateral_stability(config, geometry)
    assert -0.12 <= result["cl_beta"] <= -0.08
    assert result["cl_beta_classification"] == "stable"


def test_sweep_only_contribution_is_small_and_stabilizing():
    config = make_conventional_config(wing_overrides={"sweep_deg": 20.0, "dihedral_deg": 0.0})
    geometry = generate_aircraft_geometry(config)
    result = calculate_lateral_stability(config, geometry)
    # Sweep alone is a much weaker contributor than 5deg of dihedral -
    # expect a small negative (marginal) value, not strongly stable.
    assert -0.02 < result["cl_beta"] < 0
    assert result["cl_beta_classification"] == "marginal"


from aero_engine.aircraft.stability import calculate_directional_stability


def test_conventional_vertical_tail_gives_stable_weathercock():
    config = make_conventional_config()
    geometry = generate_aircraft_geometry(config)
    result = calculate_directional_stability(config, geometry)
    assert 0.04 < result["cn_beta"] < 0.12
    assert result["cn_beta_classification"] == "stable"
    assert result["vertical_tail_volume_coefficient"] > 0


def test_flying_wing_has_no_directional_stability():
    config = make_flying_wing_config()
    geometry = generate_aircraft_geometry(config)
    result = calculate_directional_stability(config, geometry)
    assert result["cn_beta"] == 0.0
    assert result["cn_beta_classification"] == "unstable"
    assert result["vertical_tail_volume_coefficient"] is None


def test_v_tail_uses_projected_vertical_area():
    config = make_v_tail_config()
    geometry = generate_aircraft_geometry(config)
    result = calculate_directional_stability(config, geometry)
    assert result["cn_beta"] > 0
    assert result["vertical_tail_volume_coefficient"] is not None
    assert result["vertical_tail_volume_coefficient"] > 0


from aero_engine.aircraft.stability import analyze_stability


def test_analyze_stability_returns_full_expected_shape():
    config = make_conventional_config()
    geometry = generate_aircraft_geometry(config)
    result = analyze_stability(config, geometry)
    expected_keys = {
        "neutral_point_mac", "cg_mac", "static_margin_percent", "static_margin_classification",
        "cm_alpha", "tail_volume_coefficient", "cl_beta", "cl_beta_classification",
        "cn_beta", "cn_beta_classification", "vertical_tail_volume_coefficient", "warnings",
    }
    assert expected_keys.issubset(result.keys())
    assert isinstance(result["warnings"], list)


def test_analyze_stability_flying_wing_warns_about_trim():
    config = make_flying_wing_config()
    geometry = generate_aircraft_geometry(config)
    result = analyze_stability(config, geometry)
    assert any("reflex" in w.lower() or "washout" in w.lower() for w in result["warnings"])


def test_analyze_stability_canard_warns_about_downwash_assumption():
    config = make_canard_config()
    geometry = generate_aircraft_geometry(config)
    result = analyze_stability(config, geometry)
    assert any("downwash" in w.lower() or "canard" in w.lower() for w in result["warnings"])


def test_analyze_stability_warns_when_cg_aft_of_neutral_point():
    config = make_conventional_config(cg_x_position=2.8)
    geometry = generate_aircraft_geometry(config)
    result = analyze_stability(config, geometry)
    assert any("neutral point" in w.lower() or "unstable" in w.lower() for w in result["warnings"])


def test_analyze_stability_warns_when_cg_outside_fuselage_length():
    config = make_conventional_config(cg_x_position=20.0)  # fuselage.length is 8.0
    geometry = generate_aircraft_geometry(config)
    result = analyze_stability(config, geometry)
    assert any("fuselage" in w.lower() for w in result["warnings"])
