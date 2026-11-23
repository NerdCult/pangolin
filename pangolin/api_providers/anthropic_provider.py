#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from ..core.exceptions import PangolinImportError
try: 
    from anthropic import Anthropic, AsyncAnthropic
except:
    raise PangolinImportError('using anthropic_provider requires the anthropic library, pip install pangolin[anthropic]')
from typing import Iterator, Protocol, AsyncGenerator
import logging
from ..messages import ChatRecord, Part, ApiEvent, ToolCall
from ..core.interfaces import Client, Provider, ClientAsync, MemoryManager, Toolbox, SkillManager, Guardrail
from ..memory_managers import SimpleMemoryManager
from ..response_composers import PangolinComposer
from ..agent_runtimes import PangolinRuntime

LOGGER = logging.getLogger(__name__)

DEFAULT_MAX_TOKENS = 8192

class AnthropicClient(Client, ClientAsync, Protocol):
    def __init__(self, connection: Anthropic, model_name: str, max_tokens: int = DEFAULT_MAX_TOKENS, **api_kwargs):
        '''
        connection: instance of anthropic.Anthropic
        model_name: must match a known name to the api (use AnthropicProvider to get a list of models)
        max_tokens: controls the api response size. (unlike runtime max_tokens that control size sent to the api)
        api_kwargs: sent to messages.stream(). model, max_tokens, message, system, and tools set internally and should not be set in api_kwargs
        '''
        LOGGER.info(f'__init__: {connection} {model_name} {max_tokens}')
        self.connection = connection
        self.connection_async = AsyncAnthropic(base_url=self.connection.base_url, api_key=self.connection.api_key)
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.api_kwargs = api_kwargs
        self.api_kwargs["model"] = self.model_name
        self.api_kwargs["max_tokens"] = self.max_tokens

    # convert Part to the format the Anthropic API expects
    def _part_to_anthropic(self, part: Part) -> dict:
        if part.type == "text":
            return {"type": "text", "text": part.data.get("text", "")}
        if part.type == "image":
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": part.data.get("media_type"),
                    "data": part.data.get("data", ""),
                },
            }
        return {"type": part.type, **part.data}

    # converts the ChatRecord to the format expected by the Anthropic API
    def _record_to_anthropic(self, record: ChatRecord) -> dict | None:
        if record.role == "system":
            return None

        if record.role == "assistant":
            content = []
            for part in record.content or []:
                if part.type == "text" and not part.data.get("text"):
                    continue
                content.append(self._part_to_anthropic(part))
            for call in record.tool_calls or []:
                content.append({
                    "type": "tool_use",
                    "id": call.id,
                    "name": call.name,
                    "input": call.args or {},
                })
            if not content:
                return None
            return {"role": "assistant", "content": content}

        if record.role == "tool":
            text = ""
            if record.content:
                text = record.content[0].data.get("text", "")
            return {
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": record.tool_call_id,
                    "content": text,
                }],
            }

        return {
            "role": record.role,
            "content": [self._part_to_anthropic(p) for p in (record.content or [])],
        }

    # converts a list[ChatRecord] to the format the Anthropic API format expects
    def _records_to_anthropic(self, records: list[ChatRecord]) -> tuple[str | None, list[dict]]:
        system_parts: list[str] = []
        wire: list[dict] = []
        seen_tool_use_ids: set[str] = set()

        for record in records:
            # Anthropic takes the system prompt as a separate parameter
            if record.role == "system":
                for part in record.content or []:
                    text = part.data.get("text", "") if part.type == "text" else ""
                    if text.strip():
                        system_parts.append(text)
                continue

            converted = self._record_to_anthropic(record)
            if converted is None:
                continue

            # Anthropic requires the conversation to start with a user turn.
            # Trimming can leave an assistant message first, so skip it.
            if not wire and converted["role"] != "user":
                continue

            content = []
            for block in converted["content"]:
                block_type = block.get("type")

                if block_type == "text":
                    text = block.get("text", "")
                    if converted["role"] == "assistant":
                        text = text.rstrip()  # trailing whitespace is rejected on the final assistant turn
                    if not text.strip():
                        continue  # empty or whitespace-only text is rejected
                    block = {**block, "text": text}

                elif block_type == "tool_use":
                    seen_tool_use_ids.add(block["id"])

                elif block_type == "tool_result":
                    # Its tool_use was trimmed or skipped, so the result is orphaned and would be rejected
                    if block.get("tool_use_id") not in seen_tool_use_ids:
                        continue

                content.append(block)

            if not content:
                continue

            # Messages must alternate user/assistant. Merge back-to-back messages from
            # the same role (consecutive tool results, or messages left adjacent after
            # an empty one was dropped).
            if wire and wire[-1]["role"] == converted["role"]:
                wire[-1]["content"].extend(content)
            else:
                wire.append({"role": converted["role"], "content": content})

        system = "\n\n".join(system_parts) if system_parts else None
        return system, wire

    # converts OpenAI tools schemas to the format Anthropic API expects
    def _to_anthropic_tools(self, tools: list[dict] | None) -> list[dict] | None:
        if not tools:
            return None
        converted = []
        for tool in tools:
            fn = tool.get("function", tool)
            converted.append({
                "name": fn["name"],
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters") or {"type": "object", "properties": {}},
            })
        return converted
    
    def _process_event(self, event):
        calls: dict[str,ToolCall] = {}
        event_type = getattr(event, "type", None)

        if event_type == "text":
            LOGGER.debug(f'replying {event.text}')
            return ApiEvent(event_type="replying", content=event.text)                    

        if event_type == "thinking":
            LOGGER.debug(f'thinking: {event.thinking}')
            return ApiEvent(event_type="thinking", content=event.thinking)

        # tool call start
        if event_type == "content_block_start":
            block = event.content_block
            if getattr(block, "type", None) == "tool_use":
                LOGGER.debug(f'tool call start: {block.name}')
                calls[event.index] = ToolCall(id=block.id, name=block.name, args={})
            return

        if event_type == "input_json":
            return

        # convert Anthropic tool call to the internal ToolCall format
        if event_type == "content_block_stop":
            block = getattr(event, "content_block", None)
            if block is not None and getattr(block, "type", None) == "tool_use":
                args = getattr(block, "input", None) or {}
                if not isinstance(args, dict):
                    args = {"_value": args}
                call = calls.get(event.index) or ToolCall(id=getattr(block, "id", ""), name=getattr(block, "name", ""))
                call.id = getattr(block, "id", call.id)
                call.name = getattr(block, "name", call.name)
                call.args = args
                calls[event.index] = call
                LOGGER.debug(f'tool calls: {calls}')
                return ApiEvent(event_type="tool_call", tool_calls=list(calls.values()))
                    

        if event_type == "error":
            err = getattr(event, "error", None)
            message = getattr(err, "message", None) or str(err or event)
            LOGGER.error(f'api error {message}')
            return ApiEvent(event_type='error', content=message)

    def get_stream(self, records: list[ChatRecord], tools: list[dict] | None = None) -> Iterator[ApiEvent]:
        ''' calls Anthropic.connection.messages.stream() and converts the MessageStream events to the internal ApiEvent format '''
        LOGGER.info(f'get_stream with {len(records)} records and {len(tools) if tools else '0'} tools')
        system, wire = self._records_to_anthropic(records)
        anthropic_tools = self._to_anthropic_tools(tools)

        self.api_kwargs["messages"] = wire
        if system:
            self.api_kwargs["system"] = system
        if anthropic_tools:
            self.api_kwargs["tools"] = anthropic_tools


        # messages.stream() yields SDK helper events (text, thinking, input_json,
        # content_block_start/stop), not the raw SSE event types.
        with self.connection.messages.stream(**self.api_kwargs) as stream:
            for event in stream:
                api_event = self._process_event(event)
                if api_event:
                    yield api_event

        yield ApiEvent(event_type="done", content="")

    async def get_stream_async(self, records: list[ChatRecord], tools: list[dict] | None = None) -> AsyncGenerator[ApiEvent]:
        ''' calls Anthropic.connection.messages.stream() and converts the MessageStream events to the internal ApiEvent format '''
        LOGGER.info(f'get_stream with {len(records)} records and {len(tools) if tools else '0'} tools')
        system, wire = self._records_to_anthropic(records)
        anthropic_tools = self._to_anthropic_tools(tools)

        self.api_kwargs["messages"] = wire
        if system:
            self.api_kwargs["system"] = system
        if anthropic_tools:
            self.api_kwargs["tools"] = anthropic_tools


        # messages.stream() yields SDK helper events (text, thinking, input_json,
        # content_block_start/stop), not the raw SSE event types.
        async with self.connection_async.messages.stream(**self.api_kwargs) as stream:
            async for event in stream:
                api_event = self._process_event(event)
                if api_event:
                    yield api_event

        yield ApiEvent(event_type="done", content="")


