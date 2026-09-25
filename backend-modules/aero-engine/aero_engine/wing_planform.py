import math


def calculate_surface_planform(span: float, root_chord: float, tip_chord: float, sweep_angle_deg: float) -> dict:
    """
    Calculate essential planform parameters (area, aspect ratio, taper
    ratio, MAC) for a single lifting surface. Shared by the wing-planform
    calculator and the aircraft designer's tail/canard/V-tail surfaces.
    """
    sweep_rad = math.radians(sweep_angle_deg)

    taper_ratio = tip_chord / root_chord if root_chord > 0 else 0

    area = (root_chord + tip_chord) / 2 * span

    aspect_ratio = (span ** 2) / area if area > 0 else 0

    if root_chord > 0:
        mac = (2 / 3) * root_chord * ((1 + taper_ratio + taper_ratio ** 2) / (1 + taper_ratio))
    else:
        mac = 0

    y_mac = (span / 6) * ((1 + 2 * taper_ratio) / (1 + taper_ratio))
    x_mac_le = y_mac * math.tan(sweep_rad)

    return {
        "span": span,
        "root_chord": root_chord,
        "tip_chord": tip_chord,
        "sweep_angle_deg": sweep_angle_deg,
        "taper_ratio": taper_ratio,
        "area": area,
        "aspect_ratio": aspect_ratio,
        "mac": mac,
        "y_mac": y_mac,
        "x_mac_le": x_mac_le,
    }


def calculate_wing_planform(span: float, root_chord: float, tip_chord: float, sweep_angle_deg: float):
    """
    Calculate essential wing planform parameters. Thin wrapper around
    calculate_surface_planform() kept for backward compatibility with the
    existing /aero/wing-planform endpoint.
    """
    return calculate_surface_planform(span, root_chord, tip_chord, sweep_angle_deg)
