#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from dataclasses import dataclass, field
from typing import Literal, Any
from .tool_call import ToolCall

EventType = Literal['thinking', 'replying', 'tool_call', 'usage', 'done', 'error']

@dataclass
class ApiEvent:
    ''' Api Clients convert the api response to this data class before passing them to the API Aggregator. 
    This data class helps support the aggregators responsibility to compose the complete response for use in a ChatRecord'''
    event_type: EventType
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    usage: Usage | None = None

@dataclass
class Usage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost: float | None = None          # normalized if possible
    raw: dict[str, Any] = field(default_factory=dict)    # provider-specific extras
