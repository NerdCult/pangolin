#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from ..core.exceptions import PangolinImportError
try:
    from google import genai
    from google.genai import types
except:
    raise PangolinImportError('using gemini_provider requires installing the google-genai library')
import logging, uuid, base64
from typing import Iterator, Protocol, AsyncGenerator
from ..core.interfaces import Provider, Client, ClientAsync, MemoryManager, Toolbox, SkillManager, Guardrail
from ..memory_managers import SimpleMemoryManager
from ..response_composers import PangolinComposer
from ..agent_runtimes import PangolinRuntime
from ..messages import ChatRecord, ApiEvent, ToolCall

LOGGER = logging.getLogger(__name__)

DUMMY_SIGNATURE = b"skip_thought_signature_validator"

# Gemini only knows 'user' and 'model'. Tool results go back as 'user'.
ROLE_MAP = {"user": "user", "assistant": "model", "tool": "user"}

class GeminiClient(Client, ClientAsync, Protocol):
    def __init__(self, client: genai.Client, model_name: str, **api_kwargs):
        '''
        client: a google.genai.Client 
        model_name: must be a name the API knows. use GeminiProvider to get a list of models (not all work with new accounts or free tier)
        api_kwargs: passed to types.GenerateContentConfig(). system_instruction and tools are set internally and should not be set in api_kwargs; thinking_config defaults with types.ThinkingConfig(include_thoughts=True) but can be set in api_kwargs.
        '''
        LOGGER.info(f'__init__: {model_name}')
        self.client = client
        self.model_name = model_name
        self.api_kwargs = api_kwargs
        if not 'thinking_config' in self.api_kwargs.keys():
            self.api_kwargs['thinking_config'] = types.ThinkingConfig(include_thoughts=True)

    # converts OpenAI tools schemas to the format the Gemini APi expects
    def _tools_to_gemini(self, tools: list[dict] | None):
        if not tools:
            return None
        decls = []
        for t in tools:
            fn = t.get("function", t)  # handles OpenAI-style {"type": "function", "function": {...}}
            decls.append(types.FunctionDeclaration(
                name=fn["name"],
                description=fn.get("description", ""),
                parameters_json_schema=fn.get("parameters", {"type": "object", "properties": {}}),
            ))
        return [types.Tool(function_declarations=decls)]

    # converts ChatRecord to the format the Gemini API expects
    def _record_to_gemini(self, record: ChatRecord, call_names: dict) -> list[types.Part]:
        if record.role == "tool":
            text = record.content[0].data.get("text", "") if record.content else ""
            return [types.Part(function_response=types.FunctionResponse(
                id=record.tool_call_id,
                name=call_names.get(record.tool_call_id, "unknown"),  # Gemini wants the name, not just the id
                response={"result": text},
            ))]
        parts = [types.Part(text=p.data.get("text", ""))
                 for p in record.content or [] if p.type == "text"]
        for tc in record.tool_calls or []:
            sig = base64.b64decode(tc.thought_signature) if tc.thought_signature else DUMMY_SIGNATURE
            parts.append(types.Part(
                function_call=types.FunctionCall(id=tc.id, name=tc.name, args=tc.args or {}),
                thought_signature=sig))
        return parts

    # converts list[ChatRecord] to the format the Gemini API expects
    def _records_to_gemini(self, records: list[ChatRecord]):
        system, contents, call_names = [], [], {}
        for m in records:
            if m.role == "system":
                system += [p.data.get("text", "") for p in m.content or [] if p.type == "text"]
                continue
            for tc in m.tool_calls or []:
                call_names[tc.id] = tc.name
            parts = self._record_to_gemini(m, call_names)
            if not parts:
                continue
            role = ROLE_MAP[m.role]
            # merge back-to-back same-role turns (e.g. several tool results in a row)
            if contents and contents[-1].role == role:
                contents[-1].parts.extend(parts)
            else:
                contents.append(types.Content(role=role, parts=parts))
        return ("\n\n".join(system) or None), contents

    def _process_chunk(self, chunk, calls: list, finish: ApiEvent):
            cand = chunk.candidates[0]
            if cand.finish_reason:
                finish.content = cand.finish_reason
            for part in (cand.content.parts or []) if cand.content else []:
                if part.function_call:
                    fc = part.function_call
                    calls.append(ToolCall(
                    id=fc.id or f"call_{uuid.uuid4().hex[:8]}",
                    name=fc.name,
                    args=dict(fc.args or {}),
                    # convert the thought_signature for easier handling internally
                    thought_signature=base64.b64encode(part.thought_signature).decode() if part.thought_signature else None))
                elif part.text:
                    return ApiEvent(event_type="thinking" if part.thought else "replying",
                                   content=part.text)

    def get_stream(self, records: list[ChatRecord], tools: list[dict] | None = None) -> Iterator[ApiEvent]:
        ''' Sets the config with types.GenerateContentConfig() and calls models.generate_content(stream) converting the stream of GenerateContentResponse to ApiEvents '''
        system, contents = self._records_to_gemini(records)
        LOGGER.info(f'get_stream with {len(contents)} contents and {len(tools) if tools else 0} tools')
        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=self._tools_to_gemini(tools),
            **self.api_kwargs
        )

        calls, finish_event = [], ApiEvent(event_type='done')
        for chunk in self.client.models.generate_content_stream(
                model=self.model_name, contents=contents, config=config):
            if not chunk.candidates:
                continue
            api_event = self._process_chunk(chunk, calls, finish_event)
            if api_event:
                yield api_event

        if calls:
            LOGGER.info(f'tool calls: {calls}')
            yield ApiEvent(event_type="tool_call", tool_calls=calls)
        yield finish_event

    async def get_stream_async(self, messages: list[ChatRecord], tools: list[dict] | None = None) -> AsyncGenerator[ApiEvent]:
        ''' Sets the config with types.GenerateContentConfig() and calls models.generate_content(stream) converting the stream of GenerateContentResponse to ApiEvents '''
        system, contents = self._records_to_gemini(messages)
        LOGGER.info(f'get_stream with {len(contents)} contents and {len(tools) if tools else 0} tools')
        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=self._tools_to_gemini(tools),
            **self.api_kwargs
        )

        calls, finish_event = [], ApiEvent(event_type='done')
        response = await self.client.aio.models.generate_content_stream(model=self.model_name, contents=contents, config=config)
        async for chunk in response:
            if not chunk.candidates:
                continue
            api_event = self._process_chunk(chunk, calls, finish_event)
            if api_event:
                yield api_event

        if calls:
            LOGGER.info(f'tool calls: {calls}')
            yield ApiEvent(event_type="tool_call", tool_calls=calls)
        yield finish_event


