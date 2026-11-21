#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import json, logging, copy, asyncio
from typing import Iterator, Protocol
from ..core.interfaces import  Client, ClientAsync, MemoryManager, SkillManager, Toolbox, Guardrail
from ..response_composers import PangolinComposer
from ..memory_managers import SimpleMemoryManager
from ..agent_runtimes import PangolinRuntime
from ..messages import ApiEvent, ToolCall

LOGGER = logging.getLogger(__name__)

DEFAULT_SMOKE_TEST_EVENTS: list[ApiEvent] =[
    ApiEvent(event_type='thinking', content='i am thi'),
    ApiEvent(event_type='thinking', content='nking'),
    ApiEvent(event_type='replying', content='i am r'),
    ApiEvent(event_type='replying', content='eplying'),
    ApiEvent(event_type='done', content='done'),
    # end first round
    ApiEvent(event_type='thinking', content='i am thi'),
    ApiEvent(event_type='thinking', content='nking'),
    ApiEvent(event_type='replying', content='i am r'),
    ApiEvent(event_type='replying', content='eplying'), 
    #ApiEvent(event_type='tool_call', tool_calls=[ToolCall(id='skill tool call', name='load_skill', args={'skill_name' : 'potato'})]), # use to test advanced toolbox and skill manager
    ApiEvent(event_type='tool_call', tool_calls=[ToolCall(id='time tool call', name='get_utc_time', args={})]),
    ApiEvent(event_type='done', content='done'),
    ApiEvent(event_type='replying', content='i got '),  # reply to tool result in same round
    ApiEvent(event_type='replying', content='the ti'),
    ApiEvent(event_type='replying', content='me'),
    ApiEvent(event_type='done', content='done') 
    # end second round, will yield script exahustion after this
]

class SmokeTestClient(Client, ClientAsync, Protocol):
    def __init__(self, responses: list[ApiEvent] = DEFAULT_SMOKE_TEST_EVENTS, show_system: bool = False, list_tools: bool = False):
        self.responses = copy.deepcopy(responses)
        self.show_system = show_system
        self.list_tools = list_tools

    def get_stream(self, records, tools = None):
        LOGGER.info(f'SMOKE TEST RECEIVED {len(records)} TARecords {len(tools) if tools else 0} tools')
        print(f'SMOKE TEST RECEIVED {len(records)} TARecords {len(tools) if tools else 0} tools')
        if self.show_system and records[0].role == 'system':
            LOGGER.info(f'SYSTEM:\n{records[0].content[0].data['text']}')
            print (f'SYSTEM:\n{records[0].content[0].data['text']}')

        if self.list_tools and tools:
            LOGGER.info(f'TOOLS:\n{tools}')
            print(f'TOOLS:\n{tools}')

        while True:
            if len(self.responses) ==0:
                yield ApiEvent(event_type='replying', content='script exhausted')
                yield ApiEvent(event_type='done', content='script exhausted')
                break
            next_event = self.responses.pop(0)

            yield next_event

            if next_event.event_type == 'done':
                break


    async def get_stream_async(self, records, tools = None):
        LOGGER.info(f'SMOKE TEST RECEIVED {len(records)} TARecords {len(tools) if tools else 0} tools')
        print(f'SMOKE TEST RECEIVED {len(records)} TARecords {len(tools) if tools else 0} tools')
        if self.show_system and records[0].role == 'system':
            LOGGER.info(f'SYSTEM:\n{records[0].content[0].data['text']}')
            print (f'SYSTEM:\n{records[0].content[0].data['text']}')

        if self.list_tools and tools:
            LOGGER.info(f'TOOLS:\n{tools}')
            print(f'TOOLS:\n{tools}')

        while True:
            await asyncio.sleep(1)
            if len(self.responses) ==0:
                yield ApiEvent(event_type='replying', content='script exhausted')
                yield ApiEvent(event_type='done', content='script exhausted')
                break
            next_event = self.responses.pop(0)

            yield next_event

            if next_event.event_type == 'done':
                break

def create_smoke_test_client(responses: list[ApiEvent] | None = None, show_system: bool = False, list_tools: bool = False):
    '''helper function to make a SmokeTestClient'''
    return SmokeTestClient(responses if responses else DEFAULT_SMOKE_TEST_EVENTS, show_system, list_tools)


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
    return PangolinRuntime(
            composer= PangolinComposer(client=create_smoke_test_client(responses, show_system, list_tools)),
            system_prompt=system_prompt,
            memory_manager=memory_manager or SimpleMemoryManager(),
            skill_manager=skill_manager,
            toolbox=toolbox,
            guardrail=guardrail,
            max_tokens=max_tokens,
            max_rounds=max_rounds
        )