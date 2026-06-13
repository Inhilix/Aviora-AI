# students.py — student self-service endpoints
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Student, AuditLog
from app.security.jwt import get_current_student_id
from app.security.rate_limit import limiter

router = APIRouter()


@router.get("/me")
@limiter.limit("60/minute")
async def get_me(
    request: Request,
    student_id: str = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "id": str(student.id),
        "email": student.email,
        "full_name": student.full_name,
        "created_at": student.created_at,
    }


@router.delete("/me")
@limiter.limit("3/day")
async def request_account_deletion(
    request: Request,
    student_id: str = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Self-service GDPR-style deletion request.
    Immediately deactivates the account and schedules crypto-erase in 30 days,
    giving the student a grace period to cancel by logging back in.
    """
    from datetime import datetime, timedelta
    from sqlalchemy import update

    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Not found")

    student.is_active = False
    student.deletion_scheduled_at = datetime.utcnow() + timedelta(days=30)

    db.add(AuditLog(
        student_id=student_id,
        action="account_deletion_requested",
        details={"scheduled_for": student.deletion_scheduled_at.isoformat()},
    ))

    response = JSONResponse(content={
        "message": "Account deactivated. Permanent deletion in 30 days unless you log back in to cancel.",
        "scheduled_for": student.deletion_scheduled_at.isoformat(),
    })
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response
