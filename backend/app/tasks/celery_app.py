from celery import Celery
from app.config import settings

celery_app = Celery(
    "studyai",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.sop_tasks",
        "app.tasks.interview_tasks",
        "app.tasks.deadline_alerts",
        "app.tasks.data_deletion",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.tasks.sop_tasks.*":       {"queue": "llm"},
        "app.tasks.interview_tasks.*": {"queue": "llm"},
        "app.tasks.deadline_alerts.*": {"queue": "alerts"},
        "app.tasks.data_deletion.*":   {"queue": "default"},
    },
    beat_schedule={
        "check-deadlines-daily": {
            "task": "app.tasks.deadline_alerts.send_deadline_alerts",
            "schedule": 86400,  # every 24h
        },
        "check-retention-daily": {
            "task": "app.tasks.data_deletion.check_retention_deadlines",
            "schedule": 86400,
        },
    },
)
