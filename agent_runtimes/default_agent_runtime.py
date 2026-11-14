#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from typing import Iterator
import logging
from ..core.interfaces import AgentRuntime, MemoryManager,SkillManager, Toolbox, ToolboxAdvanced, ApiAggregator
from ..messages import TARecord, Part, AgentMessage
from ..utils import count_tokens
from ..memory_managers import SimpleMemoryManager

LOGGER = logging.getLogger(__name__)


class DefaultAgentRuntime(AgentRuntime):
    '''
    default implementation of AgentRuntime.
    the only required parameter is aggregator: ApiAggregator
    '''
    def __init__(self,
                 aggregator: ApiAggregator,
                 system_prompt: str = '',
                 memory_manager: MemoryManager | None = None, 
                 skill_manager: SkillManager | None = None, 
                 toolbox: Toolbox | None = None,
                 max_tokens: int = 32_000,
                 max_rounds: int = 10):
        
        LOGGER.info(f'__init__: \n{aggregator}\n{system_prompt}\n{memory_manager}\n{skill_manager}\n{toolbox}\n{max_tokens}\n{max_rounds} ')

        self.aggregator: ApiAggregator = aggregator
        self.system_prompt: str = system_prompt
        self.memory_manager = memory_manager or SimpleMemoryManager()
        self.skill_manager: SkillManager = skill_manager 
        self.toolbox: Toolbox = toolbox
        if self.toolbox:
            LOGGER.debug('toolbox found')
            if isinstance(self.toolbox, ToolboxAdvanced):
                LOGGER.debug('toolbox is ToolboxAdvanced')
                self.toolbox.set_session(self)
            self.toolbox.load()
            LOGGER.info('toolbox loaded')
        self.max_tokens = max_tokens
        self.max_rounds = max_rounds

    def _add_context(self, message):
        self.memory_manager.add_context(message)
        while True:
            if count_tokens(self._get_context(), self._tools()) > self.max_tokens:
                LOGGER.debug('trimming context')
                self.memory_manager.trim_context()
                continue
            break
        
    def _get_context(self):
        LOGGER.debug('_get_context')
        system = f'{self.system_prompt}\n{self.skill_manager.skills() if self.skill_manager else ''}'
        system_prompt_message = TARecord(role='system', content=[Part(type='text', data={'text':system})])
        return [system_prompt_message] + self.memory_manager.get_context()
    
    def _has_tools(self) -> bool:
        return self.toolbox is not None

    def _tools(self) -> str | None:
        if self._has_tools():
            schemas = self.toolbox.schemas()
            LOGGER.debug(f'tools {schemas}')
            return schemas
        return None

    def handle_user_message(self, message: TARecord) -> Iterator[AgentMessage]:    
        LOGGER.info(f'user massage recieved: {message.to_json()}')    
        self._add_context(message)
        tool_calls = None
        for _ in range(self.max_rounds):
            context = self._get_context()
            for agent_message in self.aggregator.process_context(context, self._tools()):
                if agent_message.behavior == 'message':
                    LOGGER.info(f'assistant message recieved: {agent_message.message}')
                    self._add_context(agent_message.message)
                    tool_calls = agent_message.message.tool_calls

                yield agent_message

            if not tool_calls:
                break

            if self._has_tools():
                LOGGER.info('making tool calls')
                for result in self.toolbox.handle_tool_calls(tool_calls):
                    self._add_context(TARecord(role='tool', content=[Part(type='text', data={'text': result.result})], tool_call_id=result.id))

                    
