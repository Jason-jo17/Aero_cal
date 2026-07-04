import math

def generate_polar_curve(camber_percent: float, thickness_percent: float, min_alpha: float = -10, max_alpha: float = 20, step: float = 1):
    """
    Generate simplified lift and drag polars based on thin airfoil theory and empirical corrections.
    """
    alphas = []
    cl_values = []
    cd_values = []
    cm_values = []
    
    # Lift slope (ideal is 2*pi, empirical is usually slightly less, around 0.1 per degree)
    a0 = 0.105 
    
    # Zero-lift angle of attack (approx -camber_percent)
    alpha_L0 = -camber_percent
    
    # Stall parameters
    alpha_stall = 12 + (thickness_percent / 2)
    cl_max = a0 * (alpha_stall - alpha_L0)
    
    # Drag parameters
    cd_min = 0.005 + 0.0001 * thickness_percent
    
    for alpha in range(int(min_alpha), int(max_alpha) + 1):
        alpha_f = float(alpha)
        alphas.append(alpha_f)
        
        # Lift coefficient
        if alpha_f <= alpha_stall:
            cl = a0 * (alpha_f - alpha_L0)
        else:
            # Post-stall drop-off
            drop = 0.1 * (alpha_f - alpha_stall)
            cl = max(cl_max - drop, cl_max * 0.5)
            
        cl_values.append(cl)
        
        # Drag coefficient (quadratic polar)
        # Cd = Cd0 + K * Cl^2
        k = 0.015 # Simplified drag factor
        cd = cd_min + k * (cl ** 2)
        
        # Add stall drag penalty
        if alpha_f > alpha_stall:
            cd += 0.05 * (alpha_f - alpha_stall)
            
        cd_values.append(cd)
        
        # Moment coefficient (approx quarter chord)
        # Thin airfoil theory: Cm_c/4 is approx -pi/2 * (camber/100)
        cm = -0.05 * camber_percent
        cm_values.append(cm)
        
    return {
        "alpha": alphas,
        "cl": cl_values,
        "cd": cd_values,
        "cm": cm_values
    }
