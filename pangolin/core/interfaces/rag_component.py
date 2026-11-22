#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from typing import Protocol, runtime_checkable
from ...messages import ChatRecord

@runtime_checkable
class RAGComponent(Protocol):
    ''' Implements a hook to recieve the chat history from the runtime prior to starting the loop, so that their state (eg skills() or schemas() can be updated specific to the current api call'''
    def retrieve_with_chat_history(self, chat_history: list[ChatRecord]):...

@runtime_checkable
class RAGComponentAsync(Protocol):
    async def retrieve_with_chat_history_async(self, chat_history: list[ChatRecord]):...