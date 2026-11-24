---
description: Load when implementing, extending, or debugging RAG features. Covers RAGComponent, RAGRouter, RAGSkillManager, and how retrieval hooks into the runtime.
---

# RAG Components

The runtime calls `retrieve_with_chat_history(chat_history)` on any component passed into the constructor as rag_connection and that implements the `RAGComponent` protocol *before* each LLM turn. This lets a skill manager, toolbox, or custom component update its internal state (e.g. retrieved context, dynamic tool schemas) based on the conversation so far.

Reference: `rag_component.py`, `rag_router.py`, `rag_skill_manager.py`, `pangolin_runtime.py`.

## RAGComponent Protocol

```python
from typing import Protocol, runtime_checkable
from ...messages import ChatRecord

@runtime_checkable
class RAGComponent(Protocol):
    '''Hook to receive chat history before the LLM call so skills(), schemas(), etc. can be updated.'''
    def retrieve_with_chat_history(self, chat_history: list[ChatRecord]): ...
```

Any class claiming to be a `RAGComponent` must implement this method. It can be sync or async (the router and/or runtime wraps it safely).

## RAGRouter

```python
class RAGRouter(RAGComponent):
    def __init__(self, skill_manager: RAGComponent | None = None, toolbox: RAGComponent | None = None):
        ...
    async def retrieve_with_chat_history(self, chat_history):
        # Calls both in parallel (if both supplied) using asyncio.gather + ensure_async
```

The router is the glue the `PangolinRuntime` uses. Pass your `RAGSkillManager` (or a custom RAG toolbox) to it and the runtime will route the hook automatically. It does nothing if neither component is supplied. Optionally you can pass the RAGSkillManager in as the rag_connection.

## RAGSkillManager (the built-in RAG skill manager)

Implements *both* `SkillManager` *and* `RAGComponent`.

Key behaviors:
- On `retrieve_with_chat_history`: takes the last N user messages (configurable), embeds them, queries a Chroma collection of chunked `.md` files from `docs_folder`, filters by cosine distance, formats the hits, and stores the result in `skills_this_turn`.
- `skills()` simply returns whatever was stored this turn (empty string if no good hits).
- `reload_skills()` wipes the collection and re-indexes every `.md` file (chunked with overlap). Call this when you add/edit skill files.
- Uses `fastembed` (local ONNX BGE-small by default) + persistent Chroma. No API keys, works offline after first download.
- Configurable: `n_results`, `max_distance`, `max_chars`, chunk size/overlap, model, etc.

Default collection name is `"skills"`. Changing the embedding model requires deleting the DB and re-running `reload_skills()`.

## Writing Your Own RAG Component

```python
from pangolin_agent.core.interfaces import RAGComponent
from pangolin_agent.messages import ChatRecord

class MyRAGComponent(RAGComponent):
    def __init__(self):
        self.context_this_turn = ""

    def retrieve_with_chat_history(self, chat_history: list[ChatRecord]):
        # extract query from history, do your retrieval (vector DB, graph, API, whatever),
        # update internal state
        self.context_this_turn = "...retrieved stuff..."

    # Then expose it however you want:
    def skills(self) -> str:
        return self.context_this_turn
    # or affect tool schemas, memory, etc.
```

Register it via a `RAGRouter(skill_manager=..., toolbox=...)` or directly if your runtime accepts it.

## Do Not

- Block in `retrieve_with_chat_history` (make it async-friendly).
- Assume the runtime calls it at any particular time other than "before the LLM turn".
- Skip the `RAGComponent` check — the router will raise `PangolinTypeError`.

Load this skill (or `pangolin_architecture`) when you are touching any RAG code.

**Built-in skills can be copied to a working directory with:**

```python
from pangolin_agent.utils import copy_built_in_skills
copy_built_in_skills()  # or pass target dir
```
