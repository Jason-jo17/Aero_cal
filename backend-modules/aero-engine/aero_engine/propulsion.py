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
    
    # Convert inches to meters
    d_m = prop_diameter_in * 0.0254
    p_m = prop_pitch_in * 0.0254
    
    # Power absorbed by prop (Watts)
    # P = K_p * D^4 * P * RPM^3
    # Empirical K_p for standard APC style props is around 1.11 -> 1.3
    # Standard equation: P = prop_const * rpm^3 * diameter^4 * pitch / 10^17 (if inches)
    # Let's use simplified metric empirical equations
    power_watts = 5.3e-15 * (rpm_loaded ** 3) * (prop_diameter_in ** 4) * prop_pitch_in
    
    # Static Thrust (grams)
    thrust_grams = 2.83e-5 * (rpm_loaded ** 2) * (prop_diameter_in ** 4) * (prop_pitch_in / prop_diameter_in)
    
    # Current draw (Amps)
    # I = P / V / motor_efficiency
    motor_eff = 0.8
    current_amps = power_watts / voltage / motor_eff
    
    # Pitch speed (m/s)
    pitch_speed_ms = (rpm_loaded * p_m) / 60
    
    return {
        "motor_kv": motor_kv,
        "voltage": voltage,
        "prop_diameter_in": prop_diameter_in,
        "prop_pitch_in": prop_pitch_in,
        "rpm_no_load": rpm_no_load,
        "rpm_loaded": rpm_loaded,
        "thrust_grams": thrust_grams,
        "power_watts": power_watts,
        "current_amps": current_amps,
        "pitch_speed_ms": pitch_speed_ms
    }
