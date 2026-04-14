import pytest
from agents.providers import (
    OpenAIProvider,
    AnthropicProvider,
    MiniMaxProvider,
    get_provider,
    PROVIDER_REGISTRY,
)


def test_provider_registry_has_all_providers():
    assert "openai" in PROVIDER_REGISTRY
    assert "anthropic" in PROVIDER_REGISTRY
    assert "minimax" in PROVIDER_REGISTRY


def test_get_provider_openai():
    provider = get_provider("openai")
    assert isinstance(provider, OpenAIProvider)
    assert provider.provider_name == "openai"


def test_get_provider_anthropic():
    provider = get_provider("anthropic")
    assert isinstance(provider, AnthropicProvider)
    assert provider.provider_name == "anthropic"


def test_get_provider_minimax():
    provider = get_provider("minimax")
    assert isinstance(provider, MiniMaxProvider)
    assert provider.provider_name == "minimax"


def test_get_provider_unknown():
    with pytest.raises(ValueError, match="Unknown provider 'unknown'"):
        get_provider("unknown")


def test_openai_provider_config():
    provider = OpenAIProvider()
    config = provider.get_config({
        "model_name": "gpt-4o",
        "temperature": 0.5,
        "api_key": "test-key"
    })
    assert config["model_name"] == "gpt-4o"
    assert config["temperature"] == 0.5


def test_minimax_provider_default_url():
    provider = MiniMaxProvider()
    config = provider.get_config({})
    assert config["base_url"] == "https://api.minimax.io/v1"
    assert config["model_name"] == "MiniMax-M2.7"


def test_minimax_provider_custom_override():
    provider = MiniMaxProvider()
    config = provider.get_config({
        "base_url": "https://custom.url",
        "model_name": "custom-model"
    })
    assert config["base_url"] == "https://custom.url"
    assert config["model_name"] == "custom-model"


@pytest.mark.asyncio
async def test_anthropic_provider_config():
    provider = AnthropicProvider()
    config = provider.get_config({
        "model_name": "claude-3-5-sonnet-20241022",
        "temperature": 0.7,
        "api_key": "test-key"
    })
    assert config["model_name"] == "claude-3-5-sonnet-20241022"
    assert config["temperature"] == 0.7