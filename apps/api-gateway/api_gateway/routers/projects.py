import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core_services import crud, schemas
from core_services.auth import get_current_user
from core_services.db import get_db
from core_services.models import User

router = APIRouter(tags=["Projects & History"])


@router.post("/projects", response_model=schemas.ProjectOut)
async def create_project(
    payload: schemas.ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await crud.create_project(db, current_user.id, payload)
    return schemas.ProjectOut.model_validate(project)


@router.get("/projects", response_model=list[schemas.ProjectOut])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    projects = await crud.list_projects_for_user(db, current_user.id)
    return [schemas.ProjectOut.model_validate(p) for p in projects]


@router.get("/projects/{project_id}", response_model=schemas.ProjectOut)
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await crud.get_project(db, current_user.id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return schemas.ProjectOut.model_validate(project)


@router.put("/projects/{project_id}", response_model=schemas.ProjectOut)
async def update_project(
    project_id: uuid.UUID,
    payload: schemas.ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await crud.get_project(db, current_user.id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project = await crud.update_project(db, project, payload)
    return schemas.ProjectOut.model_validate(project)


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await crud.get_project(db, current_user.id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await crud.delete_project(db, project)


@router.post("/calculations/history", response_model=schemas.CalculationHistoryOut)
async def create_calculation_history(
    payload: schemas.CalculationHistoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await crud.log_calculation(db, current_user.id, payload)
    return schemas.CalculationHistoryOut.model_validate(record)


@router.get("/calculations/history", response_model=list[schemas.CalculationHistoryOut])
async def get_calculation_history(
    calculator_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    records = await crud.list_calculation_history(db, current_user.id, calculator_type)
    return [schemas.CalculationHistoryOut.model_validate(r) for r in records]
