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

    CL_alpha_wing = estimate_cl_alpha_3d(AR_wing, wing.sweep_deg)
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

        CL_alpha_other = estimate_cl_alpha_3d(AR_other, sweep_other)
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
    CL_alpha_wing = estimate_cl_alpha_3d(AR_wing, wing.sweep_deg)

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
