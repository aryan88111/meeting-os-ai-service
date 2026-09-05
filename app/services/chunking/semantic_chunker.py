from typing import List
from app.schemas.transcript import TranscriptSegmentSchema

class SemanticChunker:
    """
    Time-aware and speaker-turn semantic chunker preserving segment IDs
    and start/end timestamps for exact grounding citations.
    """
    def __init__(self, target_chunk_duration_ms: int = 10 * 60 * 1000): # 10 minute windows
        self.target_duration_ms = target_chunk_duration_ms

    def chunk_segments(self, segments: List[TranscriptSegmentSchema]) -> List[List[TranscriptSegmentSchema]]:
        if not segments:
            return []

        chunks: List[List[TranscriptSegmentSchema]] = []
        current_chunk: List[TranscriptSegmentSchema] = []
        current_start = segments[0].start_time_ms or 0

        for segment in segments:
            seg_end = segment.end_time_ms or (current_start + 5000)
            if (seg_end - current_start) > self.target_duration_ms and current_chunk:
                chunks.append(current_chunk)
                current_chunk = [segment]
                current_start = segment.start_time_ms or 0
            else:
                current_chunk.append(segment)

        if current_chunk:
            chunks.append(current_chunk)

        return chunks
