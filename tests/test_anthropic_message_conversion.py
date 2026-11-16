import pytest
from anthropic import Anthropic
from pangolin import AnthropicClient
from pangolin.messages import TARecord, Part, ToolCall

@pytest.fixture
def mock_anthropic_client():
    return AnthropicClient(Anthropic(base_url="dummy", api_key="dummy"), model_name="claude-3-sonnet")

def test_anthropic_message(mock_anthropic_client):
    part = Part(type='text', data={'text': 'pangolins are cool'})

    anth_part = mock_anthropic_client._part_to_anthropic(part)

    assert 'type' in anth_part.keys()
    assert anth_part['type'] == 'text'

    assert 'text' in anth_part.keys()
    assert anth_part['text'] == 'pangolins are cool'

    message = TARecord(role='user', content=[part])

    anth_message = mock_anthropic_client._message_to_anthropic(message)

    assert 'role' in anth_message.keys()
    assert anth_message['role'] == 'user'

    assert 'content' in anth_message.keys()

    message_part = anth_message['content']

    assert len(message_part) == 1
    assert 'type' in message_part[0].keys()
    assert message_part[0]['type'] == 'text'

    assert 'text' in message_part[0].keys()
    assert message_part[0]['text'] == 'pangolins are cool'


def test_anthropic_messages(mock_anthropic_client):
    part = Part(type='text', data={'text': 'pangolins are cool'})

    message = TARecord(role='user', content=[part])
    
    messages = [ TARecord(role='system', content=[Part(type='text', data={'text': 'you are an expert on pangolins'})]), 
                message,
                TARecord(role='assistant', content=[Part(type='text', data={'text': 'let me find some pangolin facts for you'})],
                         tool_calls=[ToolCall(id='test id', name='test_call', args={'test_param': 'test_value'})]), 
                TARecord(role='tool', content=[Part(type='text', data={'text': 'pangolins are in fact cool'})],
                         tool_call_id='test id'), 
                ]

    system, anth_messages = mock_anthropic_client._messages_to_anthropic(messages)

    assert isinstance(system, str)
    assert system == 'you are an expert on pangolins'
    assert len(anth_messages) == 3

    assert anth_messages[0]['role'] == 'user'

    anth_message_0 = anth_messages[0]

    message_part_0 = anth_message_0['content']
    
    assert len(message_part_0) == 1
    assert 'type' in message_part_0[0].keys()
    assert message_part_0[0]['type'] == 'text'
    
    assert 'text' in message_part_0[0].keys()
    assert message_part_0[0]['text'] == 'pangolins are cool'

    # tool call and tool result compressed as one user message with two parts
    assert anth_messages[1]['role'] == 'assistant'

    anth_message_1 = anth_messages[1]

    message_part_1 = anth_message_1['content']
    
    assert len(message_part_1) == 2 #tool call and tool result paired as 
    assert 'type' in message_part_1[0].keys()
    assert message_part_1[0]['type'] == 'text'
    
    assert 'text' in message_part_1[0].keys()
    assert message_part_1[0]['text'] == 'let me find some pangolin facts for you'

    assert message_part_1[1]['type'] == 'tool_use'
    assert message_part_1[1]['id'] == 'test id'
    assert message_part_1[1]['name'] == 'test_call'
    assert message_part_1[1]['input']['test_param'] == 'test_value'

    assert anth_messages[2]['role'] == 'user'

    anth_message_0 = anth_messages[0]

    message_part_0 = anth_message_0['content']
    
    assert len(message_part_0) == 1
    assert 'type' in message_part_0[0].keys()
    assert message_part_0[0]['type'] == 'text'
    
    assert 'text' in message_part_0[0].keys()
    assert message_part_0[0]['text'] == 'pangolins are cool'

