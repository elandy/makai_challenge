import asyncio
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models import JobStatus, JobStep
from shared.db.repositories import jobs as jobs_repository

logger = logging.getLogger(__name__)


async def process_job(db: AsyncSession, job_id: UUID, notifier) -> None:
    logger.info(f"Starting processing for job {job_id}")
    job = await jobs_repository.get_by_id_for_worker(db, job_id)
    if not job:
        logger.warning(f"Job {job_id} not found")
        return

    # Idempotency protection
    if job.status == JobStatus.COMPLETED:
        logger.info(f"Job {job_id} already completed")
        return

    if job.status == JobStatus.CANCELLED:
        logger.info(f"Job {job_id} already cancelled")
        return

    try:
        await jobs_repository.mark_running(db, job_id)

        # STEP 1 — Download document
        await jobs_repository.update_progress(db=db, job_id=job_id, progress=10, current_step=JobStep.DOWNLOAD)
        await asyncio.sleep(2)
        await check_cancellation(db, job_id)

        # STEP 2 — Extract text
        await jobs_repository.update_progress(db=db, job_id=job_id, progress=50, current_step=JobStep.EXTRACTING)
        await asyncio.sleep(3)
        await check_cancellation(db, job_id)

        # STEP 3 — Analyze document
        await jobs_repository.update_progress(db=db, job_id=job_id, progress=80, current_step=JobStep.ANALYZING)
        await asyncio.sleep(2)
        await check_cancellation(db, job_id)

        # Fake result
        result = {
            "summary": "Document processed successfully",
            "keywords": [
                "async",
                "document",
                "processing",
            ],
        }
        logger.info(f"completing job callback_url={job.payload.get('callback_url')}")

        await jobs_repository.complete_job(db=db, job_id=job_id, result=result)
        job = await jobs_repository.get_by_id_for_worker(db, job_id)

        if notifier and job:
            logger.info(f"NOTIFYING callback_url={job.payload.get('callback_url')}")
            await notifier.emit(
                user_id=str(job.user_id),
                event="job.completed",
                payload={
                    "callback_url": job.payload.get("callback_url"),
                    "job_id": str(job_id),
                    "result": result,
                },
            )

        logger.info(f"Successfully completed job {job_id}")

    except asyncio.CancelledError:
        logger.warning(f"Job {job_id} cancelled during execution")
        await jobs_repository.mark_cancelled(db=db, job_id=job_id)

    except Exception as e:
        logger.exception(f"Job {job_id} failed")
        await jobs_repository.fail_job(db=db, job_id=job_id, error=str(e))

        job = await jobs_repository.get_by_id_for_worker(db, job_id)

        if notifier and job:
            await notifier.emit(
                user_id=str(job.user_id),
                event="job.failed",
                payload={
                    "callback_url": job.payload.get("callback_url"),
                    "job_id": str(job_id),
                    "error": str(e),
                },
            )

async def check_cancellation(db: AsyncSession, job_id: UUID) -> None:
    job = await jobs_repository.get_by_id_for_worker(db, job_id)
    if not job: return
    if job.cancel_requested:
        raise asyncio.CancelledError()
