#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from ..api_providers import AnthropicProvider, GeminiProvider, OpenAIProvider


def create_openai_client(url: str, model: str, key: str):
    return OpenAIProvider(url, key).make_client(model)


def create_anthropic_client(url: str, model: str, key: str):
    return AnthropicProvider(url, key).make_client(model)

def create_gemini_client(model: str, key: str):
    return GeminiProvider(key).make_client(model)