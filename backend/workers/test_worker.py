from backend.celery_app import celery_app


@celery_app.task(name="workers.ping", bind=True)
def ping(self) -> dict:
    """Health-check task — returns pong with task metadata."""
    return {"pong": True, "task_id": self.request.id}
