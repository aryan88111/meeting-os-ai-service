from abc import ABC, abstractmethod
from typing import Type, TypeVar, List, Dict, Any, Optional
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class BaseLLMProvider(ABC):
    """
    Abstract interface for LLM providers (Gemini, OpenAI, Ollama, Claude).
    Ensures the business logic never depends directly on a specific vendor SDK.
    """
    @abstractmethod
    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        pass

    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        pass
