from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models import Application, University
from app.schemas.schemas import ApplicationCreate, ApplicationResponse
from app.security.jwt import get_current_student_id
from app.security.rate_limit import limiter

router = APIRouter()

VALID_STATUSES = {"draft", "in_progress", "submitted", "interview", "offer", "rejected", "withdrawn"}


@router.get("/", response_model=List[ApplicationResponse])
@limiter.limit("60/minute")
async def list_applications(
    request: Request,
    student_id: str = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Application).where(Application.student_id == student_id))
    return result.scalars().all()


@router.post("/", response_model=ApplicationResponse, status_code=201)
@limiter.limit("20/minute")
async def create_application(
    request: Request,
    body: ApplicationCreate,
    student_id: str = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
):
    uni_result = await db.execute(select(University).where(University.id == body.university_id))
    if not uni_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="University not found")

    existing = await db.execute(
        select(Application).where(
            Application.student_id == student_id,
            Application.university_id == body.university_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Application already exists for this university")

    app_obj = Application(
        student_id=student_id,
        university_id=body.university_id,
        deadline=body.deadline,
        notes=body.notes,
    )
    db.add(app_obj)
    await db.flush()
    return app_obj


@router.patch("/{application_id}/status")
@limiter.limit("20/minute")
async def update_status(
    request: Request,
    application_id: str,
    status: str,
    student_id: str = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
):
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {VALID_STATUSES}")

    result = await db.execute(
        select(Application).where(
            Application.id == application_id,
            Application.student_id == student_id,
        )
    )
    app_obj = result.scalar_one_or_none()
    if not app_obj:
        raise HTTPException(status_code=404, detail="Application not found")

    app_obj.status = status
    if status == "submitted":
        from datetime import datetime
        app_obj.applied_at = datetime.utcnow()
    elif status == "offer":
        from datetime import datetime
        app_obj.offer_received_at = datetime.utcnow()

    return {"message": "Status updated", "status": status}
