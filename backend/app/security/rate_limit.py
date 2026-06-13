from datetime import datetime
import time
from fastapi import HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.security.jwt import verify_token
from app.config import settings


def get_user_id(request: Request) -> str:
    token = request.cookies.get("access_token")
    if token:
        try:
            payload = verify_token(token)
            return payload.get("sub", get_remote_address(request))
        except Exception:
            pass
    return get_remote_address(request)


limiter = Limiter(
    key_func=get_user_id,
    storage_uri=f"{settings.redis_url.replace('/0', '/1')}",  # use DB 1 for rate limits
)


async def check_and_consume_token_budget(
    student_id: str,
    estimated_tokens: int,
    redis_client,
    db,
) -> None:
    """Atomic Redis check + increment for per-user daily token budget."""
    daily_limit = settings.daily_token_limit_per_user
    today = datetime.utcnow().date().isoformat()
    redis_key = f"token_budget:{student_id}:{today}"

    current = await redis_client.incrby(redis_key, estimated_tokens)

    # Set TTL on first write — expires at next midnight UTC
    if current == estimated_tokens:
        seconds_until_midnight = 86400 - int(time.time()) % 86400
        await redis_client.expire(redis_key, seconds_until_midnight)

    if current > daily_limit:
        # Roll back — don't consume budget we're going to reject
        await redis_client.decrby(redis_key, estimated_tokens)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "daily_limit_exceeded",
                "message": "Daily usage limit reached. Resets at midnight UTC.",
                "used": current - estimated_tokens,
                "limit": daily_limit,
            },
        )
