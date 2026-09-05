from pydantic import BaseModel, Field
from typing import Optional

class TranscriptJobPayload(BaseModel):
    job_id: str
    meeting_id: str
    organization_id: str
    transcript_id: str
    attempt: int = 1

class DocumentJobPayload(BaseModel):
    job_id: str
    meeting_id: str
    organization_id: str
    document_type: str = "PDF"
    version: int = 1

class EmbeddingJobPayload(BaseModel):
    job_id: str
    meeting_id: str
    organization_id: str
    transcript_id: str
