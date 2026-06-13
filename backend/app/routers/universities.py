from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List

from app.database import get_db
from app.models import University, Profile
from app.schemas.schemas import UniversityResponse
from app.security.jwt import get_current_student_id
from app.security.rate_limit import limiter
from app.services.profile_scorer import match_universities

router = APIRouter()


@router.get("/", response_model=List[UniversityResponse])
@limiter.limit("60/minute")
async def list_universities(
    request: Request,
    country: Optional[str] = Query(None),
    degree_level: Optional[str] = Query(None),
    max_tuition: Optional[int] = Query(None),
    student_id: str = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
):
    q = select(University)
    if country:
        q = q.where(University.country == country)
    if degree_level:
        q = q.where(University.degree_level == degree_level)
    if max_tuition:
        q = q.where(University.annual_tuition_usd <= max_tuition)

    result = await db.execute(q)
    universities = result.scalars().all()
    return universities


@router.get("/shortlist", response_model=List[UniversityResponse])
@limiter.limit("30/minute")
async def shortlist(
    request: Request,
    student_id: str = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
):
    """Return universities matched and scored against the student's profile."""
    profile_result = await db.execute(select(Profile).where(Profile.student_id == student_id))
    profile = profile_result.scalar_one_or_none()
    if not profile:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Complete your profile first")

    uni_result = await db.execute(select(University))
    universities = uni_result.scalars().all()

    profile_dict = {
        "gpa": float(profile.gpa or 0),
        "gpa_scale": float(profile.gpa_scale or 4.0),
        "ielts_overall": float(profile.ielts_overall or 0),
        "financial_proof_usd": profile.financial_proof_usd,
        "budget_usd_per_year": profile.budget_usd_per_year,
        "gap_years": profile.gap_years or 0,
        "target_countries": profile.target_countries or [],
        "target_degree": profile.target_degree,
    }

    matched = match_universities(profile_dict, universities)
    return matched[:20]  # top 20
