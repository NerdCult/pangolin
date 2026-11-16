#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import json, logging, copy
from typing import Iterator
from ..core.interfaces import Provider, Client
from ..messages import TARecord, Part, ApiEvent, ToolCall

LOGGER = logging.getLogger(__name__)

DEFAULT_SMOKE_TEST_EVENTS: list[ApiEvent] =[
    ApiEvent(event_type='thinking', content='i am thi'),
    ApiEvent(event_type='thinking', content='nking'),
    ApiEvent(event_type='replying', content='i am r'),
    ApiEvent(event_type='replying', content='eplying'),
    ApiEvent(event_type='done', content='done'),
    ApiEvent(event_type='thinking', content='i am thi'),
    ApiEvent(event_type='thinking', content='nking'),
    ApiEvent(event_type='replying', content='i am r'),
    ApiEvent(event_type='replying', content='eplying'), 
    ApiEvent(event_type='tool_call', tool_calls=[ToolCall(id='first tool call', name='get_utc_time', args={})]),
    ApiEvent(event_type='done', content='done'),
    ApiEvent(event_type='replying', content='i got '),    
    ApiEvent(event_type='replying', content='the ti'),
    ApiEvent(event_type='replying', content='me'),
    ApiEvent(event_type='done', content='done')
]

class SmokeTestClient(Client):
    def __init__(self, responses: list[ApiEvent] = DEFAULT_SMOKE_TEST_EVENTS):
        self.responses = copy.deepcopy(responses)

    def get_stream(self, messages, tools = None):
        LOGGER.info(f'SMOKE TEST RECEIVED {len(messages)} TARecords')

        while True:
            next_event = self.responses.pop(0)

            yield next_event

            if next_event.event_type == 'done':
                break
        