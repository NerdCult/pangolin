#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Literal
from ...messages import TARecord

EventType = Literal['tool_call_result', 'user_input', 'assistant_output']

@dataclass_json
@dataclass
class GuardrailEvent():
    event_type: EventType
    ta_record: TARecord | None = None

EventResponseType = Literal['approve', 'deny', 'modify']

@dataclass_json
@dataclass
class GuardrailEventResponse():
    event_type: EventResponseType
    reason: str | None = None
    ta_record: TARecord | None = None