#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from typing import Protocol, Iterator, AsyncGenerator, runtime_checkable

from ...messages import ChatRecord, AgentMessage

@runtime_checkable
class ResponseComposer(Protocol):
    '''
    recieves the context and tools schemas from the AgentRuntime, passes to the API Client, and handles the returned ApiEvents; 
    passes deltas through as AgentMessages for responsive user experience
    aggregates the deltas to create TARecords and passes them through for the AgentRuntime to process.
    '''
    def process_context(self, records: list[ChatRecord], tools: list[dict]) -> Iterator[AgentMessage]: ...

@runtime_checkable
class ResponseComposerAsync(Protocol):
    '''
    Async implementation of ApiAggregator.
    '''
    async def process_context_async(self, records: list[ChatRecord], tools: list[dict]) -> AsyncGenerator[AgentMessage]: ...