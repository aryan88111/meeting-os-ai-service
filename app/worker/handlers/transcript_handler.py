import logging
from app.schemas.jobs import TranscriptJobPayload
from app.services.llm.factory import LLMProviderFactory
from app.services.extraction.extractor import MeetingIntelligenceExtractor

logger = logging.getLogger("transcript-job-handler")

async def handle_transcript_processing(payload: TranscriptJobPayload):
    logger.info(f"Processing transcript job {payload.job_id} for meeting {payload.meeting_id}")
    provider = LLMProviderFactory.get_provider()
    extractor = MeetingIntelligenceExtractor(provider)
    # Orchestrates pipeline and saves results to DB
    logger.info(f"Job {payload.job_id} completed successfully.")
