---
description: Load when building an app that uses the Pangolin AI Agentic library using the factories and the shipped runtime. Covers factory kwargs, consuming AgentMessages, adding a tool file, and copying built-ins. Not for implementing a protocol.
---
# Use Pangolin

Pangolin Agent can be pulled from the github repo 
```
git clone https://github.com/NerdCult/pangolin
cd ./pangolin
pip install -e .
```
or using `pip install pangolin-agent` and `import pangolin_agent`.

pangolin-agent was intentionally kept light on required dependencies, so the three built in Clients for OpenAI, Anthropic, and Gemini require those dependencies to be installed. (example: `pip install pangolin-agent[openai]`)

A PangolinImportError is raised if a module fails to get the dependencies when loaded.

## Example sessions

Hello Pangolin. This is the minimum code to enter a session chatting with an LLM. This does not employ all components available to the runtime and defaults to a simple in memory chat history memory management.
```python
from pangolin_agent.api_providers.open_ai_provider import openai_agent_runtime
#from pangolin_agent import cli # use the built in low dependency cli
from pangolin_agent import cli 

#Create a basic instance of AgentRuntime
# use anthropic_agent_runtime if you want to connect to their api
session = openai_agent_runtime(
    url='https://api.openai.com/v1',   
    model='gpt-4o-mini',              
    key='your-key-here')

#Launch the command line interface to interact with the AgentRuntime runtime.
cli(session)
```
The example below shows connecting directly to the event stream from the runtime.
```python
from pangolin_agent.api_providers.open_ai_provider import openai_agent_runtime
from pangolin_agent.messages import user_record
import asyncio

session = openai_agent_runtime(
    url="http://localhost:11434/v1",
    model="your-model",
    key="no key",
    system_prompt="You are a terse assistant.",
)

async def process_message(text):
    async for msg in session.handle_user_message(user_record(text)):
        if msg.behavior == "replying":
            print(msg.content, end="")

asyncio.run(process_message('hello'))
```

A bare string also works: `handle_user_message("hello")`. The runtime wraps it as a user record.

Same kwargs on all three API factories: `system_prompt`, `memory_manager`, `skill_manager`, `toolbox`, `guardrail`, `rag_connection`, `max_tokens=32_000`, `max_rounds=10`, plus `**api_kwargs` forwarded to the SDK completions call. Do not pass `model`, `messages`, `tools`, or `stream` in `api_kwargs`. The client sets those.

| Factory | Required | Notes |
|---|---|---|
| `openai_agent_runtime(url, model, key='no key', ...)` | `openai` package | url is the API base. |
| `anthropic_agent_runtime(url, model, key='no key', ...)` | `anthropic` package | |
| `gemini_agent_runtime(model, key='no key', ...)` | `google-genai` package | No url argument. |
| `smoke_test_runtime(...)` | nothing | No network. used to test runtime or component changes. Returns a configurable script. |

`key` defaults to `'no key'`. Fine for a local server. Not fine for a hosted API.

Missing optional pieces stay None except memory, which becomes SimpleMemoryManager. No toolbox means the model gets no tools. No guardrail means no checks. DefaultGuardrail is not installed for you. No SkillManager means no skills provided.

## What you iterate

`handle_user_message` yields `AgentMessage`.

| behavior | What to do |
|---|---|
| `thinking` | Display `content` if you want. Not stored by you or the runtime. |
| `replying` | Display `content`. Deltas, so print with `end=""`. Likely the full response will come across several of these events. |
| `tool_calls` | Display only. `content` is the calls repr. |
| `message` | Already stored by the runtime. Skip unless you inspect `chat_record`. |
| `done` | Round finished. |
| `error` | `content` is the exception. The loop ended. |
| `guardrail` | Denied. `content` is the denial. The loop ended. |

`pangolin_agent.cli(session)` is the zero-UI option. It hides `message`, prints the rest, and treats Ctrl+C as cancel. the Github repo examples folder has cli implmentations with color coded output and any key to cancel the agent loop, require `colorama` and `pynput`.

Async: `async for msg in session.handle_user_message(...)`. Queue: `handle_user_message_to_queue(record, queue, stop, done)`. PangolinRuntime, PangolinComposer, and the built-in Clients are setup up to run async, runtime calls to the components (SkillManager, MemoryManager, Toolbox, and Guardrail) can accept sync or async implementations (those built-in implementations are sync).

