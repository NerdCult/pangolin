#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from ..api_providers import AnthropicProvider, GeminiProvider, OpenAIProvider


def create_openai_client(url: str, model: str, key: str, **api_kwargs):
    ''' helper function to make an OpenAIClient'''
    return OpenAIProvider(url, key).make_client(model, **api_kwargs)


def create_anthropic_client(url: str, model: str, key: str, **api_kwargs):
    '''helper function to make an AnthropicClient'''
    return AnthropicProvider(url, key).make_client(model, **api_kwargs)

def create_gemini_client(model: str, key: str, **api_kwargs):
    '''helper function to make a GeminiClient'''
    return GeminiProvider(key).make_client(model, **api_kwargs)