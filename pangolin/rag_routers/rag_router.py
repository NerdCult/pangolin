#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from typing import Protocol
import asyncio
from ..core.interfaces import RAGComponent, RAGComponentAsync
from ..core.exceptions import PangolinTypeError

class RAGRouter(RAGComponent, RAGComponentAsync, Protocol):
    ''' helper class used to tie into the RAG hook in PangolinRuntime and manages routing to a RAG SkillManger implementation and/or a RAG Toolbox implementation'''

    def __init__(self, skill_manager: RAGComponent | RAGComponentAsync | None = None, toolbox: RAGComponent | RAGComponentAsync | None = None):
        if skill_manager and not isinstance(skill_manager, (RAGComponent, RAGComponentAsync)):
            raise PangolinTypeError('skill_manager must implement RAGComponent and/or RAGComponentAsync')
        if toolbox and not isinstance(toolbox, (RAGComponent, RAGComponentAsync)):
            raise PangolinTypeError('toolbox must implement RAGComponent and/or RAGComponentAsync')

        self.skill_manager = skill_manager
        self.toolbox = toolbox

    def retrieve_with_chat_history(self, chat_history):
        if self.skill_manager:
            if not isinstance(self.skill_manager, RAGComponent):
                raise PangolinTypeError('skill_manager must implement RAGComponent to use the synchronous RAGRouter call')
            else:
                self.skill_manager.retrieve_with_chat_history(chat_history)

        if self.toolbox:
            if not isinstance(self.toolbox, RAGComponent):
                raise PangolinTypeError('toolbox must implement RAGComponent to use the synchronous RAGRouter call')
            else:
                self.toolbox.retrieve_with_chat_history(chat_history)


    async def retrieve_with_chat_history_async(self, chat_history):
        if isinstance(self.skill_manager, RAGComponentAsync) and isinstance(self.toolbox, RAGComponentAsync):
            await asyncio.gather(
                self.skill_manager.retrieve_with_chat_history_async(chat_history),
                self.toolbox.retrieve_with_chat_history_async(chat_history)
            )
            return

        if self.skill_manager:
            if isinstance(self.skill_manager, RAGComponentAsync):
                await self.skill_manager.retrieve_with_chat_history_async(chat_history)
            else:
                await asyncio.to_thread(self.skill_manager.retrieve_with_chat_history, chat_history)

        if self.toolbox:
            if isinstance(self.toolbox, RAGComponentAsync):
                await self.toolbox.retrieve_with_chat_history_async(chat_history)
            else:
                await asyncio.to_thread(self.toolbox.retrieve_with_chat_history, chat_history)