import logging
from app.services.llm.base import BaseLLMProvider
from app.schemas.intelligence import MeetingIntelligenceSchema
from app.schemas.transcript import NormalizedTranscriptSchema

logger = logging.getLogger("meeting-extractor")

class MeetingIntelligenceExtractor:
    """
    Orchestrates the extraction of summaries, decisions, action items,
    and risks with schema validation and retry/repair logic.
    """
    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm = llm_provider

    async def extract_intelligence(
        self,
        transcript: NormalizedTranscriptSchema,
    ) -> MeetingIntelligenceSchema:
        logger.info(f"Extracting intelligence for meeting: {transcript.meeting_id}")
        
        prompt = f"Analyze the following meeting transcript and extract structured decisions, action items, risks, and summary:\n{transcript.raw_text}"
        system_prompt = "You are an executive meeting intelligence analyst. You extract verified facts and never hallucinate attendees or deadlines."

        return await self.llm.generate_structured(
            prompt=prompt,
            schema=MeetingIntelligenceSchema,
            system_prompt=system_prompt,
        )
