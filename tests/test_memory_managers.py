#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import pytest
from pangolin import SimpleMemoryManager
from pangolin.messages import TARecord, Part, ToolCall

@pytest.fixture
def mock_simple_mm():
    return SimpleMemoryManager()

def test_simple_memory_manager(mock_simple_mm):    
    part = Part(type='text', data={'text': 'pangolins are cool'})
    message = TARecord(role='user', content=[part])
    mock_simple_mm.add_context(message)

    context = mock_simple_mm.get_context()

    assert len(context) == 1

    tar = context[0]
    
    assert tar.role == 'user'
    assert len(tar.content) == 1

    tar_part = tar.content[0]
    assert tar_part.data['text'] == 'pangolins are cool'

def test_simple_mm_multi_message(mock_simple_mm):
    part = Part(type='text', data={'text': 'pangolins are cool'})
    message = TARecord(role='user', content=[part])

    messages = [ TARecord(role='system', content=[Part(type='text', data={'text': 'you are an expert on pangolins'})]), 
                message,
                TARecord(role='assistant', content=[Part(type='text', data={'text': 'let me find some pangolin facts for you'})],
                         tool_calls=[ToolCall(id='test id', name='test_call', args={'test_param': 'test_value'})]), 
                TARecord(role='tool', content=[Part(type='text', data={'text': 'pangolins are in fact cool'})],
                         tool_call_id='test id'), 
    ]

    for m in messages:
        mock_simple_mm.add_context(m)
    context = mock_simple_mm.get_context()

    assert len(context) == 4

    context_message_0 = context[0]
    assert context_message_0.role == 'system'

    message_parts = context_message_0.content
    
    assert len(message_parts) == 1
    assert message_parts[0].type == 'text'
    assert message_parts[0].data['text'] == 'you are an expert on pangolins'

    context_message_1 = context[1]
    assert context_message_1.role == 'user'

    message_parts = context_message_1.content
    
    assert len(message_parts) == 1
    assert message_parts[0].type == 'text'
    assert message_parts[0].data['text'] == 'pangolins are cool'
    
    context_message_2 = context[2]
    assert context_message_2.role == 'assistant'

    message_parts = context_message_2.content
    
    assert len(message_parts) == 1
    assert message_parts[0].type == 'text'
    assert message_parts[0].data['text'] == 'let me find some pangolin facts for you'

    tool_calls = context_message_2.tool_calls

    assert len(tool_calls) == 1
    assert tool_calls[0].id == 'test id'
    assert tool_calls[0].name == 'test_call'
    assert tool_calls[0].args['test_param'] == 'test_value'
    
    context_message_3 = context[3]
    assert context_message_3.role == 'tool'

    message_parts = context_message_3.content
    
    assert len(message_parts) == 1
    assert message_parts[0].type == 'text'
    assert message_parts[0].data['text'] == 'pangolins are in fact cool'
    assert context_message_3.tool_call_id == 'test id'