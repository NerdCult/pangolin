#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import pytest
from pangolin import GeminiClient
from pangolin.messages import ChatRecord, Part, ToolCall
from google import genai

@pytest.fixture
def mock_gemini_client():
    return GeminiClient(genai.Client( api_key="dummy"), model_name="dummy")

def test_gemini_message(mock_gemini_client):
    part = Part(type='text', data={'text': 'pangolins are cool'})
    message = ChatRecord(role='user', content=[part])

    gemini_parts = mock_gemini_client._message_to_gemini(message,[])

    assert len(gemini_parts) == 1
    gem_part = gemini_parts[0]
    assert gem_part.text == 'pangolins are cool'
                  


def test_gemini_messages(mock_gemini_client):
    part = Part(type='text', data={'text': 'pangolins are cool'})
    message = ChatRecord(role='user', content=[part])

    messages = [ ChatRecord(role='system', content=[Part(type='text', data={'text': 'you are an expert on pangolins'})]), 
                message,
                ChatRecord(role='assistant', content=[Part(type='text', data={'text': 'let me find some pangolin facts for you'})],
                         tool_calls=[ToolCall(id='test id', name='test_call', args={'test_param': 'test_value'})]), 
                ChatRecord(role='tool', content=[Part(type='text', data={'text': 'pangolins are in fact cool'})],
                         tool_call_id='test id'), 
                ]

    system, gemini_messages = mock_gemini_client._messages_to_gemini(messages)

    assert isinstance(system, str)
    assert system == 'you are an expert on pangolins'

    assert len(gemini_messages) == 3
    # test the user message
    gem_msg_0 = gemini_messages[0]

    assert gem_msg_0.role == 'user'
    assert len(gem_msg_0.parts) == 1

    gem_msg_part_0_0 = gem_msg_0.parts[0]
    assert gem_msg_part_0_0.text == 'pangolins are cool'

    # test the assitant or 'model' messagw'
    gem_msg_1 = gemini_messages[1]

    assert gem_msg_1.role == 'model'
    assert len(gem_msg_1.parts) == 2

    gem_msg_part_1_0= gem_msg_1.parts[0]
    assert gem_msg_part_1_0.text == 'let me find some pangolin facts for you'

    # check the tool call
    gem_tool_call = gem_msg_1.parts[1]
    assert gem_tool_call.function_call.id == 'test id'
    assert gem_tool_call.function_call.name == 'test_call'
    assert gem_tool_call.function_call.args['test_param'] == 'test_value'

    #test the tool response which shows as a user message
    gem_msg_2 = gemini_messages[2]

    assert gem_msg_2.role == 'user'
    assert len(gem_msg_2.parts) == 1

    gem_msg_part_2_0 = gem_msg_2.parts[0]
    response = gem_msg_part_2_0.function_response
    assert response.id == 'test id'
    assert response.name == 'test_call'
    assert response.response['result'] == 'pangolins are in fact cool'
