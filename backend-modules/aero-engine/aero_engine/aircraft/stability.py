import math


def estimate_cl_alpha_3d(
    aspect_ratio: float,
    sweep_half_chord_deg: float = 0.0,
    eta: float = 0.95,
    mach: float = 0.0,
) -> float:
    """
    3D lift-curve slope (per radian), from thin-airfoil theory (2*pi per
    radian, camber-independent) corrected to finite span and sweep via
    Helmbold's equation with the standard DATCOM sweep/compressibility
    extension. Incompressible (mach=0) by default.
    """
    if aspect_ratio <= 0:
        raise ValueError("aspect_ratio must be positive")

    beta = math.sqrt(max(1e-6, 1 - mach ** 2))
    tan_sweep = math.tan(math.radians(sweep_half_chord_deg))

    denominator_term = 4 + (aspect_ratio ** 2 * beta ** 2 / eta ** 2) * (1 + (tan_sweep ** 2) / (beta ** 2))
    if denominator_term < 0:
        # Degenerate input - fall back to the simpler low-AR-safe form.
        return 2 * math.pi * aspect_ratio / (aspect_ratio + 2)

    denominator = 2 + math.sqrt(denominator_term)
    return (2 * math.pi * aspect_ratio) / denominator


def _le_sweep_to_half_chord_sweep(sweep_le_deg: float, aspect_ratio: float, taper_ratio: float) -> float:
    """
    Convert leading-edge sweep to half-chord sweep using the standard
    sweep-at-any-chord-fraction relation (Raymer / DATCOM):

        tan(Lambda_half_chord) = tan(Lambda_LE) - (2/AR) * (1 - taper) / (1 + taper)

    This is needed because `Surface.sweep_deg` (and `VerticalTail`/`VTail`
    `sweep_deg`) are stored as LEADING-EDGE sweep -- matching what
    `geometry.generate_surface_geometry` actually computes for the tip LE
    x-offset -- but the Helmbold/DATCOM lift-slope formula used by
    `estimate_cl_alpha_3d` wants HALF-CHORD sweep. For an untapered
    (taper_ratio=1) surface the two are identical since (1-taper)=0.
    """
    tan_le = math.tan(math.radians(sweep_le_deg))
    tan_half_chord = tan_le - (2.0 / aspect_ratio) * (1 - taper_ratio) / (1 + taper_ratio)
    return math.degrees(math.atan(tan_half_chord))


def project_v_tail_equivalent_areas(total_area: float, dihedral_v_deg: float) -> tuple[float, float]:
    """
    Standard V-tail equivalent-area decomposition (Raymer, Aircraft
    Design: A Conceptual Approach, Ch. 6.7): projects the V-tail's total
    planform area onto an equivalent horizontal-tail area and an
    equivalent vertical-tail area, based on the dihedral angle of each
    panel measured from horizontal.
    """
    dihedral_rad = math.radians(dihedral_v_deg)
    s_h_eff = total_area * (math.cos(dihedral_rad) ** 2)
    s_v_eff = total_area * (math.sin(dihedral_rad) ** 2)
    return s_h_eff, s_v_eff


from .models import AircraftConfig


def _surface_ac_x(x_position: float, planform: dict) -> float:
    """Aerodynamic center x-location: the quarter-chord of the surface's MAC."""
    return x_position + planform["x_mac_le"] + 0.25 * planform["mac"]


