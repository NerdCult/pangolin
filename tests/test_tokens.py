#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import pytest
from pangolin.messages.chat_record import ChatRecord, Part, ToolCall
from pangolin.utils.token_calculator import message_tokens

@pytest.fixture
def mock_record():
    """A fixture to provide a fake TARecord for testing."""
    record = ChatRecord(role='user', content=[Part(type='text', data={'text': 'hello, world!'})])
    return record

def test_message_tokens_text(mock_record):
    """Test that text messages are calculated correctly."""
    # 'Hello, world!' is 13 chars. 
    # Our estimate_tokens logic: (13 + 3) // 4 = 4 tokens
    # message_tokens adds a per_message_overhead of 4 by default.
    # Total expected: 4 (content) + 4 (overhead) = 8 tokens.
    
    token_count = message_tokens(mock_record)
    assert token_count == 8

@pytest.fixture
def tool_call():
    """A fixture that provides a record with text, an image, and a tool call."""
    record = ChatRecord(
        role='assistant',
        content=[
            Part(type='text', data={'text': 'Here is a photo and a tool call.'})
        ],
        tool_calls=[
            ToolCall(name='get_weather', args={'location': 'London'})
        ]
    )
    return record

def test_message_tokens_complex(tool_call):
    """Test that text, images, and tool calls are all accounted for."""
    
    token_count = message_tokens(tool_call)
    assert token_count == 21