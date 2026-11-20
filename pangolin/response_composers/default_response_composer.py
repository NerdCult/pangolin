#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import logging
from typing import Protocol
from ..messages import ChatRecord, AgentMessage, ApiEvent, Part
from ..core.interfaces import Client, ClientAsync, ResponseComposer, ResponseComposerAsync
from ..core.exceptions import PangolinTypeError, PangolinValueError

LOGGER = logging.getLogger(__name__)

class DefaultResponseComposer(ResponseComposer, ResponseComposerAsync, Protocol):
    def __init__(self, client: Client | ClientAsync):
        LOGGER.debug(f'__init__: {client}')
        if not isinstance(client, Client) and not isinstance(client, ClientAsync):
            raise PangolinTypeError('ApiAggregator client param must implement either Client or ClientAsync')
        self.client: Client | ClientAsync = client

    def _handle_api_event(self, event: ApiEvent, tool_calls: list, reply_accumulator: list[str]) -> AgentMessage:
        if event.event_type == "thinking":
            return AgentMessage(behavior= 'thinking', content= event.content)

        # the LLM responses are consolidated as they come in so a complete TARecord content can be output after the stream ends
        if event.event_type == "replying":
            reply_accumulator[0] += event.content
            return AgentMessage(behavior='replying', content= event.content)

        # Tool calls are assembled in the api_provider.Client implementation and can be API specific
        if event.event_type == "tool_call":
            for tc in event.tool_calls:
                tool_calls.append(tc)
            return AgentMessage(behavior='tool_calls', content=f'{tool_calls}')

        if event.event_type  == "done":
            return AgentMessage( behavior= 'done', content= event.content)

    def process_context(self, context: list[ChatRecord], tools: list[dict]):
        LOGGER.info(f'processing context with {len(context)} records and {len(tools) if tools else '0'}tools')
        content = [""]
        tool_calls = []

        # Get the ApiEvent stream from the api_providers.Client implementation.
        # ApiEvents can be partials of the LLM out put they are yielded as they arrive for responsive UI
        for event in self.client.get_stream(context, tools):
            yield self._handle_api_event(event, tool_calls, content)

        yield AgentMessage(behavior='message', message=ChatRecord(role='assistant', content=[Part(type='text', data={'text': content[0]})] if len(content[0]) > 0 else None, tool_calls=tool_calls))


    async def process_context_async(self, context: list[ChatRecord], tools: list[dict]):
        LOGGER.info(f'processing context with {len(context)} records and {len(tools) if tools else '0'}tools')
        if not isinstance(self.client, ClientAsync):
             raise PangolinValueError('Client does not implement ClientAsync')
        content = ['']
        tool_calls = []

        # Get the ApiEvent stream from the api_providers.Client implementation.
        # ApiEvents can be partials of the LLM out put they are yielded as they arrive for responsive UI
        async for event in self.client.get_stream_async(context, tools):
            yield self._handle_api_event(event, tool_calls, content)

        yield AgentMessage(behavior='message', message=ChatRecord(role='assistant', content=[Part(type='text', data={'text': content[0]})] if len(content[0]) > 0 else None, tool_calls=tool_calls))