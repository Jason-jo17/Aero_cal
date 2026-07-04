import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, ConfigDict


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: Optional[str] = None
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ProjectCreate(BaseModel):
    name: str
    project_type: str
    data: dict[str, Any] = {}


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    data: Optional[dict[str, Any]] = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    project_type: str
    data: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CalculationHistoryCreate(BaseModel):
    calculator_type: str
    inputs: dict[str, Any] = {}
    results: dict[str, Any] = {}
    computation_time_ms: Optional[int] = None


class CalculationHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    calculator_type: str
    inputs: dict[str, Any]
    results: dict[str, Any]
    computation_time_ms: Optional[int] = None
    created_at: datetime
