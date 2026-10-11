"""Database-backed background job queue with atomic claiming and crash recovery."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from app.modules.platform.models import Job
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

JobHandler = Callable[[dict[str, Any]], None]


class JobRunner:
    """Manages persistent background jobs with atomic claiming and recovery."""

    def __init__(self) -> None:
        self._handlers: dict[str, JobHandler] = {}

    def register_handler(self, job_type: str, handler: JobHandler) -> None:
        """Registers a worker handler for a given job type."""
        self._handlers[job_type] = handler

    def enqueue_job(
        self, session: Session, job_type: str, payload: dict[str, Any], max_retries: int = 3
    ) -> Job:
        """Enqueues a new background job into the database."""
        job = Job(
            job_type=job_type,
            payload=payload,
            status="pending",
            max_retries=max_retries,
        )
        session.add(job)
        session.commit()
        return job

    def claim_next_job(
        self, session: Session, worker_id: str, lock_timeout_seconds: int = 300
    ) -> Job | None:
        """
        Atomically claims the next pending or orphaned job.
        Recovers jobs left in 'running' status if their lock has timed out (restart-safe).
        """
        now = datetime.now(UTC)
        timeout_cutoff = now - timedelta(seconds=lock_timeout_seconds)

        # Select pending or timed-out running job
        stmt = (
            select(Job)
            .where(
                or_(
                    Job.status == "pending",
                    (Job.status == "running") & (Job.locked_at < timeout_cutoff),
                )
            )
            .order_by(Job.created_at)
            .limit(1)
        )

        # Apply skip_locked if supported by dialect
        bind = session.get_bind()
        if bind and bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update(skip_locked=True)

        job = session.scalars(stmt).first()
        if not job:
            return None

        job.status = "running"
        job.locked_at = now
        job.locked_by = worker_id
        session.commit()
        return job

    def execute_claimed_job(self, session: Session, job: Job) -> bool:
        """Executes the handler for a claimed job and records completion or failure."""
        handler = self._handlers.get(job.job_type)
        if not handler:
            logger.error(f"No handler registered for job type '{job.job_type}'")
            job.status = "failed"
            job.error_message = f"No handler registered for type {job.job_type}"
            session.commit()
            return False

        try:
            handler(job.payload)
            job.status = "completed"
            job.completed_at = datetime.now(UTC)
            session.commit()
            return True
        except Exception as exc:
            logger.exception(f"Job {job.id} execution failed: {exc}")
            job.retry_count += 1
            job.error_message = str(exc)
            job.status = "failed" if job.retry_count >= job.max_retries else "pending"
            session.commit()
            return False


job_runner = JobRunner()
