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
        '''
        aggregator: initilialized with an api_provider.Client instance.
        system_prompt: system prompt that will be injected at the start of each turn, appended with any skills provided by the skill manager
        memory_manager:  maintains the chat history for the session. If None the SimpleMemoryManager will be used, which only  stores the current session history in memory with old messages trimmed to keep system prompt, skills, chat history, and tools list under max_token size
        skill_manager: provides skills to the session
        toolbox: provides the available tools and executes them
        max_tokens: sets the ceiling for the max context sent to the model (system prompt, skills, chat history, and tools list)
        max_rounds: int = 10 sets the maxiumum rounds the agent can make for a single user message (one round can have multiple tool calls)
        '''
        
        LOGGER.info(f'__init__: \n{aggregator}\n{system_prompt}\n{memory_manager}\n{skill_manager}\n{toolbox}\n{max_tokens}\n{max_rounds} ')

        self.aggregator: ApiAggregator = aggregator
        self.system_prompt: str = system_prompt
        self.memory_manager = memory_manager or SimpleMemoryManager()
        self.skill_manager: SkillManager = skill_manager 
        self.toolbox: Toolbox = toolbox
        if self.toolbox:
            LOGGER.debug('toolbox found')
            # Advanced toolbox can enable 'session aware tools' giving them access to talk with the skills manager and memory manager but only if the session is provided
            if isinstance(self.toolbox, ToolboxAdvanced):
                LOGGER.debug('toolbox is ToolboxAdvanced')
                self.toolbox.set_session(self)
            # Initaliaze the toolbox
            self.toolbox.load()
            LOGGER.info('toolbox loaded')
        self.max_tokens = max_tokens
        self.max_rounds = max_rounds

    def _add_context(self, message):
        '''
        adds a TARecord to the Memory Manger
        '''
        self.memory_manager.add_context(message)
        while True:
            if count_tokens(self._get_context(), self._tools()) > self.max_tokens:
                LOGGER.debug('trimming context')
                self.memory_manager.trim_context()
                continue
            break
        
    def _get_context(self):
        '''
        Assembles the current record set, without the tools list, as a list[TARecord] 
        '''
        LOGGER.debug('_get_context')
        system = f'{self.system_prompt}\n{self.skill_manager.skills() if self.skill_manager else ''}'
        system_prompt_message = TARecord(role='system', content=[Part(type='text', data={'text':system})])
        return [system_prompt_message] + self.memory_manager.get_context()

    def _tools(self) -> str | None:
        ''' Get the list of tool schemas '''
        return self.toolbox.schemas() if self.toolbox else None

    def handle_user_message(self, message: TARecord) -> Iterator[AgentMessage]:
        ''' Main entry point to start the agentic loop. '''

        LOGGER.info(f'user massage recieved: {message.to_json()}')

        self._add_context(message)
        for _ in range(self.max_rounds):
            context = self._get_context() # get the context to send to the api
            tool_calls = None # initialzed to store tool calls 

            for agent_message in self.aggregator.process_context(context, self._tools()):
                # if the ApiAggregator yields a message event add it to the context and check it for tool_calls
                if agent_message.behavior == 'message':
                    LOGGER.info(f'assistant message recieved: {agent_message.message}')
                    self._add_context(agent_message.message)
                    tool_calls = agent_message.message.tool_calls
                # yield the AgentMessage to be processed for UI
                yield agent_message

            # if the stream ends with no tool calls the loop exits
            if not tool_calls:
                LOGGER.debug('no tool calls made')
                break

            # Check for a toolbox and handle tool calls. Should be no reason for tool calls to be made without a toolbox to provide available tools.
            if self.toolbox:
                LOGGER.info('making tool calls')
                for result in self.toolbox.handle_tool_calls(tool_calls):
                    tar = TARecord(role='tool', content=[Part(type='text', data={'text': result.result})], tool_call_id=result.id)
                    LOGGER.debug(f'TOOL CALL RESULT {tar.to_json()}')
                    self._add_context(tar)
