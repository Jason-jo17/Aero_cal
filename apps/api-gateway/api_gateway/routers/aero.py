from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aero_engine.naca_generator import NACAGenerator, AirfoilCoordinates
from aero_engine.multirotor_performance import MultirotorCalculator, MultirotorConfig
from aero_engine.polar_curves import generate_polar_curve
from aero_engine.wing_planform import calculate_wing_planform
from aero_engine.panel_method import VortexPanelMethod

router = APIRouter(prefix="/aero", tags=["Aerodynamics"])

class NACAQuery(BaseModel):
    digits: str
    n_points: int = 200

@router.post("/naca")
def generate_naca(query: NACAQuery):
    generator = NACAGenerator()
    try:
        airfoil = generator.generate_4digit(query.digits, query.n_points)
        return {
            "name": airfoil.name,
            "x_upper": airfoil.x_upper.tolist(),
            "y_upper": airfoil.y_upper.tolist(),
            "x_lower": airfoil.x_lower.tolist(),
            "y_lower": airfoil.y_lower.tolist(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/multirotor")
def calculate_multirotor(config: dict):
    try:
        calc_config = MultirotorConfig(**config)
        calculator = MultirotorCalculator()
        results = calculator.calculate_performance(calc_config)
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class PolarQuery(BaseModel):
    camber_percent: float
    thickness_percent: float
    min_alpha: float = -10
    max_alpha: float = 20
    
@router.post("/polar-curves")
def get_polar_curves(query: PolarQuery):
    try:
        results = generate_polar_curve(
            query.camber_percent, 
            query.thickness_percent, 
            query.min_alpha, 
            query.max_alpha
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class WingPlanformQuery(BaseModel):
    span: float
    root_chord: float
    tip_chord: float
    sweep_angle_deg: float

@router.post("/wing-planform")
def get_wing_planform(query: WingPlanformQuery):
    try:
        results = calculate_wing_planform(
            query.span,
            query.root_chord,
            query.tip_chord,
            query.sweep_angle_deg
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class AirfoilAnalysisQuery(BaseModel):
    naca_digits: str
    alpha_deg: float
    reynolds: float = 1e6
    n_panels: int = 100

@router.post("/airfoil-analysis")
def analyze_airfoil(query: AirfoilAnalysisQuery):
    try:
        # First generate the airfoil
        generator = NACAGenerator()
        airfoil = generator.generate_4digit(query.naca_digits, query.n_panels)
        
        # Then analyze it with the panel method
        analyzer = VortexPanelMethod()
        results = analyzer.analyze(
            airfoil=airfoil,
            alpha_deg=query.alpha_deg,
            reynolds=query.reynolds,
            n_panels=query.n_panels
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
