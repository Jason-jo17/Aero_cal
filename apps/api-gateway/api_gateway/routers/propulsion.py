from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aero_engine.propulsion import calculate_propulsion

router = APIRouter(prefix="/propulsion", tags=["Propulsion"])

class PropulsionQuery(BaseModel):
    motor_kv: float
    voltage: float
    prop_diameter_in: float
    prop_pitch_in: float

@router.post("/motor-prop-match")
def match_motor_prop(query: PropulsionQuery):
    try:
        results = calculate_propulsion(
            query.motor_kv,
            query.voltage,
            query.prop_diameter_in,
            query.prop_pitch_in
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
