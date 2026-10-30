import os
from celery import Celery

celery_app = Celery(
    "triagely",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)

@celery_app.task(name="verify_finding")
def verify_finding(finding_id: int):
    # Safe placeholder: intentionally does not execute code or payloads.
    # Replace with a separate hardened sandbox service, never Docker socket access here.
    return {
        "finding_id": finding_id,
        "result": "needs_human_review",
        "message": "Automated execution is disabled in this starter."
    }
