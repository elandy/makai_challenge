from enum import Enum


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class JobStep(str, Enum):
    DOWNLOAD = "DOCUMENT_DOWNLOAD"
    EXTRACTING = "TEXT_EXTRACTION"
    ANALYZING = "KEYWORD_ANALYSIS"
