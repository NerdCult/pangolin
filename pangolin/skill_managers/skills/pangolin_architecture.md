---
description: Load for the Pangolin AI Agentic library architecture and high level understanding- protocols, how a turn connects them, shared types, and which built-in to pick. Not for wiring an app or implementing a component.
---
# Pangolin architecture

This library is still in beta. While the overall design and architecture should not change, some Protocols maybe extended with async alternatives, additional event hooks may be added.

Map only. PangolinRuntime and PangolinComposer are the shipped loop and composer. It is not recommended for them to be overidden.

## Who calls whom

```
app
  -> PangolinRuntime.handle_user_message(ChatRecord | str, stop: threading.Event = threading.Event())
       -> MemoryManager.get_context / add_context / trim_context
       -> SkillManager.skills()          # string, prepended to the system prompt
       -> Toolbox.schemas()              # OpenAI function schemas, or None
       -> ResponseComposer.process_context(records, tools)
            -> Client.get_stream(...) -> Iterator[ApiEvent]
            -> yields AgentMessage
       -> Toolbox.handle_tool_calls(...) # only if the assistant message had tool_calls
       -> Guardrail.handle_guardrail_event(...)  # if one was passed
```

The runtime builds the system record itself: `system_prompt` plus `skill_manager.skills()`. The memory manager never sees that record. It only stores user, assistant, and tool records.

Optional pieces are optional. No skill manager means no skills text. No toolbox means no tools and tool calls are not executed. No guardrail means no checks. Memory defaults to SimpleMemoryManager (which only stores the current session in memory, no persistence).

## One turn

1. User record is checked by the guardrail if present, then `add_context`.
2. After every add, while `count_tokens(system + history + tool schemas) > max_tokens`, the runtime calls `trim_context` and checks again. Trim that does not shrink is an infinite loop, and setting max_tokens too low could cause a long running tool round or result to be completely dropped.
3. The Agent Runtime then submits the full context (system + chat history) to the Response Composer, which forwards it to the Client.
4. Client translates the full context to the API specific format and makes the completion request, converting the result to ApiEvents and yielding those to the Response Composer
5. Composer streams AgentMessages back to the Runtime. `thinking`, `replying`, `tool_calls`, and `done` are for display. Only `behavior == 'message'` is accumulated from the stream of ApiEvents to hold the full response, and only that one can carry tool calls.
6. The AgentEvent with `behavior == 'message` triggers a guardrail check that can check for the response content and the tool calls being made. If the guardrail returns a `modify` response it can remove specific tool calls and inject a tool call response explaining that the specific tool call was blocked.
7. If that message has tool calls and a toolbox exists, the runtime runs them, guardrail-checks each result, and stores a `role='tool'` record per call. Then another round starts.
8. No tool calls ends the turn. `max_rounds` (default 10) caps rounds per user message. One round may contain several tool calls.

Async and queue entry points exist. Same steps. Sync `handle_user_message` requires a sync Guardrail. Async paths accept GuardrailAsync and fall back to the sync method on a thread. The Client must implement the corresponding entry point for a sync or async call.

## Protocols

All live in `pangolin.core.interfaces`. `@runtime_checkable`. The runtime checks `isinstance` on the ones it accepts.