class GeminiProvider(Provider):
    def __init__(self, api_key: str):
        '''
        api_key: https://aistudio.google.com/docs/api-key Google kindly provides a free tier api key
        '''
        self.client = genai.Client(api_key=api_key)

    def list_models(self):
        try:
            return sorted(
                m.name.removeprefix("models/") for m in self.client.models.list()
                if "generateContent" in (m.supported_actions or []) and "image" not in m.name)
        except Exception as e:
            LOGGER.error(f'list_models error: {e}')
            return []

    def make_client(self, model_name: str, **api_kwargs):
        ''' api_kwargs are passed into google.genai.types.GenerateContentConfig() '''
        return GeminiClient(self.client, model_name, **api_kwargs)

def create_gemini_client(model: str, key: str, **api_kwargs):
    '''helper function to make a GeminiClient'''
    return GeminiProvider(key).make_client(model, **api_kwargs)


def gemini_agent_runtime( 
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
    ''' helper function to simplify creating an AgentRuntime session with the Gemini api. api_kwargs are passed into types.GenerateContentConfig() system_instructions and tools are set internal and should not be added to api_kwargs. thinking_config defaults to include_thoughts=true but can be set in api_kwargs'''
    return PangolinRuntime(
        composer= PangolinComposer(client=create_gemini_client( model=model, key=key, **api_kwargs)),
        system_prompt=system_prompt,
        memory_manager=memory_manager or SimpleMemoryManager(),
        skill_manager=skill_manager,
        toolbox=toolbox,
        guardrail=guardrail,
        max_tokens=max_tokens,
        max_rounds=max_rounds
    )