class AnthropicProvider(Provider):
    def __init__(self,  url: str, key: str, max_tokens: int = DEFAULT_MAX_TOKENS):
        '''
        url: https://api.anthropic.com is the anthropic provided api but other services use the same spec
        key: your api key
        max_tokens: limits the output size from the api. passed by default to make_client but can be set in that call too
        '''
        LOGGER.info(f'__init__: {url} {max_tokens}')
        LOGGER.debug(key)
        kwargs = {"api_key": key or None}
        kwargs["base_url"] = url
        self.connection = Anthropic(**kwargs)
        self.max_tokens = max_tokens

    def list_models(self) -> list[str]:
        try:
            models = []
            page = self.connection.models.list(limit=100)
            models.extend(m.id for m in page.data)
            while getattr(page, "has_more", False) and getattr(page, "last_id", None):
                page = self.connection.models.list(limit=100, after_id=page.last_id)
                models.extend(m.id for m in page.data)
            return models
        except Exception as e:
            LOGGER.error(f'list_models error: {e}')
            return []

    def make_client(self, model_name: str, **api_kwargs) -> AnthropicClient:
        return AnthropicClient(self.connection, model_name, max_tokens=self.max_tokens, **api_kwargs)


def create_anthropic_client(url: str, model: str, key: str, **api_kwargs):
    '''helper function to make an AnthropicClient'''
    return AnthropicProvider(url, key).make_client(model, **api_kwargs)


def anthropic_agent_runtime(url: str, 
                         model: str, 
                         key: str = 'no key', 
                         system_prompt: str = '', 
                         memory_manager: MemoryManager | None = None,
                         skill_manager: SkillManager | None = None,
                         toolbox: Toolbox | None = None,
                         guardrail: Guardrail | None = None, 
                         max_tokens: int = 32_000,
                         max_rounds: int = 10,
                         **api_kwargs):
    ''' helper function to simplify creating an AgentRuntime session with the Anthropic api. api_kwargs are passed into messages.stream() model, messages, tools, system, and max_tokens are set internal and should not be added to api_kwargs. '''
    return PangolinRuntime(
        composer= PangolinComposer(client=create_anthropic_client(url=url, model=model, key=key, **api_kwargs)),
        system_prompt=system_prompt,
        memory_manager=memory_manager or SimpleMemoryManager(),
        skill_manager=skill_manager,
        toolbox=toolbox,
        guardrail=guardrail,
        max_tokens=max_tokens,
        max_rounds=max_rounds
    )