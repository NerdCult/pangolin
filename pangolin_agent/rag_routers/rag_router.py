#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from typing import Protocol
import asyncio
from ..core.interfaces import RAGComponent
from ..core.exceptions import PangolinTypeError
from ..utils import ensure_async

class RAGRouter(RAGComponent,  Protocol):
    ''' helper class used to tie into the RAG hook in PangolinRuntime and manages routing to a RAG SkillManger implementation and/or a RAG Toolbox implementation'''

    def __init__(self, skill_manager: RAGComponent | None = None, toolbox: RAGComponent | None = None):
        if skill_manager and not isinstance(skill_manager, RAGComponent):
            raise PangolinTypeError('skill_manager must implement RAGComponentc')
        if toolbox and not isinstance(toolbox, RAGComponent):
            raise PangolinTypeError('toolbox must implement RAGComponent')

        self.skill_manager = skill_manager
        self.toolbox = toolbox


    async def retrieve_with_chat_history(self, chat_history):
            if self.skill_manager and self.toolbox:
                await asyncio.gather(
                    ensure_async(self.skill_manager.retrieve_with_chat_history(chat_history)),
                    ensure_async(self.toolbox.retrieve_with_chat_history(chat_history))
                )
            elif self.skill_manager:
                 await ensure_async(self.skill_manager.retrieve_with_chat_history, chat_history)
            elif self.toolbox:
                 await ensure_async(self.toolbox.retrieve_with_chat_history, chat_history)
            return
