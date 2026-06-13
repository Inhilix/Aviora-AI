from datetime import datetime
from fastapi import HTTPException
from app.config import settings

HAIKU_INPUT_COST  = 0.00000025   # $0.25 / 1M input tokens
HAIKU_OUTPUT_COST = 0.00000125   # $1.25 / 1M output tokens


async def check_daily_cost_ceiling(redis_client) -> None:
    today = datetime.utcnow().date().isoformat()
    raw = await redis_client.get(f"daily_cost:{today}")
    current = float(raw or 0)
    if current >= settings.daily_cost_ceiling_usd:
        raise HTTPException(
            status_code=503,
            detail="Service temporarily at capacity. Try again tomorrow.",
        )


async def record_api_cost(
    student_id: str,
    endpoint: str,
    input_tokens: int,
    output_tokens: int,
    duration_ms: int,
    redis_client,
    db,
) -> float:
    cost = (input_tokens * HAIKU_INPUT_COST) + (output_tokens * HAIKU_OUTPUT_COST)
    today = datetime.utcnow().date().isoformat()

    await redis_client.incrbyfloat(f"daily_cost:{today}", cost)
    await redis_client.expire(f"daily_cost:{today}", 86400)

    await db.execute(
        """
        INSERT INTO api_usage
            (student_id, endpoint, input_tokens, output_tokens, cost_usd, duration_ms)
        VALUES (:s, :e, :i, :o, :c, :d)
        """,
        {
            "s": student_id, "e": endpoint,
            "i": input_tokens, "o": output_tokens,
            "c": cost, "d": duration_ms,
        },
    )
    return cost
