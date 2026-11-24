#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Literal
from ...messages import ChatRecord

EventType = Literal['tool_call_result', 'user_input', 'assistant_output']

@dataclass_json
@dataclass
class GuardrailEvent():
    event_type: EventType
    chat_record: ChatRecord | None = None

EventResponseType = Literal['approve', 'modify', 'deny']

@dataclass_json
@dataclass
class GuardrailEventResponse():
    event_type: EventResponseType
    reason: str | None = None
    chat_record: ChatRecord | None = None
    rejected_tool_call_ids: list[str] | None = None
    inject_chat_records: list[ChatRecord] | None = None