#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from pangolin_agent.api_providers.open_ai_provider import openai_agent_runtime
#from pangolin_agent import cli # use the built in low dependency cli
from cli import cli # color-coded output cli included in the examples folder (requires colorama and pynput, and contains cli_async and cli_queue as demos for hooking to the runtime output)


#Create a basic instance of AgentRuntime
# use anthropic_agent_runtime if you want to connect to their api
session = openai_agent_runtime(
    url='https://api.openai.com/v1',   
    model='gpt-4o-mini',              
    key='your-key-here')

#Launch the command line interface to interact with the AgentRuntime runtime.
cli(session)