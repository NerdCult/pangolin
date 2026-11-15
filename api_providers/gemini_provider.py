#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import logging, uuid, base64
from typing import Iterator
from google import genai
from google.genai import types
from ..core.interfaces import Provider, Client
from ..messages import TARecord, ApiEvent, ToolCall

LOGGER = logging.getLogger(__name__)

DUMMY_SIGNATURE = b"skip_thought_signature_validator"

# Gemini only knows 'user' and 'model'. Tool results go back as 'user'.
ROLE_MAP = {"user": "user", "assistant": "model", "tool": "user"}

class GeminiClient(Client):
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

    # converts TARecord.Parts to the format the Gemini API expects
    def _record_to_parts(self, record: TARecord, call_names: dict) -> list[types.Part]:
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

    # converts list[TARecord] to the format the Gemini API expects
    def _messages_to_gemini(self, messages: list[TARecord]):
        system, contents, call_names = [], [], {}
        for m in messages:
            if m.role == "system":
                system += [p.data.get("text", "") for p in m.content or [] if p.type == "text"]
                continue
            for tc in m.tool_calls or []:
                call_names[tc.id] = tc.name
            parts = self._record_to_parts(m, call_names)
            if not parts:
                continue
            role = ROLE_MAP[m.role]
            # merge back-to-back same-role turns (e.g. several tool results in a row)
            if contents and contents[-1].role == role:
                contents[-1].parts.extend(parts)
            else:
                contents.append(types.Content(role=role, parts=parts))
        return ("\n\n".join(system) or None), contents

    def get_stream(self, messages: list[TARecord], tools: list[dict] | None = None) -> Iterator[ApiEvent]:
        ''' Sets the config with types.GenerateContentConfig() and calls models.generate_content(stream) converting the stream of GenerateContentResponse to ApiEvents '''
        system, contents = self._messages_to_gemini(messages)
        LOGGER.info(f'get_stream with {len(contents)} contents and {len(tools) if tools else 0} tools')
        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=self._tools_to_gemini(tools),
            **self.api_kwargs
        )

        calls, finish = [], None
        for chunk in self.client.models.generate_content_stream(
                model=self.model_name, contents=contents, config=config):
            if not chunk.candidates:
                continue
            cand = chunk.candidates[0]
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
                    yield ApiEvent(event_type="thinking" if part.thought else "replying",
                                   content=part.text)
            if cand.finish_reason:
                finish = cand.finish_reason

        if calls:
            LOGGER.info(f'tool calls: {calls}')
            yield ApiEvent(event_type="tool_call", tool_calls=calls)
        yield ApiEvent(event_type="done", content=getattr(finish, "name", str(finish)))


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