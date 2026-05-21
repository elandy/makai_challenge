import uuid
from datetime import datetime, UTC
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models import Job, JobStatus
from shared.domain.auth import User
from shared.domain.jobs import JobStep
from shared.schemas.jobs import JobInput


async def create(db: AsyncSession, user: User, input: JobInput) -> Job:
    job = Job(id=uuid.uuid4(), user_id=user.id, status=JobStatus.QUEUED, payload=input.model_dump())
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_by_id(db: AsyncSession, user: User, job_id: uuid.UUID) -> Job | None:
    stmt = select(Job).where(
        Job.id == job_id,
        Job.user_id == user.id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_jobs(db: AsyncSession, user: User, ) -> list[Job]:
    stmt = select(Job).where(Job.user_id == user.id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_by_id_for_worker(db: AsyncSession, job_id: uuid.UUID) -> Job | None:
    stmt = select(Job).where(Job.id == job_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def mark_running(db: AsyncSession, job_id: uuid.UUID) -> None:
    job = await get_by_id_for_worker(db, job_id)
    if not job: return

    job.status = JobStatus.RUNNING
    job.started_at = datetime.now(UTC)
    await db.commit()


async def mark_cancelled(db: AsyncSession, job_id: uuid.UUID) -> None:
    job = await get_by_id_for_worker(db, job_id)
    if not job: return

    job.status = JobStatus.CANCELLED
    job.completed_at = datetime.now(UTC)
    await db.commit()


async def update_progress(db: AsyncSession, job_id: uuid.UUID,  progress: int, current_step: JobStep) -> None:
    job = await get_by_id_for_worker(db, job_id)
    if not job: return

    job.progress = progress
    job.current_step = current_step
    await db.commit()


async def complete_job(db: AsyncSession, job_id: uuid.UUID, result: dict[str, Any]) -> None:
    job = await get_by_id_for_worker(db, job_id)
    if not job: return

    job.status = JobStatus.COMPLETED
    job.progress = 100
    job.result = result
    job.completed_at = datetime.now(UTC)
    await db.commit()


async def fail_job(db: AsyncSession, job_id: uuid.UUID, error: str) -> None:
    job = await get_by_id_for_worker(db, job_id)
    if not job: return

    job.status = JobStatus.FAILED
    job.error = error
    job.completed_at = datetime.now(UTC)
    await db.commit()


async def request_cancellation(db: AsyncSession, job_id: uuid.UUID) -> None:
    job = await get_by_id_for_worker(db, job_id)
    if not job: return

    job.cancel_requested = True
    await db.commit()


async def reset_for_retry(db: AsyncSession, job_id: uuid.UUID) -> None:
    job = await get_by_id_for_worker(db, job_id)
    if not job: return

    job.status = JobStatus.QUEUED
    job.progress = 0
    job.current_step = None
    job.error = None
    job.result = None
    job.cancel_requested = False
    job.started_at = None
    job.completed_at = None

    job.attempt_count += 1
    await db.commit()