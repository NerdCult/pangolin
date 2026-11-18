#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import json, logging, copy, asyncio
from typing import Iterator, Protocol
from ..core.interfaces import Provider, Client, ClientAsync
from ..messages import TARecord, Part, ApiEvent, ToolCall

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

    def get_stream(self, messages, tools = None):
        LOGGER.info(f'SMOKE TEST RECEIVED {len(messages)} TARecords {len(tools) if tools else 0} tools')
        print(f'SMOKE TEST RECEIVED {len(messages)} TARecords {len(tools) if tools else 0} tools')
        if self.show_system and messages[0].role == 'system':
            LOGGER.info(f'SYSTEM:\n{messages[0].content[0].data['text']}')
            print (f'SYSTEM:\n{messages[0].content[0].data['text']}')

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


    async def get_stream_async(self, messages, tools = None):
        LOGGER.info(f'SMOKE TEST RECEIVED {len(messages)} TARecords {len(tools) if tools else 0} tools')
        print(f'SMOKE TEST RECEIVED {len(messages)} TARecords {len(tools) if tools else 0} tools')
        if self.show_system and messages[0].role == 'system':
            LOGGER.info(f'SYSTEM:\n{messages[0].content[0].data['text']}')
            print (f'SYSTEM:\n{messages[0].content[0].data['text']}')

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
        