def calculate_longitudinal_stability(config: AircraftConfig, geometry: dict) -> dict:
    """
    Static longitudinal stability: neutral point, static margin, Cm_alpha.
    Uses the general two-lifting-surface neutral-point equation (Roskam
    Part VI / Raymer Ch. 16), which handles a canard as the same formula
    with a negative (forward) moment arm.
    """
    wing = config.wing
    wing_planform = geometry["wing"]["planform"]
    S_wing = wing_planform["area"]
    AR_wing = wing_planform["aspect_ratio"]
    MAC_wing = wing_planform["mac"]
    wing_ac_x = _surface_ac_x(wing.x_position, wing_planform)

    wing_sweep_half_chord = _le_sweep_to_half_chord_sweep(wing.sweep_deg, AR_wing, wing_planform["taper_ratio"])
    CL_alpha_wing = estimate_cl_alpha_3d(AR_wing, wing_sweep_half_chord)
    h_ac_wing = 0.25
    h_cg = (config.mass.cg_x_position - (wing.x_position + wing_planform["x_mac_le"])) / MAC_wing

    if config.configuration_type == "flying_wing":
        h_n = h_ac_wing
        tail_volume_coefficient = None
    else:
        if config.configuration_type == "v_tail":
            vt = config.v_tail
            v_planform = geometry["v_tail"]["planform"]
            S_other, _ = project_v_tail_equivalent_areas(v_planform["area"], vt.dihedral_v_deg)
            other_ac_x = _surface_ac_x(vt.x_position, v_planform)
            AR_other = v_planform["aspect_ratio"]
            sweep_other = vt.sweep_deg
            taper_other = v_planform["taper_ratio"]
        else:
            if config.configuration_type in ("conventional", "t_tail"):
                other, other_geom = config.horizontal_tail, geometry["horizontal_tail"]
            elif config.configuration_type == "canard":
                other, other_geom = config.canard, geometry["canard"]
            else:
                raise ValueError(f"Unhandled configuration_type: {config.configuration_type}")
            other_planform = other_geom["planform"]
            S_other = other_planform["area"]
            other_ac_x = _surface_ac_x(other.x_position, other_planform)
            AR_other = other_planform["aspect_ratio"]
            sweep_other = other.sweep_deg
            taper_other = other_planform["taper_ratio"]

        sweep_other_half_chord = _le_sweep_to_half_chord_sweep(sweep_other, AR_other, taper_other)
        CL_alpha_other = estimate_cl_alpha_3d(AR_other, sweep_other_half_chord)
        l = other_ac_x - wing_ac_x
        deps_dalpha = 2 * CL_alpha_wing / (math.pi * AR_wing)
        tail_volume_coefficient = (S_other * l) / (S_wing * MAC_wing)

        h_n = h_ac_wing + (CL_alpha_other / CL_alpha_wing) * (S_other / S_wing) * (l / MAC_wing) * (1 - deps_dalpha)

    static_margin = h_n - h_cg

    if static_margin < 0:
        classification = "unstable"
    elif static_margin < 0.05:
        classification = "marginal"
    elif static_margin <= 0.20:
        classification = "stable"
    else:
        classification = "stable_sluggish"

    return {
        "neutral_point_mac": h_n,
        "cg_mac": h_cg,
        "static_margin_percent": static_margin * 100,
        "static_margin_classification": classification,
        "cm_alpha": -CL_alpha_wing * static_margin,
        "tail_volume_coefficient": tail_volume_coefficient,
    }


def calculate_lateral_stability(config: AircraftConfig, geometry: dict) -> dict:
    """
    Static lateral stability: dihedral effect (Cl_beta), combining the
    direct-dihedral contribution and the wing-sweep contribution (both
    small-angle rule-of-thumb estimates).
    """
    wing = config.wing
    wing_planform = geometry["wing"]["planform"]
    S_wing = wing_planform["area"]
    AR_wing = wing_planform["aspect_ratio"]
    wing_sweep_half_chord = _le_sweep_to_half_chord_sweep(wing.sweep_deg, AR_wing, wing_planform["taper_ratio"])
    CL_alpha_wing = estimate_cl_alpha_3d(AR_wing, wing_sweep_half_chord)

    dihedral_rad = math.radians(wing.dihedral_deg)
    cl_beta_dihedral = -(CL_alpha_wing / 4) * dihedral_rad

    rho = 1.225
    v = config.mass.cruise_speed_ms
    weight_n = config.mass.mass_kg * 9.81
    cl_trim = weight_n / (0.5 * rho * v ** 2 * S_wing)
    sweep_rad = math.radians(wing.sweep_deg)
    cl_beta_sweep = -cl_trim * math.tan(sweep_rad) / (math.pi * AR_wing)

    cl_beta_total = cl_beta_dihedral + cl_beta_sweep

    if cl_beta_total < -0.02:
        classification = "stable"
    elif cl_beta_total <= 0:
        classification = "marginal"
    else:
        classification = "unstable"

    return {
        "cl_beta": cl_beta_total,
        "cl_beta_classification": classification,
    }


