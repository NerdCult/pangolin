#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from typing import Protocol, Iterator, AsyncGenerator

from ...messages import TARecord, AgentMessage

class ApiAggregator(Protocol):
    '''
    recieves the context and tools schems from the AgentRuntime, passes to the API Client, and handles the returned ApiEvents; 
    passes deltas through as AgentMessages for responsive user experinece
    aggregates the deltas to create TARecords and passes them through for the AgentRuntime to process.
    '''
    def process_context(self, context: list[TARecord]) -> Iterator[AgentMessage]: ...


class ApiAggregatorAsync(Protocol):
    '''
    recieves the context and tools schems from the AgentRuntime, passes to the API Client, and handles the returned ApiEvents; 
    passes deltas through as AgentMessages for responsive user experinece
    aggregates the deltas to create TARecords and passes them through for the AgentRuntime to process.
    '''
    async def process_context_async(self, context: list[TARecord]) -> AsyncGenerator[AgentMessage]: ...