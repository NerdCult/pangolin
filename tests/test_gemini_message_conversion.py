import pytest, json
from pangolin import GeminiClient
from pangolin.messages import TARecord, Part, ToolCall
from google import genai

@pytest.fixture
def mock_gemini_client():
    return GeminiClient(genai.Client( api_key="dummy"), model_name="dummy")

def test_gemini_message(mock_gemini_client):
    part = Part(type='text', data={'text': 'pangolins are cool'})
    message = TARecord(role='user', content=[part])

    gemini_parts = mock_gemini_client._message_to_gemini(message,[])

    assert len(gemini_parts) == 1
    gem_part = gemini_parts[0]
    assert gem_part.text == 'pangolins are cool'
                  


def test_gemini_messages(mock_gemini_client):
    part = Part(type='text', data={'text': 'pangolins are cool'})
    message = TARecord(role='user', content=[part])

    messages = [ TARecord(role='system', content=[Part(type='text', data={'text': 'you are an expert on pangolins'})]), 
                message,
                TARecord(role='assistant', content=[Part(type='text', data={'text': 'let me find some pangolin facts for you'})],
                         tool_calls=[ToolCall(id='test id', name='test_call', args={'test_param': 'test_value'})]), 
                TARecord(role='tool', content=[Part(type='text', data={'text': 'pangolins are in fact cool'})],
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

    gem_msg_part_0 = gem_msg_0.parts[0]
    assert gem_msg_part_0.text == 'pangolins are cool'

    # test the assitant or 'model' messagw'
    gem_msg_1 = gemini_messages[1]

    assert gem_msg_1.role == 'model'
    assert len(gem_msg_1.parts) == 2

    gem_msg_part_0= gem_msg_1.parts[0]
    assert gem_msg_part_0.text == 'let me find some pangolin facts for you'

    # check the tool call
    gem_tool_call = gem_msg_1.parts[1]
    assert gem_tool_call.function_call.id == 'test id'
    assert gem_tool_call.function_call.name == 'test_call'
    assert gem_tool_call.function_call.args['test_param'] == 'test_value'

    return

    assert gemini_messages[0]['role'] == 'system'

    gemini_message_0 = gemini_messages[0]

    message_part_0 = gemini_message_0['content']
    
    assert len(message_part_0) == 1
    assert 'type' in message_part_0[0].keys()
    assert message_part_0[0]['type'] == 'text'
    
    assert 'text' in message_part_0[0].keys()
    assert message_part_0[0]['text'] == 'you are an expert on pangolins'

    assert gemini_messages[1]['role'] == 'user'

    gemini_message_1 = gemini_messages[1]

    message_part_1 = gemini_message_1['content']
    
    assert len(message_part_1) == 1
    assert 'type' in message_part_1[0].keys()
    assert message_part_1[0]['type'] == 'text'
    
    assert 'text' in message_part_1[0].keys()
    assert message_part_1[0]['text'] == 'pangolins are cool'

    assert gemini_messages[2]['role'] == 'assistant'

    gemini_message_2 = gemini_messages[2]

    message_part_2 = gemini_message_2['content']
    
    assert len(message_part_2) == 1
    assert 'type' in message_part_2[0].keys()
    assert message_part_2[0]['type'] == 'text'
    
    assert 'text' in message_part_2[0].keys()
    assert message_part_2[0]['text'] == 'let me find some pangolin facts for you'

    assert 'tool_calls' in gemini_message_2.keys()
    assert len(gemini_message_2['tool_calls']) == 1

    tool_calls = gemini_message_2['tool_calls']

    assert len(tool_calls) == 1
    assert tool_calls[0]['id'] == 'test id'
    assert tool_calls[0]['type'] == 'function'

    func = tool_calls[0]['function']

    assert func['name'] == 'test_call'
    assert func['arguments'] == json.dumps({'test_param': 'test_value'})


    assert gemini_messages[3]['role'] == 'tool'

    gemini_message_3 = gemini_messages[3]

    message_part_3 = gemini_message_3['content']
    
    assert isinstance(message_part_3, str)
    assert message_part_3 == 'pangolins are in fact cool'
    assert gemini_message_3['tool_call_id'] == 'test id'


    gem_tool_call = gemini_parts[1]
    assert gem_tool_call.function_call.id == 'test id'
    assert gem_tool_call.function_call.name == 'test_call'
    assert gem_tool_call.function_call.args['test_param'] == 'test_value'