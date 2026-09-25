import pytest
from aero_engine.aircraft.geometry import generate_surface_geometry


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
