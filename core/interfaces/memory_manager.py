#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from typing import Protocol, runtime_checkable
from ...messages import TARecord

@runtime_checkable
class MemoryManager(Protocol):
    ''' Manages the memory for the session it is attached to. '''
    def get_context(self) -> list[TARecord]: ...
    def add_context(self, message: TARecord ): ...
    def trim_context(self): ...
    ''' can be called by AgentRuntime if system prompt + skills + tools + chat history exceeds the alloted max_tokens size. Memory Managers with persistence can keep long term storage and a short term set that is returned by get_context trim that with this method'''

@runtime_checkable
class IdTrackedMemoryManger(MemoryManager, Protocol):
    ''' Manages memory with support for Chat IDs for read/write from a persistence based storage provider'''
    def update_chat_summary(self, name: str, description: str): ...
    ''' update the name and description for the current chat history. could be called through a session aware tool or the external applicaition.'''
