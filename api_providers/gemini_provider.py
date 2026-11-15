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
        LOGGER.info(f'__init__: {model_name}')
        self.client = client
        self.model_name = model_name
        self.api_kwargs = api_kwargs
        if not self.api_kwargs['thinking_config']:
            self.api_kwargs['thinking_config'] = types.ThinkingConfig(include_thoughts=True),

    def _convert_tools(self, tools: list[dict] | None):
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

    def _to_contents(self, messages: list[TARecord]):
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
        system, contents = self._to_contents(messages)
        LOGGER.info(f'get_stream with {len(contents)} contents and {len(tools) if tools else 0} tools')
        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=self._convert_tools(tools),
            **self.api_kwargs
        )

        calls, finish = {}, None
        for chunk in self.client.models.generate_content_stream(
                model=self.model_name, contents=contents, config=config):
            if not chunk.candidates:
                continue
            cand = chunk.candidates[0]
            for part in (cand.content.parts or []) if cand.content else []:
                if part.function_call:
                    fc = part.function_call
                    calls[len(calls)] = ToolCall(
                    id=fc.id or f"call_{uuid.uuid4().hex[:8]}",
                    name=fc.name,
                    args=dict(fc.args or {}),
                    thought_signature=base64.b64encode(part.thought_signature).decode()
                        if part.thought_signature else None)
                elif part.text:
                    yield ApiEvent(event_type="thinking" if part.thought else "replying",
                                   content=part.text, raw=chunk)
            if cand.finish_reason:
                finish = cand.finish_reason

        if calls:
            LOGGER.info(f'tool calls: {calls}')
            yield ApiEvent(event_type="tool_call", tool_calls=calls)
        yield ApiEvent(event_type="done", content=getattr(finish, "name", str(finish)))


class GeminiProvider(Provider):
    def __init__(self, api_key: str):
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