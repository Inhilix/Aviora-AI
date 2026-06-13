"""
Daily deadline alert task.
Checks applications/universities with upcoming deadlines and emails students.
"""
import asyncio
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from celery import shared_task
from sqlalchemy import text
from app.database import AsyncSessionLocal
from app.config import settings

ALERT_WINDOWS_DAYS = [30, 14, 7, 3, 1]


@shared_task(name="app.tasks.deadline_alerts.send_deadline_alerts")
def send_deadline_alerts():
    asyncio.run(_run_alerts())


async def _run_alerts():
    async with AsyncSessionLocal() as db:
        today = datetime.utcnow().date()

        for days in ALERT_WINDOWS_DAYS:
            target_date = today + timedelta(days=days)

            # Applications with explicit deadlines
            result = await db.execute(
                text("""
                    SELECT a.id, a.deadline, s.email, s.full_name, u.name AS university_name
                    FROM applications a
                    JOIN students s ON s.id = a.student_id
                    JOIN universities u ON u.id = a.university_id
                    WHERE a.deadline = :target_date
                      AND a.status NOT IN ('submitted', 'rejected', 'withdrawn')
                      AND s.is_active = TRUE
                """),
                {"target_date": target_date},
            )
            for row in result.fetchall():
                _send_email(
                    to=row.email,
                    subject=f"Deadline Reminder: {row.university_name} in {days} day(s)",
                    body=(
                        f"Hi {row.full_name},\n\n"
                        f"Your application deadline for {row.university_name} is on "
                        f"{row.deadline.strftime('%d %B %Y')} ({days} day(s) from now).\n\n"
                        f"Please make sure all required documents are uploaded and your "
                        f"application is complete.\n\n— StudyAI"
                    ),
                )

            # University-wide deadlines for students who haven't created an application yet
            result = await db.execute(
                text("""
                    SELECT DISTINCT s.id AS student_id, s.email, s.full_name,
                           u.name AS university_name, u.application_deadline
                    FROM students s
                    JOIN profiles p ON p.student_id = s.id
                    JOIN universities u ON u.country = ANY(p.target_countries)
                    WHERE u.application_deadline = :target_date
                      AND s.is_active = TRUE
                      AND NOT EXISTS (
                          SELECT 1 FROM applications a
                          WHERE a.student_id = s.id AND a.university_id = u.id
                      )
                """),
                {"target_date": target_date},
            )
            for row in result.fetchall():
                _send_email(
                    to=row.email,
                    subject=f"Upcoming Deadline: {row.university_name} ({days} days)",
                    body=(
                        f"Hi {row.full_name},\n\n"
                        f"{row.university_name} has an application deadline of "
                        f"{row.application_deadline.strftime('%d %B %Y')} ({days} day(s) from now). "
                        f"This matches your target countries — consider starting your application now.\n\n"
                        f"— StudyAI"
                    ),
                )


def _send_email(to: str, subject: str, body: str) -> None:
    if not settings.smtp_host:
        print(f"[EMAIL-STUB] To: {to} | {subject}")
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.smtp_user
    msg["To"] = to

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
    except Exception as exc:
        print(f"[EMAIL-ERROR] Failed to send to {to}: {exc}")
