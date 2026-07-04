import uuid
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User, Project, CalculationHistory
from .schemas import ProjectCreate, ProjectUpdate, CalculationHistoryCreate
from .auth import hash_password


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    return await db.get(User, user_id)


async def create_user(db: AsyncSession, email: str, password: str, name: Optional[str] = None) -> User:
    user = User(email=email, hashed_password=hash_password(password), name=name)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def create_project(db: AsyncSession, user_id: uuid.UUID, payload: ProjectCreate) -> Project:
    project = Project(user_id=user_id, name=payload.name, project_type=payload.project_type, data=payload.data)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def list_projects_for_user(db: AsyncSession, user_id: uuid.UUID) -> Sequence[Project]:
    result = await db.execute(select(Project).where(Project.user_id == user_id).order_by(Project.updated_at.desc()))
    return result.scalars().all()


async def get_project(db: AsyncSession, user_id: uuid.UUID, project_id: uuid.UUID) -> Optional[Project]:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def update_project(db: AsyncSession, project: Project, payload: ProjectUpdate) -> Project:
    if payload.name is not None:
        project.name = payload.name
    if payload.data is not None:
        project.data = payload.data
    await db.commit()
    await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project: Project) -> None:
    await db.delete(project)
    await db.commit()


async def log_calculation(db: AsyncSession, user_id: uuid.UUID, payload: CalculationHistoryCreate) -> CalculationHistory:
    record = CalculationHistory(
        user_id=user_id,
        calculator_type=payload.calculator_type,
        inputs=payload.inputs,
        results=payload.results,
        computation_time_ms=payload.computation_time_ms,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def list_calculation_history(
    db: AsyncSession, user_id: uuid.UUID, calculator_type: Optional[str] = None, limit: int = 50
) -> Sequence[CalculationHistory]:
    query = select(CalculationHistory).where(CalculationHistory.user_id == user_id)
    if calculator_type:
        query = query.where(CalculationHistory.calculator_type == calculator_type)
    query = query.order_by(CalculationHistory.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
