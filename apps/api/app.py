import uuid
from typing import List
import httpx

from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from apps.api.services.jobs import JobService, JobNotFoundError
from shared.db.models import Job
from shared.db.session import get_db
from shared.domain.auth import User
from shared.mappers.jobs import to_job_response, to_job_responses
from shared.schemas.jobs import JobResponse, JobInput
from contextlib import asynccontextmanager
from shared.db.init_db import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
app = FastAPI(lifespan=lifespan)

def get_current_user():
    return User(id="test-user", username="test")  # stub, returns fake id

@app.exception_handler(JobNotFoundError)
async def job_not_found_handler(_, __):
    return JSONResponse(
        status_code=404,
        content={"detail": "Job not found"},
    )

@app.post("/jobs")
async def create_job(
        job_input: JobInput,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)) -> JobResponse:
    job = await JobService.submit_job(db, current_user, job_input)
    return to_job_response(job)

@app.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: uuid.UUID,
                     current_user: User = Depends(get_current_user),
                     db: AsyncSession = Depends(get_db)) -> JobResponse:
    job: Job = await JobService.cancel_job(db, current_user, job_id)
    return to_job_response(job)

@app.post("/jobs/{job_id}/retry")
async def retry_job(job_id: uuid.UUID,
                    current_user: User = Depends(get_current_user),
                    db: AsyncSession = Depends(get_db)) -> JobResponse:
    job: Job = await JobService.retry_job(db, current_user, job_id)
    return to_job_response(job)

@app.get("/jobs/{job_id}")
async def get_job(job_id: uuid.UUID,
                  current_user: User = Depends(get_current_user),
                  db: AsyncSession = Depends(get_db)) -> JobResponse:
    job: Job = await JobService.get_job(db, current_user, job_id)
    return to_job_response(job)

@app.get("/jobs")
async def get_jobs(current_user: User = Depends(get_current_user),
                   db: AsyncSession = Depends(get_db)) -> List[JobResponse]:
    jobs: List[Job] = await JobService.get_jobs(db, current_user)
    return to_job_responses(jobs)

