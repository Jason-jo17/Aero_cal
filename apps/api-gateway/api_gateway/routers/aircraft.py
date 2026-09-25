from fastapi import APIRouter, HTTPException

from aero_engine.aircraft.models import AircraftConfig
from aero_engine.aircraft.geometry import generate_aircraft_geometry
from aero_engine.aircraft.stability import analyze_stability

router = APIRouter(prefix="/aircraft", tags=["Aircraft Design"])


@router.post("/design")
def design_aircraft(config: AircraftConfig):
    try:
        geometry = generate_aircraft_geometry(config)
        stability = analyze_stability(config, geometry)
        return {"geometry": geometry, "stability": stability}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
