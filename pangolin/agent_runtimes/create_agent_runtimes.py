#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from ..utils import create_openai_client, create_anthropic_client, create_gemini_client, create_smoke_test_client
from ..core.interfaces import MemoryManager, Toolbox, SkillManager, Guardrail
from ..memory_managers import SimpleMemoryManager
from ..response_composers import DefaultResponseComposer
from . import DefaultAgentRuntime
from ..messages import ApiEvent

def openai_agent_runtime(url: str, 
                         model: str, 
                         key: str = 'no key', 
                         system_prompt: str = '', 
                         memory_manager: MemoryManager | None = None,
                         skill_manager: SkillManager | None = None,
                         toolbox: Toolbox | None = None,
                         guardrail: Guardrail | None = None,
                         max_tokens: int = 32_000,
                         max_rounds: int = 10,
                         **api_kwargs):
    ''' helper function to simplify creating an AgentRuntime session with an OpenAI api. api_kwargs are passed into completions.create() model, messages, tools, and stream are set internal and should not be added to api_kwargs. '''
    return DefaultAgentRuntime(
        aggregator= DefaultResponseComposer(client=create_openai_client(url=url, model=model, key=key, **api_kwargs)),
        system_prompt=system_prompt,
        memory_manager=memory_manager or SimpleMemoryManager(),
        skill_manager=skill_manager,
        toolbox=toolbox,
        guardrail=guardrail,
        max_tokens=max_tokens,
        max_rounds=max_rounds
    )


def anthropic_agent_runtime(url: str, 
                         model: str, 
                         key: str = 'no key', 
                         system_prompt: str = '', 
                         memory_manager: MemoryManager | None = None,
                         skill_manager: SkillManager | None = None,
                         toolbox: Toolbox | None = None,
                         guardrail: Guardrail | None = None, 
                         max_tokens: int = 32_000,
                         max_rounds: int = 10,
                         **api_kwargs):
    ''' helper function to simplify creating an AgentRuntime session with the Anthropic api. api_kwargs are passed into messages.stream() model, messages, tools, system, and max_tokens are set internal and should not be added to api_kwargs. '''
    return DefaultAgentRuntime(
        aggregator= DefaultResponseComposer(client=create_anthropic_client(url=url, model=model, key=key, **api_kwargs)),
        system_prompt=system_prompt,
        memory_manager=memory_manager or SimpleMemoryManager(),
        skill_manager=skill_manager,
        toolbox=toolbox,
        guardrail=guardrail,
        max_tokens=max_tokens,
        max_rounds=max_rounds
    )


def gemini_agent_runtime( 
                         model: str, 
                         key: str = 'no key', 
                         system_prompt: str = '', 
                         memory_manager: MemoryManager | None = None,
                         skill_manager: SkillManager | None = None,
                         toolbox: Toolbox | None = None,
                         guardrail: Guardrail | None = None,
                         max_tokens: int = 32_000,
                         max_rounds: int = 10,
                         **api_kwargs):
    ''' helper function to simplify creating an AgentRuntime session with the Gemini api. api_kwargs are passed into types.GenerateContentConfig() system_instructions and tools are set internal and should not be added to api_kwargs. thinking_config defaults to include_thoughts=true but can be set in api_kwargs'''
    return DefaultAgentRuntime(
        aggregator= DefaultResponseComposer(client=create_gemini_client( model=model, key=key, **api_kwargs)),
        system_prompt=system_prompt,
        memory_manager=memory_manager or SimpleMemoryManager(),
        skill_manager=skill_manager,
        toolbox=toolbox,
        guardrail=guardrail,
        max_tokens=max_tokens,
        max_rounds=max_rounds
    )


def smoke_test_runtime( 
                         system_prompt: str = '', 
                         memory_manager: MemoryManager | None = None,
                         skill_manager: SkillManager | None = None,
                         toolbox: Toolbox | None = None,
                         guardrail: Guardrail | None = None,
                         max_tokens: int = 32_000,
                         max_rounds: int = 10,
                         responses: list[ApiEvent] | None = None,
                         show_system: bool = False,
                         list_tools: bool = False,
                         **api_kwargs):
    return DefaultAgentRuntime(
            aggregator= DefaultResponseComposer(client=create_smoke_test_client(responses, show_system, list_tools)),
            system_prompt=system_prompt,
            memory_manager=memory_manager or SimpleMemoryManager(),
            skill_manager=skill_manager,
            toolbox=toolbox,
            guardrail=guardrail,
            max_tokens=max_tokens,
            max_rounds=max_rounds
        )