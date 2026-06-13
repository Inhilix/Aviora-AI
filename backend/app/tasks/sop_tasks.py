import asyncio
import json
import anthropic
import redis.asyncio as aioredis
from app.tasks.celery_app import celery_app
from app.agents.llm_agent import SYSTEM_PROMPT
from app.security.pii import strip_pii
from app.security.cost_guard import record_api_cost
from app.config import settings


@celery_app.task(bind=True, queue="llm", name="app.tasks.sop_tasks.generate_sop")
def generate_sop(self, student_context: dict, university_name: str, additional_context: str = ""):
    """
    Celery task: generate SOP draft, stream chunks to Redis pub/sub.
    Frontend SSE endpoint subscribes to sop_stream:{task_id}.
    """
    task_id = self.request.id
    asyncio.run(_generate_sop_async(task_id, student_context, university_name, additional_context))


async def _generate_sop_async(
    task_id: str,
    student_context: dict,
    university_name: str,
    additional_context: str,
):
    redis_client = aioredis.from_url(settings.redis_url)

    prompt = _build_sop_prompt(student_context, university_name, additional_context)
    clean_prompt, _ = strip_pii(prompt, student_context.get("full_name"))

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    full_text = []

    try:
        async with client.messages.stream(
            model=settings.haiku_model,
            max_tokens=1200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": clean_prompt}],
        ) as stream:
            async for chunk in stream.text_stream:
                full_text.append(chunk)
                await redis_client.publish(f"sop_stream:{task_id}", chunk)

            final = await stream.get_final_message()

        # Store result for polling
        result = {
            "status": "complete",
            "content": "".join(full_text),
            "input_tokens": final.usage.input_tokens,
            "output_tokens": final.usage.output_tokens,
        }
        await redis_client.set(f"task_result:{task_id}", json.dumps(result), ex=3600)

        # Signal stream end
        await redis_client.publish(f"sop_stream:{task_id}", "__DONE__")

    except Exception as exc:
        error = {"status": "failed", "error": str(exc)}
        await redis_client.set(f"task_result:{task_id}", json.dumps(error), ex=3600)
        await redis_client.publish(f"sop_stream:{task_id}", "__ERROR__")
    finally:
        await redis_client.aclose()


def _build_sop_prompt(student_context: dict, university_name: str, additional_context: str) -> str:
    return f"""
Write a compelling Statement of Purpose for:

University: {university_name}
Degree: {student_context.get('target_degree')} in {student_context.get('target_subject')}
GPA: {student_context.get('gpa')}/{student_context.get('gpa_scale')}
IELTS: {student_context.get('ielts_overall')}
Work experience: {student_context.get('work_experience_months')} months
Gap years: {student_context.get('gap_years')}
Target countries: {', '.join(student_context.get('target_countries') or [])}

Additional context from student:
{additional_context or 'None provided.'}

Requirements:
- 600–900 words
- Professional academic tone
- Address why this university and programme specifically
- Connect student background to future goals
- Be honest about any weaknesses (gap years, lower GPA) — don't omit them
"""
