#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from dataclasses import dataclass
from typing import Literal
from .ta_record import TARecord

agent_message_type = Literal['thinking', 'replying', 'tool_calls', 'message', 'done']

@dataclass
class AgentMessage:
    ''' ApiEvents are translated to this data class in the ApiAggregator before being passed the AgentRuntime '''
    behavior: agent_message_type
    content: str = '' 
    message: TARecord | None = None
