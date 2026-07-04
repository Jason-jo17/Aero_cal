from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class DfmIssue(BaseModel):
    severity: str
    category: str
    description: str
    location: Optional[Dict] = None
    recommendation: Optional[str] = None
    cost_impact: Optional[float] = None


class DesignReviewRequest(BaseModel):
    part_name: str
    manufacturing_process: str
    issues: List[DfmIssue]


class DesignReviewResponse(BaseModel):
    summary: str


class SolveRequest(BaseModel):
    goal: str
    domain: Literal["multirotor"]


class MultirotorConfigProposal(BaseModel):
    """Mirrors aero_engine.multirotor_performance.MultirotorConfig's field set.
    Kept as an independent schema (rather than importing aero-engine) so
    ai-agent stays a pure orchestration layer with no engine dependency -
    the proposed config is validated here, then sent over HTTP to
    api-gateway, which is the only service that runs the real physics."""

    model_config = ConfigDict(extra="forbid")

    frame_type: str = Field(description="e.g. 'quad_x', 'quad_+', 'hexa', 'octo_x'")
    frame_size: float = Field(description="motor-to-motor diagonal, mm")
    motor_kv: float
    motor_max_current: float = Field(description="amps")
    motor_weight: float = Field(description="grams, per motor")
    prop_diameter: float = Field(description="inches")
    prop_pitch: float = Field(description="inches")
    motor_efficiency: float = 0.85
    num_motors: int = 4
    prop_blades: int = 2
    battery_cells: int = Field(description="S rating, e.g. 4 for 4S")
    battery_capacity: float = Field(description="mAh")
    battery_c_rating: float
    battery_weight: float = Field(description="grams")
    esc_weight: float = Field(description="grams, per ESC")
    fc_weight: float = Field(description="flight controller weight, grams")
    frame_weight: float = Field(description="grams")
    payload_weight: float = Field(description="grams")
    required_flight_time: float = Field(default=0, description="minutes, 0 if unspecified")


class SolveProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reasoning: str = Field(description="Brief explanation of why these parameters were chosen")
    proposed_config: MultirotorConfigProposal


class SolveResponse(BaseModel):
    reasoning: str
    proposed_config: Dict[str, Any]
    simulated_results: Optional[Dict[str, Any]] = None
    target_met: Optional[bool] = None
    notes: Optional[str] = None
    error: Optional[str] = None
