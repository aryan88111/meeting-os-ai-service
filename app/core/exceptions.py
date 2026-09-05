class MeetingAIException(Exception):
    """Base exception for all MeetingOS AI worker errors."""
    pass

class SchemaValidationError(MeetingAIException):
    """Raised when LLM output fails Pydantic schema validation."""
    pass

class LLMTimeoutError(MeetingAIException):
    """Raised when LLM provider exceeds timeout window."""
    pass

class RateLimitError(MeetingAIException):
    """Raised when AI provider returns 429 Too Many Requests."""
    pass

class GroundingCheckError(MeetingAIException):
    """Raised when extracted item fails transcript grounding / citation check."""
    pass
