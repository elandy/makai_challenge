from uuid import UUID

from pydantic import BaseModel


class JobQueuedMessage(BaseModel):
    job_id: UUID