#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Literal
from .chat_record import ChatRecord
from .api_event import Usage

agent_message_type = Literal['thinking', 'replying', 'tool_calls', 'message', 'usage', 'done', 'error', 'guardrail']

@dataclass_json
@dataclass
class AgentMessage:
    ''' ApiEvents are translated to this data class in the ResponseComposer before being passed the AgentRuntime '''
    behavior: agent_message_type
    content: str = '' 
    chat_record: ChatRecord | None = None
    usage : Usage | None = None
