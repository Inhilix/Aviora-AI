from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
import redis.asyncio as aioredis
from datetime import datetime

from app.database import get_db
from app.models import Student, GuardrailViolation, ApiUsage
from app.schemas.schemas import AdminStudentResponse
from app.security.jwt import get_current_student_id
from app.security.rate_limit import limiter
from app.config import settings

router = APIRouter()


async def require_admin(student_id: str = Depends(get_current_student_id), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student or not student.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return student_id


@router.get("/students", response_model=List[AdminStudentResponse])
@limiter.limit("30/minute")
async def list_students(
    request: Request,
    admin_id: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Student).order_by(Student.created_at.desc()))
    return result.scalars().all()


@router.get("/violations")
@limiter.limit("30/minute")
async def get_violations(
    request: Request,
    admin_id: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GuardrailViolation).order_by(GuardrailViolation.created_at.desc()).limit(100)
    )
    violations = result.scalars().all()
    return [
        {
            "id": v.id,
            "student_id": str(v.student_id),
            "violation_type": v.violation_type,
            "created_at": v.created_at,
        }
        for v in violations
    ]


@router.get("/cost/today")
@limiter.limit("30/minute")
async def get_today_cost(
    request: Request,
    admin_id: str = Depends(require_admin),
):
    redis_client = aioredis.from_url(settings.redis_url)
    today = datetime.utcnow().date().isoformat()
    raw = await redis_client.get(f"daily_cost:{today}")
    await redis_client.aclose()
    return {
        "date": today,
        "cost_usd": float(raw or 0),
        "ceiling_usd": settings.daily_cost_ceiling_usd,
    }


@router.post("/students/{student_id}/deactivate")
@limiter.limit("10/minute")
async def deactivate_student(
    request: Request,
    student_id: str,
    admin_id: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    student.is_active = False
    return {"message": f"Student {student_id} deactivated"}
