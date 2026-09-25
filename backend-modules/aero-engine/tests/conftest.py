from aero_engine.aircraft.models import (
    AircraftConfig, Surface, VerticalTail, VTail, Fuselage, MassProperties,
)
from aero_engine.wing_planform import calculate_surface_planform


def make_fuselage(**overrides) -> Fuselage:
    defaults = dict(length=8.0, max_width=1.2, max_height=1.4, nose_length=1.5, tail_length=2.0)
    defaults.update(overrides)
    return Fuselage(**defaults)


def make_mass(**overrides) -> MassProperties:
    defaults = dict(mass_kg=1000.0, cg_x_position=2.56, cruise_speed_ms=60.0)
    defaults.update(overrides)
    return MassProperties(**defaults)


def make_conventional_config(wing_overrides=None, **mass_overrides) -> AircraftConfig:
    """
    Cessna-172-like proportions: wing AR ~6.9, tail volume coefficient
    ~0.14, giving a static margin in the 5-15% MAC range at the default
    CG (see docs/superpowers/specs/2026-09-25-aircraft-designer-design.md
    Task 9 derivation).
    """
    wing_kwargs = dict(span=11.0, root_chord=1.6, tip_chord=1.6, sweep_deg=0.0,
                        dihedral_deg=5.0, x_position=2.0)
    if wing_overrides:
        wing_kwargs.update(wing_overrides)
    return AircraftConfig(
        configuration_type="conventional",
        wing=Surface(**wing_kwargs),
        horizontal_tail=Surface(span=3.4, root_chord=0.9, tip_chord=0.6,
                                 sweep_deg=5.0, x_position=6.5, z_position=0.9),
        vertical_tail=VerticalTail(height=1.5, root_chord=1.0, tip_chord=0.5,
                                    sweep_deg=15.0, x_position=6.8, z_position=0.3),
        fuselage=make_fuselage(),
        mass=make_mass(**mass_overrides),
    )


def make_flying_wing_config(**mass_overrides) -> AircraftConfig:
    """
    cg_x_position defaults to the wing's own aerodynamic center (quarter
    of its swept MAC, measured from the MAC leading edge -- see
    stability._surface_ac_x), so that a flying wing -- whose neutral
    point equals the wing AC, having no tail -- sits at ~0 static margin
    by default. This wing is swept 25 deg, so its MAC leading edge is
    offset well aft of the root leading edge; a naive x_position + 0.25 *
    root-chord estimate (ignoring that sweep offset) would be wrong here.
    """
    wing_span, wing_root_chord, wing_tip_chord, wing_sweep_deg = 11.0, 1.6, 1.6, 25.0
    wing_x_position = 2.0
    wing_planform = calculate_surface_planform(wing_span, wing_root_chord, wing_tip_chord, wing_sweep_deg)
    wing_ac_x = wing_x_position + wing_planform["x_mac_le"] + 0.25 * wing_planform["mac"]

    defaults = dict(cg_x_position=wing_ac_x)
    defaults.update(mass_overrides)
    return AircraftConfig(
        configuration_type="flying_wing",
        wing=Surface(span=wing_span, root_chord=wing_root_chord, tip_chord=wing_tip_chord,
                     sweep_deg=wing_sweep_deg, dihedral_deg=3.0, x_position=wing_x_position),
        fuselage=make_fuselage(),
        mass=make_mass(**defaults),
    )


def make_canard_config(**mass_overrides) -> AircraftConfig:
    defaults = dict(cg_x_position=4.5)
    defaults.update(mass_overrides)
    return AircraftConfig(
        configuration_type="canard",
        wing=Surface(span=8.0, root_chord=1.2, tip_chord=1.2, sweep_deg=0.0, x_position=4.0),
        canard=Surface(span=2.0, root_chord=0.6, tip_chord=0.4, sweep_deg=0.0, x_position=0.3),
        vertical_tail=VerticalTail(height=1.0, root_chord=0.7, tip_chord=0.4,
                                    sweep_deg=10.0, x_position=6.5),
        fuselage=make_fuselage(length=7.0, max_width=1.0, max_height=1.2, nose_length=1.0, tail_length=1.5),
        mass=make_mass(**defaults),
    )


def make_v_tail_config(**mass_overrides) -> AircraftConfig:
    return AircraftConfig(
        configuration_type="v_tail",
        wing=Surface(span=11.0, root_chord=1.6, tip_chord=1.6, sweep_deg=0.0,
                     dihedral_deg=5.0, x_position=2.0),
        v_tail=VTail(span=2.5, root_chord=0.9, tip_chord=0.5, dihedral_v_deg=40.0,
                     sweep_deg=10.0, x_position=6.7),
        fuselage=make_fuselage(),
        mass=make_mass(**mass_overrides),
    )
