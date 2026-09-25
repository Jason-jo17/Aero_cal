import pytest
from pydantic import ValidationError

from aero_engine.aircraft.models import (
    AircraftConfig, Surface, VerticalTail, VTail, Fuselage, MassProperties,
)


def _base_kwargs(**overrides):
    kwargs = dict(
        configuration_type="conventional",
        wing=Surface(span=11.0, root_chord=1.6, tip_chord=1.6, x_position=2.0),
        horizontal_tail=Surface(span=3.4, root_chord=0.9, tip_chord=0.6, x_position=6.5),
        vertical_tail=VerticalTail(height=1.5, root_chord=1.0, tip_chord=0.5, x_position=6.8),
        fuselage=Fuselage(length=8.0, max_width=1.2, max_height=1.4, nose_length=1.5, tail_length=2.0),
        mass=MassProperties(mass_kg=1000.0, cg_x_position=2.5, cruise_speed_ms=60.0),
    )
    kwargs.update(overrides)
    return kwargs


def test_valid_conventional_config_parses():
    config = AircraftConfig(**_base_kwargs())
    assert config.configuration_type == "conventional"
    assert config.horizontal_tail is not None
    assert config.canard is None


def test_v_tail_config_with_horizontal_tail_is_rejected():
    with pytest.raises(ValidationError):
        AircraftConfig(**_base_kwargs(
            configuration_type="v_tail",
            v_tail=VTail(span=2.5, root_chord=0.9, tip_chord=0.5, dihedral_v_deg=40.0, x_position=6.7),
        ))


def test_t_tail_config_missing_vertical_tail_is_rejected():
    kwargs = _base_kwargs(configuration_type="t_tail")
    kwargs["vertical_tail"] = None
    with pytest.raises(ValidationError):
        AircraftConfig(**kwargs)


def test_flying_wing_config_with_horizontal_tail_is_rejected():
    kwargs = _base_kwargs(configuration_type="flying_wing")
    with pytest.raises(ValidationError):
        AircraftConfig(**kwargs)


def test_canard_config_with_horizontal_tail_is_rejected():
    kwargs = _base_kwargs(
        configuration_type="canard",
        canard=Surface(span=2.0, root_chord=0.6, tip_chord=0.4, x_position=0.3),
    )
    with pytest.raises(ValidationError):
        AircraftConfig(**kwargs)


def test_zero_span_wing_is_rejected():
    with pytest.raises(ValidationError):
        Surface(span=0, root_chord=1.6, tip_chord=1.6, x_position=2.0)


def test_zero_cruise_speed_is_rejected():
    with pytest.raises(ValidationError):
        MassProperties(mass_kg=1000.0, cg_x_position=2.5, cruise_speed_ms=0)


def test_fuselage_taper_sections_longer_than_fuselage_is_rejected():
    with pytest.raises(ValidationError):
        Fuselage(length=3.0, max_width=1.0, max_height=1.0, nose_length=2.0, tail_length=2.0)


def test_surface_sweep_out_of_range_is_rejected():
    with pytest.raises(ValidationError):
        Surface(span=11.0, root_chord=1.6, tip_chord=1.6, x_position=2.0, sweep_deg=85.0)


def test_surface_dihedral_out_of_range_is_rejected():
    with pytest.raises(ValidationError):
        Surface(span=11.0, root_chord=1.6, tip_chord=1.6, x_position=2.0, dihedral_deg=-90.0)


def test_vertical_tail_sweep_out_of_range_is_rejected():
    with pytest.raises(ValidationError):
        VerticalTail(height=1.5, root_chord=1.0, tip_chord=0.5, x_position=6.8, sweep_deg=81.0)


def test_surface_sweep_and_dihedral_within_range_are_accepted():
    surface = Surface(span=11.0, root_chord=1.6, tip_chord=1.6, x_position=2.0,
                       sweep_deg=80.0, dihedral_deg=-80.0)
    assert surface.sweep_deg == 80.0
    assert surface.dihedral_deg == -80.0
