from pydantic import BaseModel, Field
from typing import Optional, List

class TranscriptSegmentSchema(BaseModel):
    id: Optional[str] = None
    speaker_id: Optional[str] = None
    speaker_name: Optional[str] = None
    text: str = Field(description="Utterance text")
    start_time_ms: Optional[int] = Field(default=None, description="Start timestamp in ms")
    end_time_ms: Optional[int] = Field(default=None, description="End timestamp in ms")
    confidence: Optional[float] = 1.0
    sequence: int = Field(description="Zero-indexed sequence in transcript")

class NormalizedTranscriptSchema(BaseModel):
    meeting_id: str
    language: str = "en"
    segments: List[TranscriptSegmentSchema] = Field(default_factory=list)
    raw_text: Optional[str] = None
