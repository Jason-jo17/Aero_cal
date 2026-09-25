import math

def calculate_propulsion(motor_kv: float, voltage: float, prop_diameter_in: float, prop_pitch_in: float):
    """
    Motor-Propeller matcher to estimate RPM, Thrust, and Power.
    Simplified empirical model for brushless motors and hobbyist propellers.
    """
    # Unloaded RPM
    rpm_no_load = motor_kv * voltage
    
    # Loaded RPM (assume 75% efficiency for a matched prop, could vary based on prop size vs motor size)
    rpm_loaded = rpm_no_load * 0.75
    
    # Thrust calculation
    # Using classical empirical formula for static thrust of RC props
    # Thrust (kg) = (Diameter / 10)^3 * (Pitch / 10) * (RPM / 1000)^2 * 0.0283
    # Wait, a more standard empirical equation (e.g. Abbot's equation or similar):
    # Thrust (g) = (RPM/1000)^2 * Diameter^4 * Pitch * 2.83 * 10^-5
    # Let's use a standard approximation for static thrust (in grams)
    # T = 1.225 * pi * (D*0.0254)^2 / 4 * (RPM * Pitch * 0.0254 / 60)^2
    
    # Convert dimensions to SI units
    d_m = prop_diameter_in * 0.0254
    p_m = prop_pitch_in * 0.0254
    n_rps = rpm_loaded / 60.0
    air_density = 1.225  # kg/m^3 (standard sea-level air)
    gravity = 9.80665

    # Propeller aerodynamic coefficients (CT, CP based on pitch-to-diameter ratio)
    pitch_ratio = (prop_pitch_in / prop_diameter_in) if prop_diameter_in > 0 else 0.0
    ct = 0.10 * (1.0 + 0.20 * pitch_ratio)
    cp = 0.05 * (1.0 + 0.30 * pitch_ratio)

    # Static thrust (Newtons and grams)
    # T = CT * rho * n^2 * D^4
    thrust_newtons = ct * air_density * (n_rps ** 2) * (d_m ** 4)
    thrust_grams = (thrust_newtons * 1000.0) / gravity

    # Mechanical and electrical power
    # P_mech = CP * rho * n^3 * D^5
    power_mechanical_w = cp * air_density * (n_rps ** 3) * (d_m ** 5)
    motor_eff = 0.82
    power_watts = power_mechanical_w / motor_eff
    current_amps = (power_watts / voltage) if voltage > 0 else 0.0

    # Pitch speed (theoretical exit velocity in m/s)
    pitch_speed_ms = (rpm_loaded * p_m) / 60.0

    return {
        "motor_kv": motor_kv,
        "voltage": voltage,
        "prop_diameter_in": prop_diameter_in,
        "prop_pitch_in": prop_pitch_in,
        "rpm_no_load": round(rpm_no_load, 1),
        "rpm_loaded": round(rpm_loaded, 1),
        "thrust_grams": round(thrust_grams, 1),
        "thrust_newtons": round(thrust_newtons, 2),
        "power_watts": round(power_watts, 1),
        "current_amps": round(current_amps, 2),
        "pitch_speed_ms": round(pitch_speed_ms, 2)
    }
