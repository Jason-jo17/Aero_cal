from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class Surface(BaseModel):
    """A single lifting surface (wing, horizontal tail, or canard)."""
    span: float = Field(gt=0)
    root_chord: float = Field(gt=0)
    tip_chord: float = Field(gt=0)
    sweep_deg: float = Field(ge=-80, le=80, default=0.0)  # leading-edge sweep, degrees
    dihedral_deg: float = Field(ge=-80, le=80, default=0.0)
    twist_deg: float = 0.0
    airfoil: str = "0012"  # NACA 4-digit; reference/display only, not used in v1 stability math
    x_position: float = Field(ge=0)
    z_position: float = 0.0
    mount: Literal["high", "mid", "low"] = "mid"


class VerticalTail(BaseModel):
    """A single (unmirrored) vertical fin."""
    height: float = Field(gt=0)
    root_chord: float = Field(gt=0)
    tip_chord: float = Field(gt=0)
    sweep_deg: float = Field(ge=-80, le=80, default=0.0)  # leading-edge sweep, degrees
    airfoil: str = "0012"
    x_position: float = Field(ge=0)
    z_position: float = 0.0


class VTail(BaseModel):
    """A V-tail: full span of both panels combined, plus their shared dihedral angle."""
    span: float = Field(gt=0)
    root_chord: float = Field(gt=0)
    tip_chord: float = Field(gt=0)
    dihedral_v_deg: float = Field(ge=0, le=90)
    sweep_deg: float = 0.0  # leading-edge sweep, degrees
    airfoil: str = "0012"
    x_position: float = Field(ge=0)
    z_position: float = 0.0


class Fuselage(BaseModel):
    length: float = Field(gt=0)
    max_width: float = Field(gt=0)
    max_height: float = Field(gt=0)
    nose_length: float = Field(ge=0)
    tail_length: float = Field(ge=0)

    @model_validator(mode="after")
    def check_taper_sections_fit(self) -> "Fuselage":
        if self.nose_length + self.tail_length >= self.length:
            raise ValueError(
                "nose_length + tail_length must be less than the fuselage length"
            )
        return self


class MassProperties(BaseModel):
    mass_kg: float = Field(gt=0)
    cg_x_position: float = Field(ge=0)
    # Used only to estimate trim CL for the lateral (Cl-beta) sweep term.
    # Sea-level standard density (rho=1.225 kg/m^3) is assumed; there is no
    # altitude/atmosphere model in v1.
    cruise_speed_ms: float = Field(gt=0)


class AircraftConfig(BaseModel):
    configuration_type: Literal["conventional", "flying_wing", "canard", "t_tail", "v_tail"]
    wing: Surface
    horizontal_tail: Optional[Surface] = None
    vertical_tail: Optional[VerticalTail] = None
    canard: Optional[Surface] = None
    v_tail: Optional[VTail] = None
    fuselage: Fuselage
    mass: MassProperties

    @model_validator(mode="after")
    def check_surfaces_match_configuration_type(self) -> "AircraftConfig":
        t = self.configuration_type
        errors: list[str] = []

        def require(name: str, present: bool):
            if not present:
                errors.append(f"{t} configuration requires '{name}'")

        def forbid(name: str, present: bool):
            if present:
                errors.append(f"{t} configuration must not include '{name}'")

        if t in ("conventional", "t_tail"):
            require("horizontal_tail", self.horizontal_tail is not None)
            require("vertical_tail", self.vertical_tail is not None)
            forbid("canard", self.canard is not None)
            forbid("v_tail", self.v_tail is not None)
        elif t == "canard":
            require("canard", self.canard is not None)
            require("vertical_tail", self.vertical_tail is not None)
            forbid("horizontal_tail", self.horizontal_tail is not None)
            forbid("v_tail", self.v_tail is not None)
        elif t == "v_tail":
            require("v_tail", self.v_tail is not None)
            forbid("horizontal_tail", self.horizontal_tail is not None)
            forbid("vertical_tail", self.vertical_tail is not None)
            forbid("canard", self.canard is not None)
        elif t == "flying_wing":
            forbid("horizontal_tail", self.horizontal_tail is not None)
            forbid("vertical_tail", self.vertical_tail is not None)
            forbid("canard", self.canard is not None)
            forbid("v_tail", self.v_tail is not None)

        if errors:
            raise ValueError("; ".join(errors))
        return self
