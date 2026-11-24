#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from dataclasses_json import dataclass_json
from dataclasses import dataclass
from typing import Literal
from .tool_call import ToolCall

@dataclass_json
@dataclass
class Part:
    type: str
    data: dict

RoleType = Literal['system', 'user', 'assistant', 'tool']

@dataclass_json
@dataclass
class ChatRecord:
    '''
    The Pangolin internal data class used to store interactions between user, assistant, system, and tool results.
    '''
    role: RoleType
    content: list[Part] | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] | None = None

def user_record( text: str) -> ChatRecord:
    '''
    helper function to create a user ChatRecord 
    '''
    return ChatRecord(role='user', content=[Part(type='text',data={'text': text})])

def assistant_record( text: str) -> ChatRecord:
    '''
    helper function to create a user ChatRecord 
    '''
    return ChatRecord(role='assistant', content=[Part(type='text', data={'text': text})])

def system_record(text: str) -> ChatRecord:
    '''
    helper function to create a user ChatRecord 
    '''
    return ChatRecord(role='system', content=[Part(type='text', data={'text': text})])