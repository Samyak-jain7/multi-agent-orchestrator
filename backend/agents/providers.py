"""
LLM Provider abstraction — Strategy Pattern

Adding a new provider:
1. Create a new class implementing LLMProviderStrategy
2. Register it in PROVIDER_REGISTRY
3. Done — no other code changes needed
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI


class LLMProviderStrategy(ABC):
    """Abstract base for all LLM providers."""

    _config: Dict[str, Any] = {}

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier for this provider."""
        pass

    @abstractmethod
    async def ainvoke(self, messages: List[BaseMessage]) -> BaseMessage:
        """Send messages to LLM and return response."""
        pass

    @abstractmethod
    def get_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform agent config into provider-specific kwargs."""
        pass

    def _resolve_from_env(self, env_vars: Dict[str, str], provider_key: str) -> None:
        """
        Auto-resolve api_key and base_url from env vars.
        e.g. MINIMAX_API_KEY, MINIMAX_BASE_URL → merged into _config
        """
        prefix = provider_key.upper()
        api_key = env_vars.get(f"{prefix}_API_KEY")
        base_url = env_vars.get(f"{prefix}_BASE_URL")
        model_name = env_vars.get(f"{prefix}_MODEL_NAME")

        self._config = {
            **self._config,
            **({"api_key": api_key} if api_key else {}),
            **({"base_url": base_url} if base_url else {}),
            **({"model_name": model_name} if model_name else {}),
        }


class OpenAIProvider(LLMProviderStrategy):
    """OpenAI provider using ChatOpenAI."""

    @property
    def provider_name(self) -> str:
        return "openai"

    def get_client(self, config: Dict[str, Any]) -> ChatOpenAI:
        return ChatOpenAI(
            model=config.get("model_name", "gpt-4o"),
            temperature=config.get("temperature", 0.7),
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
        )

    async def ainvoke(self, messages: List[BaseMessage]) -> BaseMessage:
        client = self.get_client(self._config)
        return await client.ainvoke(messages)

    def get_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return config  # Direct passthrough


class AnthropicProvider(LLMProviderStrategy):
    """Anthropic provider using ChatAnthropic."""

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def get_client(self, config: Dict[str, Any]) -> ChatAnthropic:
        return ChatAnthropic(
            model=config.get("model_name", "claude-3-5-sonnet-20241022"),
            temperature=config.get("temperature", 0.7),
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
        )

    async def ainvoke(self, messages: List[BaseMessage]) -> BaseMessage:
        client = self.get_client(self._config)
        return await client.ainvoke(messages)

    def get_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return config  # Direct passthrough


class MiniMaxProvider(LLMProviderStrategy):
    """MiniMax provider — OpenAI-compatible API at https://api.minimax.io/v1."""

    DEFAULT_BASE_URL = "https://api.minimax.io/v1"
    DEFAULT_MODEL = "MiniMax-M2.7"

    @property
    def provider_name(self) -> str:
        return "minimax"

    def get_client(self, config: Dict[str, Any]) -> ChatOpenAI:
        return ChatOpenAI(
            model=config.get("model_name", self.DEFAULT_MODEL),
            temperature=config.get("temperature", 0.7),
            api_key=config.get("api_key"),
            base_url=config.get("base_url", self.DEFAULT_BASE_URL),
        )

    async def ainvoke(self, messages: List[BaseMessage]) -> BaseMessage:
        client = self.get_client(self._config)
        return await client.ainvoke(messages)

    def get_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return {
            **config,
            "base_url": config.get("base_url") or self.DEFAULT_BASE_URL,
            "model_name": config.get("model_name") or self.DEFAULT_MODEL,
        }


# ---------------------------------------------------------------------------
# Provider Registry — the only place you need to edit to add a new provider
# ---------------------------------------------------------------------------
PROVIDER_REGISTRY: Dict[str, type[LLMProviderStrategy]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "minimax": MiniMaxProvider,
}

# Map of environment variable prefixes → provider key
# e.g. MINIMAX_API_KEY + MINIMAX_BASE_URL → "minimax"
PROVIDER_ENV_PREFIXES: Dict[str, str] = {
    "OPENAI": "openai",
    "ANTHROPIC": "anthropic",
    "MINIMAX": "minimax",
}


def get_provider(provider_key: str, global_config: Optional[Dict[str, str]] = None) -> LLMProviderStrategy:
    """
    Factory: resolve a provider key to a provider instance.

    provider_key: "openai" | "anthropic" | "minimax" | ...
    global_config: dict of env vars (e.g. {"OPENAI_API_KEY": "...", "MINIMAX_API_KEY": "..."})
    """
    provider_class = PROVIDER_REGISTRY.get(provider_key.lower())
    if not provider_class:
        available = ", ".join(PROVIDER_REGISTRY.keys())
        raise ValueError(f"Unknown provider '{provider_key}'. Available: {available}")

    instance = provider_class()
    if global_config:
        instance._resolve_from_env(global_config, provider_key)
    return instance


def load_provider_from_agent(
    agent_model_name: str, agent_provider: str, agent_config: Dict[str, Any], env_vars: Optional[Dict[str, str]] = None
) -> LLMProviderStrategy:
    """
    Load the correct provider for an agent, merging agent config + env vars.
    Env vars take precedence over stored agent config.
    """
    # Build merged config — env vars override agent DB config
    merged = {**agent_config}
    prefix = provider_key_from_name(agent_provider)

    if env_vars:
        for env_key, env_val in env_vars.items():
            if env_key.upper().startswith(f"{prefix}_") or env_key.upper() == f"{prefix}_API_KEY":
                config_key = env_key[len(prefix) + 1 :].lower()
                if config_key == "api_key":
                    merged["api_key"] = env_val
                elif config_key == "base_url":
                    merged["base_url"] = env_val

    # Use provider from agent or default to minimax
    provider_key = agent_provider or "minimax"
    instance = get_provider(provider_key)
    instance._config = merged
    return instance


def provider_key_from_name(name: str) -> str:
    """Get env prefix from provider name."""
    return PROVIDER_ENV_PREFIXES.get(name.upper(), name.lower())
