from pangolin_agent.api_providers.gemini_provider import gemini_agent_runtime
#from pangolin_agent import cli # use the built in low dependency cli
from cli import cli # color-coded output cli included in the examples folder (requires colorama and pynput, and contains cli_async and cli_queue as demos for hooking to the runtime output)

#Create a basic instance of AgentRuntime
session = gemini_agent_runtime(
    model='gemini-3.1-flash-lite', 
    key='your api key')

#Launch the command line interface to interact with the AgentRuntime runtime. 
cli(session)