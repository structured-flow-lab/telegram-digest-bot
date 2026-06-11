"""Factory — selects the configured LLM provider."""

from app import config
from app.llm.base import LLMClient
from app.llm.claude import ClaudeClient


def get_llm_client() -> LLMClient:
    if config.LLM_PROVIDER == "claude":
        return ClaudeClient(model=config.LLM_MODEL)
    raise ValueError(f"Unknown LLM_PROVIDER: {config.LLM_PROVIDER!r}")
