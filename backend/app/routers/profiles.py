from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Profile
from app.schemas.schemas import ProfileCreate, ProfileResponse
from app.security.jwt import get_current_student_id
from app.security.rate_limit import limiter
from app.services.profile_scorer import score_profile

router = APIRouter()


@router.get("/", response_model=ProfileResponse)
@limiter.limit("60/minute")
async def get_profile(
    request: Request,
    student_id: str = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Profile).where(Profile.student_id == student_id))
    profile = result.scalar_one_or_none()
    if not profile:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("/", response_model=ProfileResponse, status_code=201)
@limiter.limit("10/minute")
async def create_or_update_profile(
    request: Request,
    body: ProfileCreate,
    student_id: str = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Profile).where(Profile.student_id == student_id))
    profile = result.scalar_one_or_none()

    profile_data = body.model_dump()
    score_result = score_profile(profile_data)
    profile_data["profile_score"] = score_result["total"]
    profile_data["score_breakdown"] = score_result["breakdown"]

    if profile:
        for k, v in profile_data.items():
            setattr(profile, k, v)
    else:
        profile = Profile(student_id=student_id, **profile_data)
        db.add(profile)

    await db.flush()
    return profile


@router.get("/score")
@limiter.limit("60/minute")
async def get_score(
    request: Request,
    student_id: str = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Profile).where(Profile.student_id == student_id))
    profile = result.scalar_one_or_none()
    if not profile:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Profile not found")
    score = score_profile({
        "gpa": profile.gpa, "gpa_scale": profile.gpa_scale,
        "ielts_overall": profile.ielts_overall,
        "financial_proof_usd": profile.financial_proof_usd,
        "work_experience_months": profile.work_experience_months,
        "gap_years": profile.gap_years,
    })
    return score
