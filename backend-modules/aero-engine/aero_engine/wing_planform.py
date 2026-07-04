import math

def calculate_wing_planform(span: float, root_chord: float, tip_chord: float, sweep_angle_deg: float):
    """
    Calculate essential wing planform parameters.
    """
    # Convert sweep to radians
    sweep_rad = math.radians(sweep_angle_deg)
    
    # Taper ratio (lambda)
    taper_ratio = tip_chord / root_chord if root_chord > 0 else 0
    
    # Wing Area (S) - Trapezoidal rule
    area = (root_chord + tip_chord) / 2 * span
    
    # Aspect Ratio (AR)
    aspect_ratio = (span ** 2) / area if area > 0 else 0
    
    # Mean Aerodynamic Chord (MAC)
    if root_chord > 0:
        mac = (2/3) * root_chord * ((1 + taper_ratio + taper_ratio**2) / (1 + taper_ratio))
    else:
        mac = 0
        
    # Y-position of MAC
    y_mac = (span / 6) * ((1 + 2 * taper_ratio) / (1 + taper_ratio))
    
    # X-position of MAC leading edge relative to root leading edge
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
        "x_mac_le": x_mac_le
    }
