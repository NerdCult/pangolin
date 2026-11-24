#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import logging
from ..core.interfaces.memory_manager import MemoryManager
from ..core.exceptions import PangolinError
from ..messages import ChatRecord, user_record

LOGGER = logging.getLogger(__name__)

class SimpleMemoryManager(MemoryManager):
    '''
    stores a single session history in memory, no persistence once the session is closed.
    '''
    def __init__(self):
        LOGGER.info('__init__')
        self.memory: list = []

    def get_history(self) -> list[ChatRecord]:
        return self.memory

    def add_record(self, record: ChatRecord):
        self.memory.append(record)
        LOGGER.debug(f'message added {record}')

    # handle requests from AgentRuntime to trim context
    def trim_history(self):
        LOGGER.debug('trimming context')
        dropped_tool_call_ids: set[str] = set() #accumulate dropped tool calls so the paired tool call results can be cleared

        def pop_front():
            popped = self.memory.pop(0)
            if popped.tool_calls:
                dropped_tool_call_ids.update(tc.id for tc in popped.tool_calls)

        # pop the oldest record in memory
        pop_front()

        # APIs like the first chat message to be a user message
        while self.memory and self.memory[0].role != 'user':
            pop_front()

        # clear the orphaned tool call results
        if dropped_tool_call_ids:
            self.memory = [ m for m in self.memory if m.tool_call_id not in dropped_tool_call_ids]

        if not self.memory or len(self.memory) == 0:
            LOGGER.error('trimming removed the entire history')
            raise PangolinError('SimpleMemoryManager.trim_context() dropped all chat history. increase max_tokens in AgentRuntime or reduce system prompt, skills, and or available tools.')
