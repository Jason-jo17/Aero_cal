import numpy as np
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class AirfoilCoordinates:
    x_upper: np.ndarray
    y_upper: np.ndarray
    x_lower: np.ndarray
    y_lower: np.ndarray
    name: str
    max_thickness: float
    max_camber: float
    camber_location: float

class NACAGenerator:
    """Generate NACA airfoil coordinates with complete equations"""
    
    def generate_4digit(
        self, 
        digits: str, 
        n_points: int = 200,
        cosine_spacing: bool = True
    ) -> AirfoilCoordinates:
        """
        Generate NACA 4-digit airfoil
        
        Format: MPXX
        M = maximum camber (% chord)
        P = location of maximum camber (tenths of chord)
        XX = maximum thickness (% chord)
        """
        
        # Parse digits
        m = int(digits[0]) / 100.0  # Maximum camber
        p = int(digits[1]) / 10.0   # Location of max camber
        t = int(digits[2:4]) / 100.0  # Thickness
        
        # Generate x-coordinates
        if cosine_spacing:
            # Cosine spacing for better resolution at leading edge
            beta = np.linspace(0, np.pi, n_points)
            x = (1 - np.cos(beta)) / 2
        else:
            # Linear spacing
            x = np.linspace(0, 1, n_points)
        
        # Thickness distribution (NACA equation)
        yt = 5 * t * (
            0.2969 * np.sqrt(x) 
            - 0.1260 * x 
            - 0.3516 * x**2 
            + 0.2843 * x**3 
            - 0.1015 * x**4  # Sharp trailing edge
        )
        
        # Camber line
        if m == 0:  # Symmetric airfoil
            yc = np.zeros_like(x)
            dyc_dx = np.zeros_like(x)
        else:
            yc = np.zeros_like(x)
            dyc_dx = np.zeros_like(x)
            
            # Forward of maximum camber (0 <= x < p)
            mask_forward = x < p
            if p > 0:
                yc[mask_forward] = (m / p**2) * (
                    2 * p * x[mask_forward] - x[mask_forward]**2
                )
                dyc_dx[mask_forward] = (2 * m / p**2) * (
                    p - x[mask_forward]
                )
            
            # Aft of maximum camber (p <= x <= 1)
            mask_aft = x >= p
            yc[mask_aft] = (m / (1 - p)**2) * (
                (1 - 2*p) + 2*p*x[mask_aft] - x[mask_aft]**2
            )
            dyc_dx[mask_aft] = (2 * m / (1 - p)**2) * (
                p - x[mask_aft]
            )
        
        # Angle of camber line
        theta = np.arctan(dyc_dx)
        
        # Upper and lower surface coordinates
        x_upper = x - yt * np.sin(theta)
        y_upper = yc + yt * np.cos(theta)
        
        x_lower = x + yt * np.sin(theta)
        y_lower = yc - yt * np.cos(theta)
        
        return AirfoilCoordinates(
            x_upper=x_upper[::-1],  # Reverse for clockwise ordering
            y_upper=y_upper[::-1],
            x_lower=x_lower,
            y_lower=y_lower,
            name=f"NACA {digits}",
            max_thickness=t,
            max_camber=m,
            camber_location=p
        )
