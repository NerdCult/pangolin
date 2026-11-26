#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from ..core.exceptions import PangolinImportError
try:
    from openai import OpenAI, AsyncOpenAI
except:
    raise PangolinImportError('using openai_provider requires the openai library, pip install pangolin-agent[openai]')
import json, logging
from typing import Iterator, Protocol
from ..core.interfaces import Provider, Client, MemoryManager, SkillManager, Toolbox, Guardrail, RAGComponent
from ..core.exceptions import PangolinTypeError
from ..response_composers import PangolinComposer
from ..agent_runtimes import PangolinRuntime
from ..memory_managers import SimpleMemoryManager
from ..messages import ChatRecord, Part, ApiEvent, Usage, ToolCall

LOGGER = logging.getLogger(__name__)

class OpenAIClient(Client, Protocol):
    def __init__(self, connection: OpenAI, model_name: str, **api_kwargs):
        '''
        connection: openai.OpenAI instance
        model_name: must be a name recognized by the API use OpenAIProvider to get a list of models
        api_kwargs: passed through to chat.completions.create() model, messages, tools, and stream set internally and should not be set in api_kwargs
        '''

        if not isinstance(connection, OpenAI):
            raise PangolinTypeError('OpenAIClient param connection must be OpenAI')

        LOGGER.info(f'__init__: {connection} {model_name}')
        self.connection = connection
        self.connection_async = AsyncOpenAI(api_key= self.connection.api_key, base_url=self.connection.base_url)
        self.model_name = model_name
        self.api_kwargs =  api_kwargs

    # convert Part to the OpenAI format
    def _part_to_openai(self, part: Part) -> dict:
        if part.type == "text":
            return {"type": "text", "text": part.data.get("text", "")}
        elif part.type == "image_url":
            return {"type": "image_url", "image_url": part.data}
        elif part.type == "audio":
            return {"type": "audio", "audio": part.data}
        return {"type": part.type, **part.data}

    # convert ChatRecord to the OpenAI format
    def _record_to_openai(self, record: ChatRecord) -> dict:
        if record.role == "tool":
            return {
                "role": "tool",
                "tool_call_id": record.tool_call_id,
                "content": record.content[0].data.get("text", "") if record.content else None,
            }
        result = {"role": record.role, "content": [self._part_to_openai(p) for p in record.content] if record.content else None}
        if record.tool_calls:
            result["tool_calls"] = [{'id': tc.id, 'type': 'function', 'function': {'name': tc.name, 'arguments': json.dumps(tc.args) if isinstance(tc.args, dict) else (tc.args or "{}")}} for tc in record.tool_calls]
        return result

    # converts a list[ChatRecord] to the OpenAI format
    def _records_to_openai(self, records: list[ChatRecord]):
        openai_messages = []
        for m in records:
            openai_messages.append(self._record_to_openai(m))
        return openai_messages

    def _process_chunk(self, chunk, calls, raw_args):
                delta = chunk.choices[0].delta
                finish_reason = chunk.choices[0].finish_reason
        
                extra = getattr(delta, "model_extra", None) or {}
                rtext = getattr(delta, "reasoning_content", None) or extra.get  ("reasoning_content") or extra.get ("reasoning")
        
                if rtext:
                    LOGGER.debug(f'thinking: {rtext}')
                    return ApiEvent(
                        event_type="thinking",
                        content=rtext
                     )
        
                if delta.content:
                    LOGGER.debug(f'replying {delta.content}')
                    return ApiEvent(
                        event_type="replying",
                        content=delta.content
                    )
        
                for call in delta.tool_calls or []:
                    idx = call.index
                    if call.id:
                        calls.setdefault(idx, ToolCall(id=call.id, name="", args={})).id = call.id
                    if call.function:
                        if call.function.name:
                            calls.setdefault(idx, ToolCall(id=call.id, name="", args={})).name = call.function.name
                        if call.function.arguments:
                            raw_args[idx] = raw_args.get(idx, "") + call.function.arguments
        
                if finish_reason:
                    LOGGER.debug('round complete')
                    return ApiEvent(event_type='done', content=finish_reason)

    def _process_tool(self, calls, raw_args):
            for idx, c in calls.items():
                s = raw_args.get(idx, "").strip()
                try:
                    c.args = json.loads(s) if s else {}
                except json.JSONDecodeError:
                    c.args = {}   # or keep raw string if you want to be permissive
            LOGGER.info(f'tool calls: {calls}')
            return ApiEvent(event_type="tool_call", tool_calls=list(calls.values()))

    async def get_stream(self, records, tools = None):
        '''
        Calls chat.completeion.create() on the async OpenAI client, yields the chunks as ApiEvents
        '''
        LOGGER.info(f'get_stream with {len(records)} records and {len(tools) if tools else '0'} tools')
        stream = await self.connection_async.chat.completions.create(
            model=self.model_name, 
            messages=self._records_to_openai(records),
            tools=tools,
            stream=True,
            stream_options={'include_usage': True},
            **self.api_kwargs)

        calls = {}
        raw_args = {}
    
        async for chunk in stream:
            if not chunk.choices:
                if hasattr(chunk, 'usage') and chunk.usage:
                    yield ApiEvent(event_type='usage', usage=Usage(
                        prompt_tokens=chunk.usage.prompt_tokens, 
                        completion_tokens=chunk.usage.completion_tokens, 
                        total_tokens=chunk.usage.total_tokens,
                        raw=dict(chunk.usage)))
                    break
            api_event = self._process_chunk(chunk, calls, raw_args)
            if api_event:
                yield api_event
            
        if calls:
            yield self._process_tool(calls, raw_args)

