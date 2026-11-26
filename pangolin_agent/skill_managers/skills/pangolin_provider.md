---
description: Load when writing a new Provider or Client to connect to a new LLM API or customize handling. Covers list_models, make_client, get_stream, and the ApiEvent stream PangolinComposer already consumes. Not for reimplementing the composer or the runtime.
---
# Provider and Client

A new API needs a Client. It needs a Provider only if the app should list models and construct clients, or is intended to be compatible with other Pangolin based applications. It does not need a new composer. PangolinComposer already turns ApiEvents into AgentMessages. Leave it alone.

Reference: `OpenAIClient` / `OpenAIProvider`, plus the Anthropic and Gemini modules. Copy the event mapping, not the SDK calls.

## Provider

```python
def list_models(self) -> list[str]: ...
def make_client(self, model_name: str, **api_kwargs) -> Client: ...
```

The runtime never sees a Provider. Application code does. `make_client` returns a Client, not a runtime. The factories in the built-in modules are convenience wrappers around `PangolinRuntime(composer=PangolinComposer(client=...))`. Match that if you add a factory. Do not write a new runtime class.

## Client

```python
def get_stream(self, records: list[ChatRecord], tools: list[dict] | None = None) -> Iterator[ApiEvent]: ...
```

PangolinComposer is the class that calls the Client and can handle sync and async implementations.

Inputs are ChatRecords and use Pangolin roles: `system`, `user`, `assistant`, `tool`. Convert them inside the client. Tool results are `role='tool'` with `tool_call_id` and text in `content[0].data['text']`. Assistant tool calls are `record.tool_calls: list[ToolCall]`, each with `id`, `name`, `args`.

`tools` use the OpenAI function wrappers:

```python
[{"type": "function", "function": SCHEMA}, ...]
```

`None` means no tools. Do not invent a tools list.

Output is an iterator of `ApiEvent`, not SDK chunks, not `AgentMessage`. Do not yield a event_type='message'.

```python
ApiEvent(event_type="thinking" | "replying" | "tool_call" | "done" | "error",
         content: str | None = None,
         tool_calls: list[ToolCall] | None = None)
```

| event_type | When | Fields |
|---|---|---|
| `replying` | Visible text delta | `content` is the delta, not the full text so far |
| `thinking` | Reasoning delta, if the API has it | `content` delta |
| `tool_call` | Model asked for tools | `tool_calls` is the complete list for this assistant turn, not a partial fragment, unless you are prepared to match what PangolinComposer expects from the built-in clients |
| `usage` | API provided usage counts | `usage` must be set |
| `done` | Stream finished cleanly | `content` optional |
| `error` | Provider failed | `content` is the message |

Yield deltas as they arrive. Do not buffer the whole completion and then yield once, unless the API gives you no choice. The composer forwards deltas so the UI can print them.

Gemini-only: `ToolCall.thought_signature` must round-trip on the tool call you send back next turn. Other providers ignore it. If your API has a similar opaque blob, that field is the place.

## What the composer does, so you do not redo it

PangolinComposer calls `get_stream`, yields display AgentMessages for thinking / replying / tool_calls / done, accumulates text, and yields one `behavior='message'` AgentMessage whose `chat_record` is the assistant record with the full text and the tool calls. The runtime stores that record. Your client does not create ChatRecords on the way out.

## Factory shape, if you add one

```python
def my_agent_runtime(model: str, key: str, system_prompt: str = "",
                     memory_manager=None, skill_manager=None, toolbox=None,
                     guardrail=None,
                     rag_connection=None, max_tokens: int = 32_000, max_rounds: int = 10, **api_kwargs):
    from pangolin_agent.agent_runtimes import PangolinRuntime
    from pangolin_agent.response_composers import PangolinComposer
    from pangolin_agent.memory_managers import SimpleMemoryManager
    return PangolinRuntime(
        composer=PangolinComposer(client=my_provider(key).make_client(model, **api_kwargs)),
        system_prompt=system_prompt,
        memory_manager=memory_manager or SimpleMemoryManager(),
        skill_manager=skill_manager,
        toolbox=toolbox,
        rag_connection=rag_connection
        guardrail=guardrail,
        max_tokens=max_tokens,
        max_rounds=max_rounds,
        **api_kwargs
    )
```

Put `**api_kwargs` on the SDK call. Do not let them override `model`, `messages`, `tools`, or `stream`.

## Do not

Do not subclass PangolinComposer. Do not yield `AgentMessage` from the client. Do not swallow SDK errors into an empty stream. Yield `ApiEvent(event_type='error', content=...)` or raise. A silent stop looks like a finished turn.
