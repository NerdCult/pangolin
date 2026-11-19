#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from typing import Protocol, Iterator, AsyncGenerator
import logging, asyncio, threading
from ..core.interfaces import AgentRuntime, AgentRuntimeAsync, AgentRuntimeToQueue, MemoryManager,SkillManager, Toolbox, ToolboxAdvanced, ApiAggregator, ApiAggregatorAsync, Guardrail, GuardrailAsync
from ..core.exceptions import PangolinTypeError, PangolinValueError, PangolinGuardRailDenial
from ..core.types import GuardrailEvent
from ..messages import TARecord, Part, AgentMessage, ToolCall
from ..utils import count_tokens
from ..memory_managers import SimpleMemoryManager

LOGGER = logging.getLogger(__name__)


class DefaultAgentRuntime(AgentRuntime, AgentRuntimeToQueue, AgentRuntimeAsync, Protocol):
    '''
    default implementation of AgentRuntime.
    the only required parameter is aggregator: ApiAggregator
    memory_manager will default to SimpleMemoryManager which only tracks the current session in memory.
    '''
    def __init__(self,
                 aggregator: ApiAggregator, 
                 system_prompt: str = '',
                 memory_manager: MemoryManager | None = None,
                 skill_manager: SkillManager | None = None, 
                 toolbox: Toolbox | None = None,
                 guardrail: Guardrail | GuardrailAsync | None = None,
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

        if not isinstance(aggregator, ApiAggregator):
            raise PangolinTypeError('aggregator parameter does not implement ApiAggregator')
        if memory_manager and not isinstance(memory_manager, MemoryManager):
            raise PangolinTypeError('memory_manager parameter does not implement MemoryManger')
        if skill_manager and not isinstance(skill_manager, SkillManager):
            raise PangolinTypeError('skill_manager parameter does not implement SkillManager')
        if toolbox and not isinstance(toolbox, Toolbox):
            raise PangolinTypeError('toolbox parameter does not implement Toolbox')
        if guardrail and (not isinstance(guardrail, Guardrail) and not isinstance(guardrail, GuardrailAsync)):
            raise PangolinTypeError('guardrail parameter does not implement Guardrail or GuardrailAsync')
        
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
        self.guardrail = guardrail
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

    def _handle_agent_message(self, agent_message: AgentMessage, tool_calls: list, blocked_tool_call_ids: list, reason: list):
                # if the ApiAggregator yields a message event add it to the context and check it for tool_calls
                if agent_message.behavior == 'message':
                    LOGGER.info(f'assistant message recieved: {agent_message.message}')
                    if agent_message.message and self.guardrail:
                        ger = self.guardrail.handle_guardrail_event(
                            GuardrailEvent(
                                event_type='assistant_output',
                                ta_record=agent_message.message
                            )
                        )

                        if ger.event_type == 'deny':
                            raise PangolinGuardRailDenial(f'AgentMessage triggered a Guardrail denial {ger.reason}')
                        if ger.event_type == 'modify':
                            agent_message.message = ger.ta_record
                            reason['reason'] = ger.reason
                            for rtci in ger.rejected_tool_call_ids or []:
                                blocked_tool_call_ids.append(rtci)

                    if agent_message.message.tool_calls:
                        for tc in agent_message.message.tool_calls:
                            tool_calls.append(tc) 
                    
                    self._add_context(agent_message.message)

    async def _handle_agent_message_async(self, agent_message: AgentMessage, tool_calls: list, blocked_tool_call_ids: list, reason: list):
                # if the ApiAggregator yields a message event add it to the context and check it for tool_calls
                if agent_message.behavior == 'message':
                    LOGGER.info(f'assistant message recieved: {agent_message.message}')
                    if agent_message.message and self.guardrail:
                        ger = await self.guardrail.handle_guardrail_event_async(
                            GuardrailEvent(
                                event_type='assistant_output',
                                ta_record=agent_message.message
                            )
                        )

                        if ger.event_type == 'deny':
                            raise PangolinGuardRailDenial(f'AgentMessage triggered a Guardrail denial {ger.reason}')
                        if ger.event_type == 'modify':
                            agent_message.message = ger.ta_record
                            reason['reason'] = ger.reason
                            for rtci in ger.rejected_tool_call_ids or []:
                                blocked_tool_call_ids.append(rtci)

                    if agent_message.message.tool_calls:
                        for tc in agent_message.message.tool_calls:
                            tool_calls.append(tc) 
                    
                    self._add_context(agent_message.message)

    def _handle_tool_calls(self, tool_calls: list[ToolCall], blocked_tool_call_ids: list, reason: str) -> None:
        LOGGER.info('making tool calls')
        calls_to_run = []
        for tc in tool_calls:
            if tc.id in blocked_tool_call_ids:
                self._add_context(TARecord(
                    role='tool', 
                    content=[Part(type='text', data={'text': reason})],
                    tool_call_id=tc.id))
            else:
                calls_to_run.append(tc)

        for result in self.toolbox.handle_tool_calls(calls_to_run):
            tar = TARecord(role='tool', content=[Part(type='text', data={'text': result.result})], tool_call_id=result.id)
            if self.guardrail:
                ger = self.guardrail.handle_guardrail_event(
                    GuardrailEvent(
                        event_type='tool_call_result',
                        ta_record=tar
                    )
                )
                if ger.event_type == 'modify':
                    tar = ger.ta_record

            LOGGER.debug(f'TOOL CALL RESULT {tar.to_json()}')
            self._add_context(tar)
            

    def _user_message_guardrail_check(self, message: TARecord):
        if self.guardrail:
            ger = self.guardrail.handle_guardrail_event(
                GuardrailEvent(event_type='user_input',
                               ta_record=message
                               ))
            
            if ger.event_type == 'deny':
                raise PangolinGuardRailDenial(f'User Message triggered a Guardrail denial {ger.reason}')
            if ger.event_type == 'modify':
                self._add_context(ger.ta_record)
                return

        self._add_context(message)
    
    async def _user_message_guardrail_check_async(self, message: TARecord):
        if self.guardrail:
            ger = await self.guardrail.handle_guardrail_event_async(
                GuardrailEvent(event_type='user_input',
                               ta_record=message
                               ))

            if ger.event_type == 'deny':
                raise PangolinGuardRailDenial(f'User Message triggered a Guardrail denial {ger.reason}')
            if ger.event_type == 'modify':
                self._add_context(ger.ta_record)
                return

        self._add_context(message)
         
    def handle_user_message(self, message: TARecord) -> Iterator[AgentMessage]:
        ''' Main entry point to start the agentic loop. '''

        if not isinstance(message, TARecord):
            raise PangolinTypeError('message does not implement TARecord')
        LOGGER.info(f'user message recieved: {message.to_json()}')

        try:
            if self.guardrail and not isinstance(self.guardrail, Guardrail):
                raise PangolinValueError('runtime guardrail must implement the non async Guardrail to be used in    the synchorous handle_user_message() call')
            self._user_message_guardrail_check(message)

            for _ in range(self.max_rounds):
                context = self._get_context() # get the context to send to the api
                tool_calls = [] # initialzed to store tool calls 
                blocked_tool_call_ids = []
                reason = {'reason': ''}

                for agent_message in self.aggregator.process_context(context, self._tools()):
                    self._handle_agent_message(agent_message, tool_calls, blocked_tool_call_ids, reason)
                    yield agent_message

                # if the stream ends with no tool calls the loop exits
                if tool_calls and self.toolbox:
                    LOGGER.debug(f'runtime got {len(tool_calls)} tool calls')
                    self._handle_tool_calls(tool_calls, blocked_tool_call_ids, reason['reason'])
                else:
                    break
        except PangolinGuardRailDenial as grd:
            yield AgentMessage(behavior='guardrail', content=grd)
        except BaseException as e:
            yield AgentMessage(behavior='error', content=e)
    
    async def handle_user_message_async(self, message: TARecord) -> AsyncGenerator[AgentMessage]:
        ''' Main entry point to start the agentic loop. '''
        
        if not isinstance(message, TARecord):
            raise PangolinTypeError('message does not implement TARecord')
        if not isinstance(self.aggregator, ApiAggregatorAsync):
            raise PangolinTypeError('Aggregator does not implement ApiAggregatorAsync')
        
        LOGGER.info(f'user message recieved: {message.to_json()}')
        try:
            if isinstance(self.guardrail, GuardrailAsync):
                await self._user_message_guardrail_check_async(message)
            else:
                await asyncio.to_thread(self._user_message_guardrail_check, message)

            for _ in range(self.max_rounds):
                context = self._get_context() # get the context to send to the api
                tool_calls = [] # initialzed to store tool calls 
                blocked_tool_call_ids = []
                reason = {'reason': ''}

                async for agent_message in self.aggregator.process_context_async(context, self._tools()):
                    if isinstance(self.guardrail, GuardrailAsync):
                        await     self._handle_agent_message_async(agent_message, tool_calls, blocked_tool_call_ids,  reason)
                    else:
                        await asyncio.to_thread(self._handle_agent_message, agent_message, tool_calls,    blocked_tool_call_ids, reason)
                    yield agent_message
    
                # if the stream ends with no tool calls the loop exits
                if tool_calls and self.toolbox:
                    LOGGER.debug(f'runtime got {len(tool_calls)} tool calls')
                    self._handle_tool_calls(tool_calls, blocked_tool_call_ids, reason['reason'])
                else:
                    break
        except PangolinGuardRailDenial as grd:
            yield AgentMessage(behavior='guardrail', content=grd)
        except BaseException as e:
            yield AgentMessage(behavior='error', content=e)
        
    async def handle_user_message_to_queue(self, message: TARecord, 
                             queue: asyncio.Queue[AgentMessage | None], 
                             stop: threading.Event = threading.Event(),
                             done: threading.Event = threading.Event()):
        ''' To ansycio.Queue entry point to start the agentic loop. '''
        
        if not isinstance(message, TARecord):
            raise PangolinTypeError('message does not implement TARecord')
        if not isinstance(self.aggregator, ApiAggregatorAsync):
            raise PangolinTypeError('aggregator does not implement ApiAggregatorAsync')

        LOGGER.info(f'user massege recieved: {message.to_json()}')

        async def task_done():
            await queue.put(None)
            done.set()

        try:
            if isinstance(self.guardrail, GuardrailAsync):
                await self._user_message_guardrail_check_async(message)
            else:
                await asyncio.to_thread(self._user_message_guardrail_check, message)

            for _ in range(self.max_rounds):
                context = self._get_context() # get the context to send to the api
                tool_calls = [] # initialzed to store tool calls 
                blocked_tool_call_ids = []
                reason = {'reason': ''}

                async for agent_message in self.aggregator.process_context_async(context, self._tools()):
                    if isinstance(self.guardrail, GuardrailAsync):
                        await self._handle_agent_message_async(agent_message, tool_calls, blocked_tool_call_ids,  reason)
                    else:
                        await asyncio.to_thread(self._handle_agent_message, agent_message, tool_calls, blocked_tool_call_ids, reason)
                    await queue.put(agent_message)

                    if stop.is_set(): 
                        break

                # if the stream ends with no tool calls the loop exits
                if tool_calls and self.toolbox:
                    LOGGER.debug(f'runtime got {len(tool_calls)} tool calls')
                    self._handle_tool_calls(tool_calls, blocked_tool_call_ids, reason['reason'])
                else:
                    await task_done()
                    break

                if stop.is_set(): 
                    await task_done()
                    break
        except PangolinGuardRailDenial as grd:
            await queue.put(AgentMessage(behavior='guardrail', content=grd))
        except BaseException as e:
            await queue.put(AgentMessage(behavior='error', content=e))