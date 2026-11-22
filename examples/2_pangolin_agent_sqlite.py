#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from pangolin.api_providers.open_ai_provider import openai_agent_runtime
from pangolin.memory_managers.sqlite_memory_manager import SQLiteMemoryManager
#from pangolin import cli # uses the built in low dependency cli
from cli import cli # more the robust cli included in the examples folder (requires colorama and pynput, and contains cli_async and cli_queue as demos for hooking to the runtime output)
from uuid import UUID, uuid4

#configure your connection

URL = 'https://api.openai.com/v1'   # or your preferred endpoint
MODEL = 'gpt-4o-mini'               # or whatever you prefer
KEY = 'your-key-here'

# configure your system prompt
SYSTEM_PROMPT = 'You are Friday. A helpful, however snarky and sarcastic, assistant. Provide quick brief answers unless a longer explaination is specifically warranted. If a longer explaination is warranted, open with a TL;DR summary, sticking to the helpful however snarky and saracastic persona. Following the TL;DR provide the complete answer in a direct, state the facts manner.'

CHAT_ID = uuid4() #generate random Chat Id

#CHAT_ID = UUID('12345678-1234-5678-1234-567812345679') # manually set a Chat Id to resume a previous chat.

print (CHAT_ID)

#Create a basic instance of AgentRuntime
# use anthropic_agent_runtime if you want to connect to their api
session = openai_agent_runtime(
    url=URL, 
    model=MODEL, 
    key=KEY,
    # does the thing system prompts do (tells the agent how to act and behave)
    system_prompt=SYSTEM_PROMPT,
    # writes full history and keeps a configurable size of the conversation in-memory 
    memory_manager=SQLiteMemoryManager(chat_id=CHAT_ID)
    )

#Launch the command line interface to interact with the AgentRuntime runtime. output is color-coded green -> user, red -> agent thinking, yellow -> tool calls, blue -> agent reply
cli(session)