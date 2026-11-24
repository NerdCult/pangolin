---
description: Load when writing a new Toolbox, or a session-aware tool. Covers load, schemas, handle_tool_calls, set_session, and create_tool. Not for dropping a normal tool file into PangolinToolbox.
---
# Toolbox

A normal tool file dropped into a PangolinToolbox folder is application wiring, not this skill. This skill is for a new Toolbox class, or a tool that needs the runtime.

Reference: `BasicToolbox` (Toolbox), `PangolinToolbox` (ToolboxAdvanced).

## Toolbox

```python
def load(self) -> None: ...
def schemas(self) -> list[dict]: ...
def handle_tool_calls(self, calls: list[ToolCall]) -> Iterator[ToolCallResult]: ...
```

The runtime calls `load()` once, from `PangolinRuntime.__init__`, before the first turn. It calls `schemas()` every turn. It calls `handle_tool_calls` only when the assistant message had tool calls.

`schemas()` must return OpenAI function wrappers, or `None` is wrong — return an empty list if you have no tools:

```python
[{"type": "function", "function": schema_dict}, ...]
```

`schema_dict` is the object with `name`, `description`, and `parameters`. The built-in clients forward this list. A custom client may need to unwrap it. That is the client's job.

`handle_tool_calls` receives `ToolCall(id, name, args, thought_signature)`. `args` is a dict. Yield one `ToolCallResult(id=call.id, result=str)` per call you actually ran. The runtime has already removed guardrail-blocked ids. Do not re-check policy here.

Unknown tool: still return a result string the model can read, for example `json.dumps({"error": "unknown tool ..."})`. Raising loses the turn. Exceptions inside a tool should become that same kind of error string. The built-ins do this.

Result strings should be bounded. Built-ins cap at 50_000 characters and append a truncation note. An unbounded tool result blows `max_tokens` on the next trim cycle.

## ToolboxAdvanced

```python
def set_session(self, session: AgentRuntime) -> None: ...
def create_tool(self, tool_name: str, code: str) -> str: ...
```

If the runtime sees ToolboxAdvanced, it calls `set_session(self)` before `load()`. Session-aware tools must be built in `load`, after that call, or `self.session` is missing.

`create_tool` is not called by the runtime. A session-aware tool or the host calls it. It must write the tool somewhere `load` would have found it, then register it immediately. Returning an error string beats raising. The model has to read the failure.

## Tool module shapes

Ordinary, used by both built-in toolboxes:

```python
SCHEMA = {
    "name": "echo",
    "description": "Return the text.",
    "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
}

def run(text: str) -> str:
    return text
```

`run` keywords match `properties`. Return str, dict, list, number, or bool. The toolbox json-dumps the return value. Do not return a pre-dumped JSON string unless you want double encoding. A datetime and anything else non-JSON survives only if the toolbox passes `default=str`, which the built-ins do. A new toolbox should do the same.

Session-aware, PangolinToolbox only. BasicToolbox skips the file on purpose:

```python
def make_session_aware_run(session):
    def run(skill_name: str) -> str:
        session.skill_manager.load_skill(skill_name)
        return f"{skill_name} loaded"
    return run
```

No module-level `run` is required when `make_session_aware_run` exists. PangolinToolbox prefers that hook. The function it returns is what gets called.

`set_session` must have run first. Calling `make_session_aware_run` without a session is a bug in `load` order, not in the tool.

The built-in tools can be copied to a new directory using the code below. Default copies to the current working directory/tools/ or you can pass in a target directory. You can also use `copy_built_in_power_tools` to get the files for `create_tool`,`delete_file`, `write_file`, and `run_sh`, which should be reviewed and understood before giving access to an agent, it is recommended to use an implementation of Guardrail along with these tools.
**Review tools before using.**

```python
from pangolin_agent.utils import copy_built_in_tools

copy_built_in_tools()
```

## Skeleton

```python
import json
from typing import Iterator
from pangolin_agent.core.interfaces import Toolbox
from pangolin_agent.messages import ToolCall, ToolCallResult

class StaticToolbox(Toolbox):
    def __init__(self):
        self.registry = {}

    def load(self) -> None:
        self.registry["echo"] = (
            {"name": "echo", "description": "Echo.", "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
            lambda text: text,
        )

    def schemas(self) -> list[dict]:
        return [{"type": "function", "function": s} for s, _ in self.registry.values()]

    def handle_tool_calls(self, calls: list[ToolCall]) -> Iterator[ToolCallResult]:
        for c in calls:
            entry = self.registry.get(c.name)
            if not entry:
                yield ToolCallResult(id=c.id, result=json.dumps({"error": f"unknown tool {c.name}"}))
                continue
            try:
                out = json.dumps(entry[1](**c.args), ensure_ascii=False, default=str)
            except Exception as e:
                out = json.dumps({"error": f"{type(e).__name__}: {e}"})
            yield ToolCallResult(id=c.id, result=out)
```

## Do not

Do not call tools from `schemas`. Do not yield `AgentMessage`. Do not depend on `thought_signature` unless you are the Gemini client. Do not load session-aware tools from a plain Toolbox. `set_session` will never be called, and the file will fail or, if you skip it the way BasicToolbox does, silently not appear. Silent skip needs a comment. A crash needs a better `load`.
