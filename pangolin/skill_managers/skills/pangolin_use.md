---
description: Load when building an app that uses the Pangolin AI Agentic library using the factories and the shipped runtime. Covers factory kwargs, consuming AgentMessages, adding a tool file, and copying built-ins. Not for implementing a protocol.
---
# Use Pangolin

Wire an app. Do not implement PangolinRuntime, PangolinComposer. Those already exist.

Imports are absolute. `from pangolin.agent_runtimes import PangolinRuntime` works. `from .agent_runtimes import ...` does not work outside the package.

## Smallest session

```python
from pangolin.api_providers.open_ai_provider import openai_agent_runtime
from pangolin.messages import user_record

session = openai_agent_runtime(
    url="http://localhost:11434/v1",
    model="your-model",
    key="no key",
    system_prompt="You are a terse assistant.",
)

for msg in session.handle_user_message(user_record(text="hello")):
    if msg.behavior == "replying":
        print(msg.content, end="")
```

A bare string also works: `handle_user_message("hello")`. The runtime wraps it as a user record.

Same kwargs on all three API factories: `system_prompt`, `memory_manager`, `skill_manager`, `toolbox`, `guardrail`, `max_tokens=32_000`, `max_rounds=10`, plus `**api_kwargs` forwarded to the SDK completions call. Do not pass `model`, `messages`, `tools`, or `stream` in `api_kwargs`. The client sets those.

| Factory | Required | Notes |
|---|---|---|
| `openai_agent_runtime(url, model, key='no key', ...)` | `openai` package | url is the API base. |
| `anthropic_agent_runtime(url, model, key='no key', ...)` | `anthropic` package | |
| `gemini_agent_runtime(model, key='no key', ...)` | `google-genai` package | No url argument. |
| `smoke_test_runtime(...)` | nothing | No network. |

`key` defaults to `'no key'`. Fine for a local server. Not fine for a hosted API.

Missing optional pieces stay None except memory, which becomes SimpleMemoryManager. No toolbox means the model gets no tools. No guardrail means no checks. DefaultGuardrail is not installed for you. No SkillManager means no skills provided.

## What you iterate

`handle_user_message` yields `AgentMessage`.

| behavior | What to do |
|---|---|
| `thinking` | Display `content` if you want. Not stored by you. |
| `replying` | Display `content`. Deltas, so print with `end=""`. |
| `tool_calls` | Display only. `content` is the calls repr. |
| `message` | Already stored by the runtime. Skip unless you inspect `chat_record`. |
| `done` | Round finished. |
| `error` | `content` is the exception. The loop ended. |
| `guardrail` | Denied. `content` is the denial. The loop ended. |

`pangolin.cli(session)` is the zero-UI option. It hides `message`, prints the rest, and treats Ctrl+C as cancel. the Github repo examples folder has cli implmentations with color coded output and async handling.

Async: `async for msg in session.handle_user_message_async(...)`. Queue: `handle_user_message_to_queue(record, queue, stop, done)`. The composer must implement the async composer, which PangolinComposer does. Sync guardrails are run on a thread. An async-only guardrail cannot be used with the sync entry point. The Client must also implement the corresponding sync or async entry point, all of the built in api providers do this.

## Add tools without writing a toolbox

```python
from pangolin.utils import copy_built_in_tools
from pangolin.toolboxes import PangolinToolbox

copy_built_in_tools("./tools")  # copies the built-in tool modules; read them before enabling. Either delete the tools you don't want or implement guardrail to check for those tools on `assistant_message` events, DefaultGuardrails blocks create_tool and delete_file.
toolbox = PangolinToolbox(tools_folder="./tools")
```

Pass `toolbox=toolbox` to the factory. The runtime calls `load()`.

BasicToolbox ignores the folder and loads only browse_files, fetch_page, web_search, read_file, get_utc_time from the package. Use it when the model must not write files or create tools.

A new tool file in the PangolinToolbox folder:

```python
SCHEMA = {
    "name": "echo",
    "description": "Return the text unchanged.",
    "parameters": {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
}

def run(text: str) -> str:
    return text
```

`SCHEMA["name"]` must match the file stem only by convention. The registry key is `SCHEMA["name"]`. `run` keyword arguments must match the schema properties. Return a str, dict, list, number, or bool. The toolbox json-dumps it and caps the length (default 50_000 chars).

Session-aware tools (`make_session_aware_run`) are a toolbox-skill topic. Do not invent that pattern here. BasicToolbox skips those files.

## Skills

```python
from pangolin.skill_managers import SimpleSkillManager, AdvancedSkillManager
from pangolin.utils import copy_built_in_skills

copy_built_in_skills("./skills")  # demo and library-dev skills, not app skills
skills = SimpleSkillManager(skill_folder="./skills")  # every file in the prompt
# or
skills = AdvancedSkillManager(skill_folder="./skills")  # menu only, until load_skill
```

SimpleSkillManager reads the whole file, including front matter, and dumps it in the system prompt. AdvancedSkillManager shows names and descriptions until something calls `load_skill`. The runtime will not call `load_skill` for you. That requires load_skill / unload_skill tools plus ToolboxAdvanced. PangolinToolbox is that. The built-in copies include those tools.

Skill files are `.md` . Markdown front matter is one line: `description: ...`.

## Memory and guardrail

```python
from pangolin.memory_managers import SQLiteMemoryManager
from pangolin.guardrails import DefaultGuardrail
from uuid import UUID

memory = SQLiteMemoryManager(sqlite_folder="./db", chat_id=UUID("..."))  # omit chat_id to start new
guard = DefaultGuardrail(blocked_tools=["create_tool", "delete_file"])
```

SQLite file is `ta_records.db` inside that folder. Resuming loads an in-memory window (`reload_token_limit`, default 8000), not the full history. `update_chat_summary` is yours to call if you want a name, or a session aware tool could call it. The runtime never calls it.

DefaultGuardrail approves user input and tool results. On assistant output it rejects tool-call ids whose name is in `blocked_tools`, and the runtime stores the reason as the tool result instead of running the tool. `deny` aborts the turn.

## Smoke test

```python
from pangolin.api_providers.smoke_test_client import smoke_test_runtime
from pangolin.messages import ApiEvent

session = smoke_test_runtime(
    responses=[ApiEvent(event_type="replying", content="ok"), ApiEvent(event_type="done")],
    show_system=True,
)
```

`show_system=True` makes the scripted stream echo the system prompt it received. `list_tools=True` echoes tool schemas. Use this to prove wiring. It is not a model.

## Stop

If the next step is a new MemoryManager, SkillManager, Provider, Toolbox, or Guardrail, this skill is the wrong one. Load that component skill. Do not re-describe the turn loop in the app.
