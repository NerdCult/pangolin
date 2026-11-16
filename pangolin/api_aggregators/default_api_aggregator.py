#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import logging
from ..messages import TARecord, Part, AgentMessage, ToolCall, assistant_record
from ..core.interfaces import Client, ApiAggregator

LOGGER = logging.getLogger(__name__)

class DefaultApiAggregator(ApiAggregator):
    def __init__(self, client: Client):
        LOGGER.info(f'__init__: {client}')
        self.client: Client = client

    def process_context(self, context: list[TARecord], tools: list[dict]):
            LOGGER.info(f'processing context with {len(context)} records and {len(tools) if tools else '0'} tools')
            content = ""

            tool_calls = None

            # Get the ApiEvent stream from the api_providers.Cliet implementation.
            # ApiEvents can be partials of the LLM out put they are yielded as they arrive for responsive UI
            for event in self.client.get_stream(context, tools):
                if event.event_type == "thinking":
                    yield AgentMessage(behavior= 'thinking', content= event.content)

                # the LLM responses are consolidated as they come in so a complete TARecord content can be output after the stream ends
                if event.event_type == "replying":
                    yield AgentMessage(behavior='replying', content= event.content)
                    content = content + event.content

                # Tool calls are assembled in the api_provider.Client implementation and can be API specific
                if event.event_type == "tool_call":
                    tool_calls = event.tool_calls
                    yield AgentMessage(behavior='tool_calls', content=tool_calls)

                if event.event_type  == "done":
                    yield AgentMessage( behavior= 'done', content= event.content)

            yield AgentMessage(behavior='message', message=TARecord(role='assistant', content=[Part(type='text', data={'text': content})] if content else None, tool_calls=tool_calls))

                