class OpenAIProvider(Provider):
    def __init__(self, url: str, key: str = "", timeout: int = 600):
        '''
        url: the url for the desired OpenAI compatible endpoint
        key: your api key if you have one
        timeout: sets the timeout for OpenAI()
        '''
        LOGGER.info(f'__init__: {url} ')
        LOGGER.debug(key)
        self.connection = OpenAI(base_url=url, api_key=key, timeout=timeout)
    
    def list_models(self):
        try:
            ids = [m.id for m in self.connection.models.list().data]
            return sorted(i for i in ids if "image" not in i and "imagine" not in i)
        except Exception as e:
            LOGGER.error(f'list_models error: {e}')
            return []
    
    def make_client(self, model_name: str, **api_kwargs):
        '''
        model_name: must be a model name the API recognizes
        kwargs: passed through the OpenAIClient created
        '''
        return OpenAIClient(self.connection, model_name, **api_kwargs)


def create_openai_client(url: str, model: str, key: str, **api_kwargs):
    ''' helper function to make an OpenAIClient'''
    return OpenAIProvider(url, key).make_client(model, **api_kwargs)


def openai_agent_runtime(url: str, 
                         model: str, 
                         key: str = 'no key', 
                         system_prompt: str = '', 
                         memory_manager: MemoryManager | None = None,
                         skill_manager: SkillManager | None = None,
                         toolbox: Toolbox | None = None,
                         guardrail: Guardrail | None = None,
                         rag_connection: RAGComponent | None = None,
                         max_tokens: int = 32_000,
                         max_rounds: int = 10,
                         **api_kwargs):
    ''' helper function to simplify creating an AgentRuntime session with an OpenAI api. api_kwargs are passed into completions.create() model, messages, tools, and stream are set internal and should not be added to api_kwargs. '''
    return PangolinRuntime(
        composer= PangolinComposer(client=create_openai_client(url=url, model=model, key=key, **api_kwargs)),
        system_prompt=system_prompt,
        memory_manager=memory_manager or SimpleMemoryManager(),
        skill_manager=skill_manager,
        toolbox=toolbox,
        guardrail=guardrail,
        rag_connection=rag_connection,
        max_tokens=max_tokens,
        max_rounds=max_rounds
    )