| Protocol | Methods the runtime calls | Notes |
|---|---|---|
| MemoryManager | `get_context`, `add_context`, `trim_context` | Required shape. |
| IdTrackedMemoryManger | `update_chat_summary(name, description)` | Runtime never calls it. Intended to be called by a `session aware tool` or the application code |
| SkillManager | `skills() -> str`, `reload_skills()` | Runtime calls `skills` only. |
| SkillManagerDynamic | `load_skill`, `unload_skill` | Tools call these, not the runtime. |
| SkillManagerSkillMaker | `create_skill(skill_name, description, text)` | Same. |
| Toolbox | `load`, `schemas`, `handle_tool_calls` | `load` runs once in `PangolinRuntime.__init__`. |
| ToolboxAdvanced | `set_session`, `create_tool` | `set_session` runs before `load` if the toolbox is advanced. |
| Guardrail | `handle_guardrail_event` | Sync path. |
| GuardrailAsync | `handle_guardrail_event_async` | Async path only. |
| Client | `get_stream(records, tools) -> Iterator[ApiEvent]` | Composer calls this. |
| ClientAsync | `get_stream_async` | Async composer path. |
| Provider | `list_models`, `make_client` | App code calls this as a helper to get model names and generate a Client. Runtime never sees a Provider. |
| ResponseComposer | `process_context` | Shipped. Leave it. |
| AgentRuntime | `handle_user_message` | Shipped as PangolinRuntime. Leave it. |

## Shared types

- `ChatRecord`: `role` in `system|user|assistant|tool`, `content: list[Part] | None`, `tool_calls`, `tool_call_id`. Helpers: `user_record`, `assistant_record`, `system_record`.
- `Part`: `type`, `data` dict. Text is `Part(type='text', data={'text': ...})`.
- `ApiEvent`: `event_type` in `thinking|replying|tool_call|done|error`, `content`, `tool_calls`. Client output. Composer input.
- `AgentMessage`: `behavior` in `thinking|replying|tool_calls|message|done|error|guardrail`, `content`, optional `chat_record`. What the app iterates.
- `ToolCall`: `id`, `name`, `args`, optional `thought_signature` (Gemini; other providers ignore it).
- `ToolCallResult`: `id`, `result: str`.
- `GuardrailEvent.event_type`: `user_input`, `assistant_output`, `tool_call_result`.
- `GuardrailEventResponse.event_type`: `approve`, `modify`, `deny`. Also `reason`, `chat_record`, `rejected_tool_call_ids`, `inject_ta_records`.

`inject_ta_records` is not read by the runtime. Do not rely on it. Intended for possible future development.

## Built-ins

| Class | Pick it when |
|---|---|
| SimpleMemoryManager | Process memory only. Session dies with the process. |
| SQLiteMemoryManager | Resume by `chat_id`. File `ta_records.db`. In-memory window is what the model sees. |
| SimpleSkillManager | Concatenate every file in the skills folder into the prompt. |
| AdvancedSkillManager | Menu of names plus descriptions. Load, unload, and create on demand. Needs ToolboxAdvanced tools. |
| BasicToolbox | Fixed safe built-in set: browse_files, fetch_page, web_search, read_file, get_utc_time. Ignores session-aware tools. |
| PangolinToolbox | Load `*.py` from a tools folder. Can host session-aware tools and `create_tool`. `create_tool` is potentially dangerous without some Guardrail Implementation, DefaultGuardrail blocks `create_tool` and `delete_file` |
| DefaultGuardrail | Blocks named tools (default `create_tool`, `delete_file`) by rejecting their call ids. Approves user input and tool results. |
| OpenAIProvider / AnthropicProvider / GeminiProvider | One API family. `make_client` returns a Client. |
| SmokeTestClient | Scripted `ApiEvent`s. No network. For tests. Can be initialized with a custom set of ApiEvents to return in sequence, returns `script exhausted` each round once the scripted events are done. |
| cli | Prints a session. `thinking`, `replying`, `tool_calls`, `error`. Ctrl+C cancels the turn. The Github repo's example folder has more a visually robust cli and async examples|

Factories that return a ready runtime: `openai_agent_runtime`, `anthropic_agent_runtime`, `gemini_agent_runtime`, `smoke_test_runtime`. Those are app wiring. Not architecture. These are intended as the primary entry point for any user knowing the `url`, `api key`, and `model name` they want to use.

## What not to do

Do not invent a runtime, a composer, or a new message type. Do not call Dynamic skill methods or `update_chat_summary` from application loop code and expect the runtime to. Do not put the system prompt in the memory manager. 
