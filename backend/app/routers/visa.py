from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis

from app.database import get_db
from app.models import Student
from app.schemas.schemas import InterviewMessageRequest
from app.security.jwt import get_current_student_id
from app.security.rate_limit import limiter
from app.guardrail.classifier import run_guardrail
from app.services.rag import answer_with_rag
from app.config import settings

router = APIRouter()


@router.post("/ask")
@limiter.limit("10/minute;100/hour;300/day")
async def ask_visa_question(
    request: Request,
    body: InterviewMessageRequest,
    country: str | None = None,
    student_id: str = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
):
    """RAG-grounded Q&A on visa/admission topics, scoped to knowledge_base content."""
    redis_client = aioredis.from_url(settings.redis_url)

    ip = request.headers.get("X-Forwarded-For", request.client.host)
    await run_guardrail(body.message, student_id, ip, redis_client, db)

    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    response = await answer_with_rag(
        body.message, country, student_id, student.full_name, redis_client, db
    )
    await redis_client.aclose()
    return response
