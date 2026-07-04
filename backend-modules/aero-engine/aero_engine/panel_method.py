import numpy as np
from scipy.linalg import solve
from typing import Dict, Tuple, List
from .naca_generator import AirfoilCoordinates

class VortexPanelMethod:
    """
    2D vortex panel method for airfoil analysis
    """
    
    def analyze(
        self,
        airfoil: AirfoilCoordinates,
        alpha_deg: float,
        reynolds: float = 1e6,
        n_panels: int = 100
    ) -> Dict:
        # Combine upper and lower surfaces
        x = np.concatenate([airfoil.x_upper, airfoil.x_lower[1:]])
        y = np.concatenate([airfoil.y_upper, airfoil.y_lower[1:]])
        
        # Ensure closed contour
        if not (np.isclose(x[0], x[-1]) and np.isclose(y[0], y[-1])):
            x = np.append(x, x[0])
            y = np.append(y, y[0])
        
        # Resample to n_panels
        x_panels, y_panels = self._resample_airfoil(x, y, n_panels)
        
        # Calculate panel properties
        panels = self._create_panels(x_panels, y_panels)
        
        # Build and solve influence matrix
        gamma = self._solve_panel_system(panels, alpha_deg)
        
        # Calculate surface velocities
        velocities = self._calculate_velocities(panels, gamma, alpha_deg)
        
        # Pressure coefficient
        Cp = 1 - velocities**2  # Bernoulli (incompressible)
        
        # Integrate forces
        Cl, Cd, Cm = self._integrate_forces(panels, Cp, alpha_deg)
        
        # Add viscous drag estimate
        Cd_viscous = self._estimate_viscous_drag(Cl, reynolds, airfoil.max_thickness)
        Cd_total = Cd + Cd_viscous
        
        # Control point locations for plotting
        xcp = np.array([p['xc'] for p in panels])
        ycp = np.array([p['yc'] for p in panels])
        
        return {
            'Cl': Cl,
            'Cd_inviscid': Cd,
            'Cd_viscous': Cd_viscous,
            'Cd_total': Cd_total,
            'Cm': Cm,
            'L_D': Cl / Cd_total if Cd_total > 1e-6 else np.inf,
            'Cp': Cp.tolist(),
            'x_cp': xcp.tolist(),
            'y_cp': ycp.tolist(),
            'velocities': velocities.tolist(),
            'gamma': gamma.tolist(),
            'convergence': 'converged'
        }
    
    def _resample_airfoil(self, x: np.ndarray, y: np.ndarray, n_panels: int) -> Tuple[np.ndarray, np.ndarray]:
        dx = np.diff(x)
        dy = np.diff(y)
        ds = np.sqrt(dx**2 + dy**2)
        s = np.concatenate([[0], np.cumsum(ds)])
        s_new = np.linspace(0, s[-1], n_panels + 1)
        x_new = np.interp(s_new, s, x)
        y_new = np.interp(s_new, s, y)
        return x_new, y_new
    
    def _create_panels(self, x: np.ndarray, y: np.ndarray) -> List[Dict]:
        panels = []
        n_panels = len(x) - 1
        for i in range(n_panels):
            xa, ya = x[i], y[i]
            xb, yb = x[i+1], y[i+1]
            xc = (xa + xb) / 2
            yc = (ya + yb) / 2
            dx = xb - xa
            dy = yb - ya
            S = np.sqrt(dx**2 + dy**2)
            beta = np.arctan2(dy, dx)
            panels.append({
                'xa': xa, 'ya': ya, 'xb': xb, 'yb': yb, 'xc': xc, 'yc': yc,
                'S': S, 'beta': beta, 'sin_beta': np.sin(beta), 'cos_beta': np.cos(beta)
            })
        return panels
    
    def _solve_panel_system(self, panels: List[Dict], alpha_deg: float) -> np.ndarray:
        n = len(panels)
        alpha = np.radians(alpha_deg)
        U_inf = 1.0
        u_inf = U_inf * np.cos(alpha)
        v_inf = U_inf * np.sin(alpha)
        
        A = np.zeros((n, n))
        b = np.zeros(n)
        
        for i, panel_i in enumerate(panels):
            xc, yc = panel_i['xc'], panel_i['yc']
            sin_beta_i = panel_i['sin_beta']
            cos_beta_i = panel_i['cos_beta']
            for j, panel_j in enumerate(panels):
                if i == j:
                    A[i, j] = 0.5
                else:
                    u, v = self._vortex_panel_influence(xc, yc, panel_j)
                    A[i, j] = -u * sin_beta_i + v * cos_beta_i
            b[i] = u_inf * sin_beta_i - v_inf * cos_beta_i
        
        # Kutta condition
        A[-1, :] = 0
        A[-1, 0] = 1.0
        A[-1, -1] = 1.0
        b[-1] = 0
        
        gamma = solve(A, b)
        return gamma
    
    def _vortex_panel_influence(self, x: float, y: float, panel: Dict) -> Tuple[float, float]:
        xa, ya = panel['xa'], panel['ya']
        xb, yb = panel['xb'], panel['yb']
        dx = x - xa
        dy = y - ya
        beta = panel['beta']
        xi = dx * np.cos(beta) + dy * np.sin(beta)
        eta = -dx * np.sin(beta) + dy * np.cos(beta)
        S = panel['S']
        if np.abs(eta) < 1e-10:
            eta = 1e-10
        r1 = np.sqrt(xi**2 + eta**2)
        r2 = np.sqrt((xi - S)**2 + eta**2)
        theta1 = np.arctan2(eta, xi)
        theta2 = np.arctan2(eta, xi - S)
        u_panel = (theta2 - theta1) / (2 * np.pi)
        v_panel = 0.5 / (2 * np.pi) * np.log(r2 / r1)
        u = u_panel * np.cos(beta) - v_panel * np.sin(beta)
        v = u_panel * np.sin(beta) + v_panel * np.cos(beta)
        return u, v
    
    def _calculate_velocities(self, panels: List[Dict], gamma: np.ndarray, alpha_deg: float) -> np.ndarray:
        alpha = np.radians(alpha_deg)
        U_inf = 1.0
        velocities = np.zeros(len(panels))
        for i, panel_i in enumerate(panels):
            xc, yc = panel_i['xc'], panel_i['yc']
            sin_beta = panel_i['sin_beta']
            cos_beta = panel_i['cos_beta']
            u_total = U_inf * np.cos(alpha)
            v_total = U_inf * np.sin(alpha)
            for j, panel_j in enumerate(panels):
                u_ind, v_ind = self._vortex_panel_influence(xc, yc, panel_j)
                u_total += gamma[j] * u_ind
                v_total += gamma[j] * v_ind
            velocities[i] = u_total * cos_beta + v_total * sin_beta
        return velocities
    
    def _integrate_forces(self, panels: List[Dict], Cp: np.ndarray, alpha_deg: float) -> Tuple[float, float, float]:
        alpha = np.radians(alpha_deg)
        cn = 0
        ca = 0
        cm = 0
        for i, panel in enumerate(panels):
            dx = panel['xb'] - panel['xa']
            dy = panel['yb'] - panel['ya']
            cn -= Cp[i] * dx
            ca -= Cp[i] * dy
            x_ref = 0.25
            cm -= Cp[i] * ((panel['xc'] - x_ref) * dy - panel['yc'] * dx)
        Cl = cn * np.cos(alpha) - ca * np.sin(alpha)
        Cd = cn * np.sin(alpha) + ca * np.cos(alpha)
        return Cl, Cd, cm
    
    def _estimate_viscous_drag(self, Cl: float, Re: float, thickness: float) -> float:
        if Re < 5e5:
            Cf = 1.328 / np.sqrt(Re)
        else:
            Cf = 0.074 / (Re ** 0.2)
        form_factor = 1 + 2 * thickness + 60 * thickness**4
        Cd_friction = 2 * Cf * form_factor
        Cd_pressure = 0.01 * abs(Cl)**1.5
        return Cd_friction + Cd_pressure
