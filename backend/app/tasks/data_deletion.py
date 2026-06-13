from datetime import datetime, timedelta
from celery import shared_task
from sqlalchemy import text
from app.database import AsyncSessionLocal


@shared_task(name="app.tasks.data_deletion.check_retention_deadlines")
def check_retention_deadlines():
    import asyncio
    asyncio.run(_run_retention())


async def _run_retention():
    async with AsyncSessionLocal() as db:
        cutoff_5yr = datetime.utcnow() - timedelta(days=365 * 5)
        cutoff_notify = cutoff_5yr + timedelta(days=60)

        # Notify students approaching deletion
        result = await db.execute(
            text("""
                SELECT id, email, last_active_at
                FROM students
                WHERE last_active_at < :cutoff_notify
                  AND deletion_notified_at IS NULL
                  AND is_active = TRUE
            """),
            {"cutoff_notify": cutoff_notify},
        )
        for row in result.fetchall():
            deletion_date = row.last_active_at + timedelta(days=365 * 5 + 60)
            await _notify_student(row.id, row.email, deletion_date)
            await db.execute(
                text("UPDATE students SET deletion_notified_at = NOW() WHERE id = :id"),
                {"id": row.id},
            )

        # Crypto-erase students past deadline
        cutoff_delete = cutoff_5yr - timedelta(days=60)
        result = await db.execute(
            text("""
                SELECT id FROM students
                WHERE last_active_at < :cutoff
                  AND deletion_notified_at IS NOT NULL
            """),
            {"cutoff": cutoff_delete},
        )
        for row in result.fetchall():
            await _crypto_erase(row.id, db)

        await db.commit()


async def _notify_student(student_id, email: str, deletion_date: datetime):
    """Send pre-deletion notification email. Stub — wire SMTP in production."""
    print(f"[RETENTION] Notify {email}: deletion scheduled {deletion_date.date()}")


async def _crypto_erase(student_id, db):
    """
    Destroy per-student encryption key and overwrite PII fields.
    Documents on NAS should be securely deleted separately.
    """
    await db.execute(
        text("""
            UPDATE students
            SET email            = 'deleted-' || id || '@erased',
                full_name        = '[DELETED]',
                phone            = NULL,
                password_hash    = '',
                encryption_key_id = NULL,
                is_active        = FALSE
            WHERE id = :id
        """),
        {"id": student_id},
    )
    print(f"[RETENTION] Crypto-erased student {student_id}")
