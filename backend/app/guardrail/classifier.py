import re
from datetime import datetime, timedelta
from fastapi import HTTPException
import httpx
from app.config import settings

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+instructions",
    r"you\s+are\s+now\s+(a|an|the)",
    r"(pretend|act|behave)\s+(you\s+are|as\s+if|like\s+you)",
    r"(new|different|updated|your\s+real)\s+system\s+prompt",
    r"<\|?(system|im_start|im_end)\|?>",
    r"###\s*(system|instruction|prompt)",
    r"forget\s+(everything|all|your\s+instructions)",
    r"(disregard|bypass|override|ignore)\s+(your\s+)?(guidelines|rules|instructions|training)",
    r"do\s+anything\s+now",
    r"jailbreak",
    r"prompt\s+injection",
    r"you\s+have\s+no\s+(restrictions|limits|rules)",
]

VIOLATION_WINDOW_SECONDS = 3600   # 1-hour rolling window
SOFT_BLOCK_THRESHOLD = 3          # violations before soft block
ADMIN_FLAG_THRESHOLD = 5          # total violations before admin flag


async def run_guardrail(
    text: str,
    student_id: str,
    ip: str,
    redis_client,
    db,
) -> None:
    """
    Four-stage guardrail pipeline. Raises HTTPException on any violation.
    On clean pass, returns None. Never silently passes through.
    """
    # Stage 1 — Regex fast-check (~0ms)
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text.lower()):
            await _handle_violation(student_id, ip, "injection_attempt", text, redis_client, db)
            raise HTTPException(status_code=422, detail="Request not permitted.")

    # Stage 2 + 3 — Semantic check (guardrail container, ~150ms)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                settings.guardrail_url,
                json={"text": text[:1000]},
            )
        result = resp.json()
    except Exception:
        # Fail closed — if guardrail is unreachable, block the request
        raise HTTPException(status_code=503, detail="Content classification temporarily unavailable.")

    if result["verdict"] == "off_topic":
        raise HTTPException(
            status_code=422,
            detail="I can only assist with study abroad and university admission topics.",
        )

    if result["verdict"] == "injection_attempt":
        await _handle_violation(student_id, ip, "injection_attempt", text, redis_client, db)
        raise HTTPException(status_code=422, detail="Request not permitted.")

    # Stage 4 — Violation accumulator (~1ms)
    count = await _get_violation_count(student_id, redis_client)
    if count >= SOFT_BLOCK_THRESHOLD:
        raise HTTPException(
            status_code=403,
            detail="Account restricted due to repeated policy violations. Contact support.",
        )


async def _handle_violation(
    student_id: str, ip: str, violation_type: str, raw_input: str, redis_client, db
) -> None:
    # Persist to DB (truncated)
    await db.execute(
        """
        INSERT INTO guardrail_violations (student_id, violation_type, raw_input, ip_address)
        VALUES (:s, :v, :r, :ip)
        """,
        {
            "s": student_id, "v": violation_type,
            "r": raw_input[:500], "ip": ip,
        },
    )

    # Increment rolling-window counter in Redis
    window_key = f"violations:{student_id}:window"
    total_key  = f"violations:{student_id}:total"
    await redis_client.incr(window_key)
    await redis_client.expire(window_key, VIOLATION_WINDOW_SECONDS)
    total = await redis_client.incr(total_key)

    # Flag account in audit log if threshold exceeded
    if total >= ADMIN_FLAG_THRESHOLD:
        await db.execute(
            """
            INSERT INTO audit_logs (student_id, action, details)
            VALUES (:s, 'guardrail_flag', :d)
            """,
            {
                "s": student_id,
                "d": {"total_violations": total, "violation_type": violation_type},
            },
        )


async def _get_violation_count(student_id: str, redis_client) -> int:
    raw = await redis_client.get(f"violations:{student_id}:window")
    return int(raw or 0)
