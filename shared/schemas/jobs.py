from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from shared.domain.jobs import JobStatus, JobStep


class JobInput(BaseModel):
    """Used to post a pdf extraction job on the post job endpoint"""
    document_url: str
    extract_keywords: bool = True
    generate_summary: bool = True
    callback_url: str | None = None
    # email: str | None = None  # In case we implement email notification

class JobResponse(BaseModel):
    """Used to return a job from get job endpoint"""
    job_id: UUID
    status: JobStatus

    progress: int  = 0 # progress between 0 and 100
    current_step: JobStep | None = None
    
    attempt_count: int = 0
    max_attempts: int = 3
    error_message: str | None = None
    result: dict[str, Any] | None = None

    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None