## Add tools without writing a toolbox

`BasicToolbox`, recommended for a basic research assistant type use case, implements the basic toolset from the library directory and provides tools for web search, browsing and reading files. It can not create tools, create/load/unload skills, or edit files.

`PangolinToolbox` implements a more capable Toolbox, but requires a little more setup. It can run `session aware tools` that can communicate with the rest of the runtime components.

Some tools require extra dependencies. Using a tool that has missing dependencies will return a result telling the agent to prompt the user to install those dependencies.

```python
from pangolin_agent.utils import copy_built_in_tools
from pangolin_agent.toolboxes import PangolinToolbox

copy_built_in_tools("./tools")  # copies the standard tool modules (browse_files, read_file, web_search/web_search_playwright, fetch_page, load_skill, unload_skill, create_skill, update_chat_summary, get_utc_time). use copy_built_in_power_tools to get create_tool, delete_file, write_file, run_sh **these tools should be inspected and understood before allowing and agent to access them, recommend implementing a Guardrail if you use them**
toolbox = PangolinToolbox(tools_folder="./tools")
```

Pass `toolbox=toolbox` to the factory. The runtime calls `load()`.

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

create_tool session aware code
```python
def make_session_aware_run(session):
    def run(tool_name: str, code: str) -> str:
        return session.toolbox.create_tool(tool_name, code)

    return run
```

## Skills

```python
from pangolin_agent.skill_managers import SimpleSkillManager, AdvancedSkillManager
from pangolin_agent.utils import copy_built_in_skills

copy_built_in_skills("./skills")  # built-in skills cover how to use and develop pangolin-agent.
skills = SimpleSkillManager(skill_folder="./skills")  # every file in the prompt
# or
skills = AdvancedSkillManager(skill_folder="./skills")  # menu only, until load_skill
```

`SimpleSkillManager` reads all files in the director, including front matter, and dumps it in the system prompt. `AdvancedSkillManager` shows names and descriptions until something calls `load_skill`. The runtime will not call `load_skill` for you. That requires load_skill / unload_skill tools plus ToolboxAdvanced implementation (example: PangolinToolbox). copy_built_in_tools includes those tools.
`RAGSkillManager` loads skills into a vector database and can set the skills at the start of the agent turn. It must also be passed into the runtime as the `rag_connection` or attched to a `RAGRouter` that gets passed in as `rag_connection`

Skill files are `.md` . Markdown front matter is one line: `description: ...`.

## Memory 

```python
from pangolin_agent.memory_managers import SQLiteMemoryManager
from pangolin_agent.guardrails import DefaultGuardrail
from uuid import UUID

memory = SQLiteMemoryManager(sqlite_folder="./db", chat_id=UUID("..."))  # omit chat_id to start new
guard = DefaultGuardrail(blocked_tools=["create_tool", "delete_file", "write_file", "run_sh"])
```

SQLite file is `chat_records.db` inside that folder. Resuming loads an in-memory window (`reload_token_limit`, default 8000), not the full history. `update_chat_summary` is yours to call if you want a name, or the session aware tool `update_chat_summary`. The runtime never calls it.

`DefaultGuardrail` approves user input and tool results. On assistant output it rejects tool-call ids whose name is in `blocked_tools`, and the runtime stores the reason as the tool result instead of running the tool. `deny` aborts the turn.

## Smoke test

```python
from pangolin_agent.api_providers.smoke_test_client import smoke_test_runtime
from pangolin_agent.messages import ApiEvent

session = smoke_test_runtime(
    responses=[ApiEvent(event_type="replying", content="ok"), ApiEvent(event_type="done")],
    show_system=True,
)
```

`show_system=True` makes the scripted stream echo the system prompt it received. `list_tools=True` echoes tool schemas. Use this to prove wiring. It is not a model.

## RAG Connection

Any component can implement `RAGComponent` and be passed in as `rag_connection`. There is also a `RAGRouter` that can accept a `SkillManager` and a `Toolbox` allowing both to process the chat_history. `RAGSkillManager` can be configured to `process_last_n_user_recoreds`.

## Stop

If the next step is a new MemoryManager, SkillManager, Provider, Toolbox, or Guardrail, this skill is the wrong one. Load that component skill. Do not re-describe the turn loop in the app.
