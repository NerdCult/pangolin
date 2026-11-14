#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from typing import Protocol, runtime_checkable
from ...messages import TARecord
from ..types import ChatSummary

@runtime_checkable
class MemoryManager(Protocol):
    ''' Manages the memory for the session it is attached to. '''
    def get_context(self) -> list[TARecord]: ...
    def add_context(self, message: TARecord ): ...
    def trim_context(self): ...

@runtime_checkable
class IdTrackedMemoryManger(MemoryManager, Protocol):
    ''' Manages memory with support for Chat IDs for read/write from a persistence based storage provider'''
    def set_id(self, id: str, max_records_to_reload: int): ...
    ''' set the Chat ID and reload memory from persistence. reloaded memory can be trimmed longer by the AgentRuntime, this is just a starting point. '''
    def get_ids(self) -> list[ChatSummary]: ...
    ''' return a list of ChatSumary { id: str, summary = { 'last_used': date, 'name': str | None,  'description': str | None}'''
    def update_chat_summary(self, name: str, description: str): ...
    ''' update the name and description for the current chat history. could be called through a session aware tool.'''
    def delete_chat(self): ...
    ''' delete the current selected chat history. could be called through a session aware tool.'''
