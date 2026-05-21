import logging
from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models import Job
from shared.db.repositories import jobs as jobs_repository
from shared.domain.auth import User
from shared.domain.jobs import JobStatus
from shared.queue.producer import enqueue_job
from shared.schemas.jobs import JobInput

logger = logging.getLogger(__name__)

class JobNotFoundError(Exception):
    pass

class JobService:

    @staticmethod
    async def submit_job(db: AsyncSession, user: User, job_input: JobInput) -> Job:
        job = await jobs_repository.create(db, user, job_input)
        logger.info(f"Created job with ID: {job.id} for user {user.username}")
        await enqueue_job(job.id)
        logger.info(f"Enqueued job with ID: {job.id} for user {user.username}")
        return job

    @staticmethod
    async def get_job(db: AsyncSession, user: User, job_id: UUID) -> Job:
        job = await jobs_repository.get_by_id(db, user, job_id)
        if not job: raise JobNotFoundError()
        return job

    @staticmethod
    async def get_jobs(db: AsyncSession, user: User) -> List[Job]:
        jobs = await jobs_repository.list_jobs(db, user)
        return jobs

    @staticmethod
    async def cancel_job(db: AsyncSession, user: User, job_id: UUID) -> Job:
        job = await jobs_repository.get_by_id(db, user, job_id)
        if not job: raise JobNotFoundError()
        if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            return job

        # If still queued, cancel immediately
        if job.status == JobStatus.QUEUED:
            await jobs_repository.mark_cancelled(db, job_id)

        # If already running, request cooperative cancellation
        elif job.status == JobStatus.RUNNING:
            await jobs_repository.request_cancellation(db, job_id)

        updated_job = await jobs_repository.get_by_id(db, user, job_id)
        if not updated_job: raise JobNotFoundError()
        logger.info(f"Cancelled job with ID: {job_id} for user {user.username}")
        return updated_job

    @staticmethod
    async def retry_job(db: AsyncSession, user: User, job_id: UUID) -> Job:
        job = await jobs_repository.get_by_id(db, user, job_id)

        if not job: raise JobNotFoundError()
        # Only failed/canceled jobs may be retried
        if job.status not in (JobStatus.FAILED, JobStatus.CANCELLED):
            return job

        await jobs_repository.reset_for_retry(db, job_id)
        await enqueue_job(job_id)
        updated_job = await jobs_repository.get_by_id(db, user, job_id)
        if not updated_job: raise JobNotFoundError()
        logger.info(f"Retried job with ID: {job_id} for user {user.username}")
        return updated_job