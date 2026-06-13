import uuid
import json
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis

from app.database import get_db
from app.models import Profile, Student
from app.schemas.schemas import InterviewMessageRequest, InterviewMessageResponse
from app.security.jwt import get_current_student_id
from app.security.rate_limit import limiter
from app.guardrail.classifier import run_guardrail
from app.agents.llm_agent import call_haiku_safe
from app.config import settings

router = APIRouter()

INTERVIEW_SYSTEM = """You are a UK visa officer conducting a mock student visa interview.
Ask pointed, realistic questions about:
- Why this university and course
- Career plans post-study
- Ties to home country (reason to return)
- Financial capability
- English language proficiency

Be direct and professional. Probe vague answers. Do not help the student rehearse misleading answers.
Evaluate responses honestly and flag weak answers explicitly."""


@router.post("/message", response_model=InterviewMessageResponse)
@limiter.limit("5/minute;50/hour;200/day")
async def send_message(
    request: Request,
    body: InterviewMessageRequest,
    student_id: str = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
):
    redis_client = aioredis.from_url(settings.redis_url)

    # Guardrail
    ip = request.headers.get("X-Forwarded-For", request.client.host)
    await run_guardrail(body.message, student_id, ip, redis_client, db)

    # Load or create session
    session_id = body.session_id or str(uuid.uuid4())
    history_key = f"interview:{student_id}:{session_id}"
    raw = await redis_client.get(history_key)
    history = json.loads(raw) if raw else []

    # Load student context
    student_result = await db.execute(select(Student).where(Student.id == student_id))
    student = student_result.scalar_one()

    profile_result = await db.execute(select(Profile).where(Profile.student_id == student_id))
    profile = profile_result.scalar_one_or_none()

    context = f"Student profile: GPA {getattr(profile, 'gpa', 'N/A')}, IELTS {getattr(profile, 'ielts_overall', 'N/A')}"
    history.append({"role": "user", "content": body.message})

    prompt = f"{INTERVIEW_SYSTEM}\n\n{context}\n\nConversation so far:\n"
    prompt += "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history[-10:])
    prompt += "\n\nRespond as the visa officer:"

    response_text = await call_haiku_safe(
        prompt, student_id, "mock_interview", student.full_name, redis_client, db
    )

    history.append({"role": "assistant", "content": response_text})
    await redis_client.set(history_key, json.dumps(history), ex=3600)
    await redis_client.aclose()

    return InterviewMessageResponse(
        session_id=session_id,
        response=response_text,
    )
