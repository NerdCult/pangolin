#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import logging
from typing import Protocol
from pathlib import Path
from ..core.interfaces import SkillManager, RAGComponent, RAGComponentAsync

LOGGER = logging.getLogger(__name__)

class RAGSkillManager(SkillManager, RAGComponent, RAGComponentAsync, Protocol):
    '''
    Implements SkillManger and RAGComponent/RAGComponentAsync

    '''
    def __init__(self):
        self.skills_this_turn: str = ''

    # load the available skills
    def reload_skills(self):
        LOGGER.debug('RAGSkillManger does not utilise reload_skills')

    # provide the concatonation of the found skills
    def skills(self) -> str:
        return self.skills_this_turn

    def retrieve_with_chat_history(self, chat_history):
        self.skills_this_turn = chat_history[-1].content[0].data['text']

    async def retrieve_with_chat_history_async(self, chat_history):
        self.skills_this_turn = chat_history[-1].content[0].data['text']
