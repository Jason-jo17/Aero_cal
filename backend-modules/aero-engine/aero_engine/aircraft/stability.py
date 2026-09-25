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
