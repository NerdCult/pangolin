#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import pytest, json
from pangolin.api_providers.open_ai_provider import OpenAIClient
from pangolin.messages import ChatRecord, Part, ToolCall
from openai import OpenAI

@pytest.fixture
def mock_openai_client():
    return OpenAIClient(OpenAI(base_url="dummy", api_key="dummy"), model_name="dummy")

def test_openai_message(mock_openai_client):
    part = Part(type='text', data={'text': 'pangolins are cool'})

    openai_part = mock_openai_client._part_to_openai(part)

    assert 'type' in openai_part.keys()
    assert openai_part['type'] == 'text'

    assert 'text' in openai_part.keys()
    assert openai_part['text'] == 'pangolins are cool'

    message = ChatRecord(role='user', content=[part])

    openai_message = mock_openai_client._record_to_openai(message)

    assert 'role' in openai_message.keys()
    assert openai_message['role'] == 'user'

    assert 'content' in openai_message.keys()

    message_part = openai_message['content']

    assert len(message_part) == 1
    assert 'type' in message_part[0].keys()
    assert message_part[0]['type'] == 'text'

    assert 'text' in message_part[0].keys()
    assert message_part[0]['text'] == 'pangolins are cool'


def test_openai_messages(mock_openai_client):
    part = Part(type='text', data={'text': 'pangolins are cool'})
    message = ChatRecord(role='user', content=[part])

    messages = [ ChatRecord(role='system', content=[Part(type='text', data={'text': 'you are an expert on pangolins'})]), 
                message,
                ChatRecord(role='assistant', content=[Part(type='text', data={'text': 'let me find some pangolin facts for you'})],
                         tool_calls=[ToolCall(id='test id', name='test_call', args={'test_param': 'test_value'})]), 
                ChatRecord(role='tool', content=[Part(type='text', data={'text': 'pangolins are in fact cool'})],
                         tool_call_id='test id'), 
                ]

    openai_messages = mock_openai_client._records_to_openai(messages)

    assert len(openai_messages) == 4

    assert openai_messages[0]['role'] == 'system'

    openai_message_0 = openai_messages[0]

    message_part_0 = openai_message_0['content']
    
    assert len(message_part_0) == 1
    assert 'type' in message_part_0[0].keys()
    assert message_part_0[0]['type'] == 'text'
    
    assert 'text' in message_part_0[0].keys()
    assert message_part_0[0]['text'] == 'you are an expert on pangolins'

    assert openai_messages[1]['role'] == 'user'

    openai_message_1 = openai_messages[1]

    message_part_1 = openai_message_1['content']
    
    assert len(message_part_1) == 1
    assert 'type' in message_part_1[0].keys()
    assert message_part_1[0]['type'] == 'text'
    
    assert 'text' in message_part_1[0].keys()
    assert message_part_1[0]['text'] == 'pangolins are cool'

    assert openai_messages[2]['role'] == 'assistant'

    openai_message_2 = openai_messages[2]

    message_part_2 = openai_message_2['content']
    
    assert len(message_part_2) == 1
    assert 'type' in message_part_2[0].keys()
    assert message_part_2[0]['type'] == 'text'
    
    assert 'text' in message_part_2[0].keys()
    assert message_part_2[0]['text'] == 'let me find some pangolin facts for you'

    assert 'tool_calls' in openai_message_2.keys()
    assert len(openai_message_2['tool_calls']) == 1

    tool_calls = openai_message_2['tool_calls']

    assert len(tool_calls) == 1
    assert tool_calls[0]['id'] == 'test id'
    assert tool_calls[0]['type'] == 'function'

    func = tool_calls[0]['function']

    assert func['name'] == 'test_call'
    assert func['arguments'] == json.dumps({'test_param': 'test_value'})


    assert openai_messages[3]['role'] == 'tool'

    openai_message_3 = openai_messages[3]

    message_part_3 = openai_message_3['content']
    
    assert isinstance(message_part_3, str)
    assert message_part_3 == 'pangolins are in fact cool'
    assert openai_message_3['tool_call_id'] == 'test id'

