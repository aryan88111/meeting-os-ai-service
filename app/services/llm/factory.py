from app.services.llm.base import BaseLLMProvider
from app.services.llm.gemini_provider import GeminiLLMProvider
from app.core.config import settings

class LLMProviderFactory:
    """
    Factory resolving active LLM Provider instance based on configuration.
    """
    @staticmethod
    def get_provider(provider_type: str = settings.AI_PROVIDER) -> BaseLLMProvider:
        provider_type = provider_type.lower()
        if provider_type == "gemini":
            return GeminiLLMProvider()
        # Additional providers: OpenAI, Ollama, Claude can be added here seamlessly
        return GeminiLLMProvider()
