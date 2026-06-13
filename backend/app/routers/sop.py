import json
import asyncio
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis

from app.database import get_db
from app.models import Profile, Student, University
from app.schemas.schemas import SopGenerateRequest, TaskStatusResponse
from app.security.jwt import get_current_student_id
from app.security.rate_limit import limiter
from app.guardrail.classifier import run_guardrail
from app.tasks.sop_tasks import generate_sop
from app.config import settings

router = APIRouter()


@router.post("/generate")
@limiter.limit("5/minute;50/hour;200/day")
async def generate(
    request: Request,
    body: SopGenerateRequest,
    student_id: str = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
):
    redis_client = aioredis.from_url(settings.redis_url)

    # Load student + profile
    student_result = await db.execute(select(Student).where(Student.id == student_id))
    student = student_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    profile_result = await db.execute(select(Profile).where(Profile.student_id == student_id))
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=400, detail="Complete your profile before generating an SOP")

    uni_result = await db.execute(select(University).where(University.id == body.university_id))
    university = uni_result.scalar_one_or_none()
    if not university:
        raise HTTPException(status_code=404, detail="University not found")

    # Guardrail on additional context if provided
    if body.additional_context:
        await run_guardrail(
            body.additional_context, student_id,
            request.headers.get("X-Forwarded-For", request.client.host),
            redis_client, db,
        )

    student_context = {
        "full_name": student.full_name,
        "gpa": float(profile.gpa or 0),
        "gpa_scale": float(profile.gpa_scale or 4.0),
        "ielts_overall": float(profile.ielts_overall or 0),
        "target_degree": profile.target_degree,
        "target_subject": profile.target_subject,
        "target_countries": profile.target_countries or [],
        "work_experience_months": profile.work_experience_months or 0,
        "gap_years": profile.gap_years or 0,
        "profile_score": profile.profile_score,
    }

    task = generate_sop.delay(student_context, university.name, body.additional_context or "")
    await redis_client.aclose()

    return {"task_id": task.id, "status": "queued"}


@router.get("/stream/{task_id}")
async def stream_sop(
    task_id: str,
    request: Request,
    student_id: str = Depends(get_current_student_id),
):
    """SSE endpoint — streams SOP text chunks from Redis pub/sub."""
    async def event_generator():
        redis_client = aioredis.from_url(settings.redis_url)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"sop_stream:{task_id}")
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                chunk = message["data"].decode("utf-8")
                if chunk in ("__DONE__", "__ERROR__"):
                    yield f"data: {chunk}\n\n"
                    break
                yield f"data: {chunk}\n\n"
                if await request.is_disconnected():
                    break
        finally:
            await pubsub.unsubscribe(f"sop_stream:{task_id}")
            await redis_client.aclose()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
@limiter.limit("60/minute")
async def get_task_status(
    request: Request,
    task_id: str,
    student_id: str = Depends(get_current_student_id),
):
    redis_client = aioredis.from_url(settings.redis_url)
    raw = await redis_client.get(f"task_result:{task_id}")
    await redis_client.aclose()

    if not raw:
        return TaskStatusResponse(task_id=task_id, status="in_progress")

    data = json.loads(raw)
    return TaskStatusResponse(
        task_id=task_id,
        status=data.get("status", "unknown"),
        result=data if data.get("status") == "complete" else None,
        error=data.get("error"),
    )
