#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from typing import Protocol, Iterator, AsyncGenerator, runtime_checkable

from ...messages import TARecord, AgentMessage

@runtime_checkable
class ApiAggregator(Protocol):
    '''
    recieves the context and tools schemas from the AgentRuntime, passes to the API Client, and handles the returned ApiEvents; 
    passes deltas through as AgentMessages for responsive user experience
    aggregates the deltas to create TARecords and passes them through for the AgentRuntime to process.
    '''
    def process_context(self, context: list[TARecord], tools: list[dict]) -> Iterator[AgentMessage]: ...

@runtime_checkable
class ApiAggregatorAsync(Protocol):
    '''
    Async implementation of ApiAggregator.
    '''
    async def process_context_async(self, context: list[TARecord], tools: list[dict]) -> AsyncGenerator[AgentMessage]: ...