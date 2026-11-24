---
description: Load when writing a new MemoryManager. Covers get_context, add_context, trim_context, and the IdTrackedMemoryManger extra. Not for using the existing Simple or SQLite implementations.
---
# MemoryManager

The runtime stores history here. It does not store the system prompt or the skills text here. Those are rebuilt every turn and prepended in front of `get_context()`.

Reference implementations: `SimpleMemoryManager`, `SQLiteMemoryManager`. Read them. Do not copy the SQLite schema into a new class unless you are extending that one.

## What the runtime calls

```python
def get_context(self) -> list[ChatRecord]: ...
def add_context(self, record: ChatRecord) -> None: ...
def trim_context(self) -> None: ...
```

Nothing else. No async methods. The runtime will not await you.

`get_context` returns the records the model should see, oldest first, not counting the system record. Return the live list or a copy. Either works. Do not include a system record. The runtime already made one.

`add_context` receives user records, assistant records, and tool-result records (`role='tool'`, `tool_call_id` set). Append. Do not trim inside `add_context`. The runtime decides when.

`trim_context` must make the next `get_context()` smaller. The runtime does this after every add:

```python
while count_tokens(system_plus_history, tool_schemas) > max_tokens:
    memory_manager.trim_context()
```

A no-op trim loops until the process dies. If the history cannot shrink further, raise `PangolinError` the way the built-ins do.

## Trim rules that keep APIs from rejecting the next request

- After trimming, the first record should be `role='user'`. Providers dislike a transcript that starts on an assistant or tool record.
- If you drop an assistant record that has `tool_calls`, also drop every later record whose `tool_call_id` is one of those ids. Orphan tool results are an API error.
- Do not drop a tool result and leave its assistant `tool_calls` entry behind. Same failure, other direction.
- Persist if you want, but trim the in-memory window the runtime reads. Deleting from disk and still returning the full list does not count.

## IdTrackedMemoryManager

Subclass it only if you have a chat id and a summary. 

```python
def update_chat_summary(self, name: str, description: str) -> None: ...
```

The runtime never calls this. A session-aware tool or the host app does. SQLiteMemoryManager stores `chat_id`, `last_used`, `name`, `description`, `token_count` and reloads a token-capped window when `chat_id` already exists.

## Skeleton

```python
from pangolin_agent.core.interfaces import MemoryManager
from pangolin_agent.core.exceptions import PangolinError
from pangolin_agent.messages import ChatRecord

class ListMemory(MemoryManager):
    def __init__(self):
        self.memory: list[ChatRecord] = []

    def get_context(self) -> list[ChatRecord]:
        return self.memory

    def add_context(self, record: ChatRecord) -> None:
        self.memory.append(record)

    def trim_context(self) -> None:
        if not self.memory:
            raise PangolinError("nothing left to trim; raise max_tokens or shrink the prompt")
        dropped = self.memory.pop(0)
        ids = {tc.id for tc in dropped.tool_calls} if dropped.tool_calls else set()
        while self.memory and self.memory[0].role != "user":
            nxt = self.memory.pop(0)
            if nxt.tool_calls:
                ids.update(tc.id for tc in nxt.tool_calls)
        if ids:
            self.memory = [m for m in self.memory if m.tool_call_id not in ids]
```

## Do not

Do not implement `handle_user_message`. Do not call `trim_context` yourself from `add_context` unless you also still honor the runtime's calls. Do not return a string. Do not invent a system record. Do not add an async API and expect the runtime to use it.