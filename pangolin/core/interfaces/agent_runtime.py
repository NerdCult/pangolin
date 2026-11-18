#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import asyncio, threading
from typing import Protocol, Iterator, AsyncGenerator, runtime_checkable
from ...messages import TARecord, AgentMessage

@runtime_checkable
class AgentRuntime(Protocol):
    '''
    The central orchestration class and entry point for running inference.
    manages the ApiAggregator, SkillsManager, Toolbox, and Memory Manager
    routes steps between the different components.
    '''
    def handle_user_message(self, message: TARecord) -> Iterator[AgentMessage]: ...

@runtime_checkable
class AgentRuntimeAsync(Protocol):
    '''
    Adds AgentRuntime method to run agent requests asychronously.
    '''
    async def handle_user_message_async(self, message: TARecord) -> AsyncGenerator[AgentMessage]: ...

@runtime_checkable
class AgentRuntimeToQueue(Protocol):
    '''
    Adds AgentRuntime method to use an asyncio.Queue to provide the results.
    '''
    async def handle_user_message_to_queue(self, message: TARecord, 
                             queue: asyncio.Queue[AgentMessage | None], 
                             stop: threading.Event = threading.Event(),
                             done: threading.Event = threading.Event()): ...