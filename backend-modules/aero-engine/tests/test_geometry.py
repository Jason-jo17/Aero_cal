import math
import pytest
from aero_engine.aircraft.geometry import generate_surface_geometry, generate_vertical_surface_geometry, generate_fuselage_geometry


def test_generate_surface_geometry_symmetry_sweep_dihedral():
    geom = generate_surface_geometry(
        span=10.0, root_chord=2.0, tip_chord=1.0,
        sweep_deg=30.0, dihedral_deg=10.0,
        x_position=5.0, z_position=0.5,
    )

    # vertices order: [root_le, tip_le_pos, tip_te_pos, root_te, tip_le_neg, tip_te_neg]
    root_le, tip_le_pos, tip_te_pos, root_te, tip_le_neg, tip_te_neg = geom["vertices"]

    assert root_le == pytest.approx([5.0, 0.0, 0.5])
    assert root_te == pytest.approx([7.0, 0.0, 0.5])
    # tip x offset = half_span * tan(sweep); tip z offset = half_span * tan(dihedral)
    assert tip_le_pos == pytest.approx([7.8868, 5.0, 1.3816], abs=1e-3)
    assert tip_te_pos == pytest.approx([8.8868, 5.0, 1.3816], abs=1e-3)

    # Mirror symmetry: the negative-y tip matches the positive-y tip in x
    # and z, with only y negated.
    assert tip_le_neg[0] == pytest.approx(tip_le_pos[0])
    assert tip_le_neg[2] == pytest.approx(tip_le_pos[2])
    assert tip_le_neg[1] == pytest.approx(-tip_le_pos[1])

    assert len(geom["vertices"]) == 6
    assert len(geom["edges"]) == 7
    assert geom["top_view"][0] == pytest.approx([5.0, 0.0])


def test_generate_surface_geometry_no_sweep_no_dihedral_is_flat_rectangle():
    geom = generate_surface_geometry(
        span=4.0, root_chord=1.0, tip_chord=1.0,
        sweep_deg=0.0, dihedral_deg=0.0,
        x_position=0.0, z_position=0.0,
    )
    for v in geom["vertices"]:
        assert v[2] == pytest.approx(0.0)  # no dihedral -> flat in z
    xs = [v[0] for v in geom["vertices"]]
    assert min(xs) == pytest.approx(0.0)
    assert max(xs) == pytest.approx(1.0)  # no sweep -> tip LE stays above root LE


def test_generate_vertical_surface_geometry_single_unmirrored_fin():
    geom = generate_vertical_surface_geometry(
        height=1.5, root_chord=1.0, tip_chord=0.5, sweep_deg=15.0,
        x_position=6.8, z_position=0.3,
    )
    root_le, tip_le, tip_te, root_te = geom["vertices"]

    assert root_le == pytest.approx([6.8, 0.0, 0.3])
    assert root_te == pytest.approx([7.8, 0.0, 0.3])

    expected_tip_le_x = 6.8 + 1.5 * math.tan(math.radians(15.0))
    assert tip_le == pytest.approx([expected_tip_le_x, 0.0, 1.8], abs=1e-6)

    assert len(geom["vertices"]) == 4
    assert len(geom["edges"]) == 4
    assert all(v[1] == 0.0 for v in geom["vertices"])  # unmirrored: y stays 0


def test_generate_fuselage_geometry_outline():
    geom = generate_fuselage_geometry(
        length=8.0, max_width=1.2, max_height=1.4, nose_length=1.5, tail_length=2.0,
    )
    assert geom["side_view"][1] == pytest.approx([1.5, 0.7])
    assert geom["top_view"][1] == pytest.approx([1.5, 0.6])
    assert geom["vertices"][0] == pytest.approx([0.0, 0.0, 0.0])   # nose tip
    assert geom["vertices"][-1] == pytest.approx([8.0, 0.0, 0.0])  # tail tip
    assert len(geom["front_view"]) == 17  # 16-segment cross-section ellipse + closing point


from aero_engine.aircraft.geometry import generate_aircraft_geometry
from tests.conftest import (
    make_conventional_config, make_flying_wing_config, make_canard_config, make_v_tail_config,
)


def test_generate_aircraft_geometry_conventional_has_wing_tails_no_canard():
    geometry = generate_aircraft_geometry(make_conventional_config())
    assert geometry["wing"] is not None
    assert geometry["wing"]["planform"]["area"] > 0
    assert geometry["horizontal_tail"] is not None
    assert geometry["vertical_tail"] is not None
    assert geometry["canard"] is None
    assert geometry["v_tail"] is None
    assert geometry["fuselage"] is not None
    assert geometry["fuselage"]["planform"] is None


def test_generate_aircraft_geometry_flying_wing_has_only_wing():
    geometry = generate_aircraft_geometry(make_flying_wing_config())
    assert geometry["wing"] is not None
    assert geometry["horizontal_tail"] is None
    assert geometry["vertical_tail"] is None
    assert geometry["canard"] is None
    assert geometry["v_tail"] is None


def test_generate_aircraft_geometry_canard_has_canard_not_horizontal_tail():
    geometry = generate_aircraft_geometry(make_canard_config())
    assert geometry["canard"] is not None
    assert geometry["horizontal_tail"] is None
    assert geometry["vertical_tail"] is not None


def test_generate_aircraft_geometry_v_tail_has_v_tail_not_separate_tails():
    geometry = generate_aircraft_geometry(make_v_tail_config())
    assert geometry["v_tail"] is not None
    assert geometry["horizontal_tail"] is None
    assert geometry["vertical_tail"] is None
