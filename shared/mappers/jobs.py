from shared.db.models import Job
from shared.schemas.jobs import JobResponse


def to_job_response(job: Job) -> JobResponse:
    return JobResponse(
        job_id=job.id,
        status=job.status,
        created_at=job.created_at,
        progress=job.progress,
        current_step=job.current_step,
        error_message=job.error_message,
        result=job.result,  # TODO: check typing warning
    )

def to_job_responses(jobs: list[Job]) -> list[JobResponse]:
    return [to_job_response(job) for job in jobs]