---
description: Load when writing a new Guardrail. Covers the three event types, approve modify deny, and which response fields the runtime actually honors. Not for turning DefaultGuardrail on.
---
# Guardrail

Optional. If the app does not pass one, nothing is checked. DefaultGuardrail is the reference for "block these tool names." It is not installed by the factories.

Sync protocol, required for `handle_user_message`:

```python
def handle_guardrail_event(self, event: GuardrailEvent) -> GuardrailEventResponse: ...
```

Async protocol, used only by `handle_user_message_async` and `handle_user_message_to_queue` when the object implements GuardrailAsync:

```python
async def handle_guardrail_event_async(self, event: GuardrailEvent) -> GuardrailEventResponse: ...
```

A class can implement both. A GuardrailAsync-only object cannot be used with the sync entry point. The runtime raises `PangolinValueError`. On the async path, a sync-only guardrail is called via `asyncio.to_thread`.

## Events

`GuardrailEvent(event_type, chat_record)`.

| event_type | When | chat_record |
|---|---|---|
| `user_input` | Before the user record is stored | The user record |
| `assistant_output` | When the composer emits `behavior='message'` | The assistant record, which may contain `tool_calls` |
| `tool_call_result` | After a tool runs, before the result is stored | `role='tool'`, text in `content[0].data['text']`, `tool_call_id` set |

Display deltas (`thinking`, `replying`) are not guardrail events. You see the finished assistant record once.

## Responses

`GuardrailEventResponse(event_type, reason=None, chat_record=None, rejected_tool_call_ids=None, inject_ta_records=None)`.

| response | user_input | assistant_output | tool_call_result |
|---|---|---|---|
| `approve` | Record stored as-is | Stored as-is | Stored as-is |
| `modify` | `chat_record` is stored instead | `chat_record` replaces the assistant message. `rejected_tool_call_ids` are not executed. `reason` is stored as the tool result for each blocked id | `chat_record` is stored instead of the real result |
| `deny` | Raises `PangolinGuardRailDenial`. Turn ends as `behavior='guardrail'` | Same | **Not special.** The runtime only checks `modify`. `deny` does not stop the turn and does not replace the result |

`inject_ta_records` is never read. Set it and nothing happens.

Blocked tool calls still need a tool-role record or the next API call breaks. The runtime does that for ids in `rejected_tool_call_ids`, using `reason` as the text. Do not also delete those calls from `chat_record.tool_calls` unless you want the model to forget it asked. DefaultGuardrail leaves the calls on the record and lists the ids.

`reason` on a `modify` of assistant output should be model-readable. It becomes the tool result. "tool blocked by the current runtime guardrail policy" is the built-in text.

## DefaultGuardrail behavior

`DefaultGuardrail(blocked_tools=None)` default blocks `create_tool`,`delete_file`, `write_file`, and `run_sh`. Approves `user_input` and `tool_call_result`. On `assistant_output`, if any tool name is blocked, returns `modify` with those ids. If none are blocked, `approve`. Any other event type is `deny`.

Matching is exact on `ToolCall.name`, not on arguments. A blocked tool with a different name string will run.

## Skeleton

```python
from pangolin_agent.core.interfaces import Guardrail
from pangolin_agent.core.types import GuardrailEvent, GuardrailEventResponse

class ReadOnlyGuardrail(Guardrail):
    def handle_guardrail_event(self, event: GuardrailEvent) -> GuardrailEventResponse:
        if event.event_type == "assistant_output" and event.chat_record and event.chat_record.tool_calls:
            blocked = [tc.id for tc in event.chat_record.tool_calls if tc.name != "read_file"]
            if blocked:
                return GuardrailEventResponse(
                    event_type="modify",
                    reason="only read_file is allowed",
                    chat_record=event.chat_record,
                    rejected_tool_call_ids=blocked,
                )
        if event.event_type in ("user_input", "assistant_output", "tool_call_result"):
            return GuardrailEventResponse(event_type="approve")
        return GuardrailEventResponse(event_type="deny", reason="unknown event")
```

## Do not

Do not raise for a blocked tool if you still want the conversation to continue. Use `modify` and `rejected_tool_call_ids`. Raise, or return `deny` on user input or assistant output, only to abort the turn. Do not implement a second policy inside the toolbox. Do not expect `deny` on a tool result to drop that result. It will not.