def calculate_directional_stability(config: AircraftConfig, geometry: dict) -> dict:
    """
    Static directional (weathercock) stability: Cn_beta from the vertical
    tail volume coefficient. Fuselage side-area destabilizing contribution
    and sidewash are not modeled (see design spec's Known Limitations).
    """
    wing_planform = geometry["wing"]["planform"]
    S_wing = wing_planform["area"]
    span_wing = config.wing.span
    wing_ac_x = _surface_ac_x(config.wing.x_position, wing_planform)

    if config.configuration_type in ("conventional", "t_tail", "canard"):
        vt = config.vertical_tail
        v_planform = geometry["vertical_tail"]["planform"]
        S_v = v_planform["area"]
        v_ac_x = _surface_ac_x(vt.x_position, v_planform)
        AR_v = v_planform["aspect_ratio"]
        sweep_v = vt.sweep_deg
    elif config.configuration_type == "v_tail":
        vtail = config.v_tail
        v_planform = geometry["v_tail"]["planform"]
        _, S_v = project_v_tail_equivalent_areas(v_planform["area"], vtail.dihedral_v_deg)
        v_ac_x = _surface_ac_x(vtail.x_position, v_planform)
        AR_v = v_planform["aspect_ratio"]
        sweep_v = vtail.sweep_deg
    else:  # flying_wing: no vertical surface, no weathercock stability
        return {
            "cn_beta": 0.0,
            "cn_beta_classification": "unstable",
            "vertical_tail_volume_coefficient": None,
        }

    l_v = v_ac_x - wing_ac_x
    V_V = (S_v * l_v) / (S_wing * span_wing)
    sweep_v_half_chord = _le_sweep_to_half_chord_sweep(sweep_v, AR_v, v_planform["taper_ratio"])
    CL_alpha_v = estimate_cl_alpha_3d(AR_v, sweep_v_half_chord)
    cn_beta = CL_alpha_v * V_V

    if cn_beta > 0.05:
        classification = "stable"
    elif cn_beta >= 0:
        classification = "marginal"
    else:
        classification = "unstable"

    return {
        "cn_beta": cn_beta,
        "cn_beta_classification": classification,
        "vertical_tail_volume_coefficient": V_V,
    }


def analyze_stability(config: AircraftConfig, geometry: dict) -> dict:
    """
    Runs the full static stability analysis (longitudinal, lateral,
    directional) and assembles warnings for cases the underlying formulas
    don't fully capture, or physically odd inputs that still compute a
    number.
    """
    longitudinal = calculate_longitudinal_stability(config, geometry)
    lateral = calculate_lateral_stability(config, geometry)
    directional = calculate_directional_stability(config, geometry)

    warnings: list[str] = []

    if config.configuration_type == "flying_wing":
        warnings.append(
            "Flying wing: pitch trim requires a reflexed airfoil or washout, "
            "which this tool does not model. Neutral point is based on the "
            "wing's aerodynamic center only."
        )

    if config.configuration_type == "canard":
        warnings.append(
            "Canard: the neutral-point calculation reuses the same downwash "
            "correction term used for an aft tail, which is physically "
            "backward for a forward canard surface. Treat this result as a "
            "rougher approximation than for conventional/T-tail configs."
        )

    if longitudinal["static_margin_percent"] < 0:
        warnings.append(
            "CG is aft of the neutral point: the aircraft is longitudinally "
            "unstable as configured."
        )

    if directional["cn_beta_classification"] == "unstable" and config.configuration_type != "flying_wing":
        warnings.append(
            "No positive weathercock stability: check vertical tail sizing/position."
        )

    if not (0.0 <= config.mass.cg_x_position <= config.fuselage.length):
        warnings.append(
            "CG position is outside the physical fuselage length - check "
            "cg_x_position against fuselage.length."
        )

    return {
        **longitudinal,
        **lateral,
        **directional,
        "warnings": warnings,
    }
