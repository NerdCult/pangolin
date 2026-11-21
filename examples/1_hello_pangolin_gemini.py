from pangolin.api_providers.gemini_provider import gemini_agent_runtime
#from pangolin import cli # uses the built in low dependency cli
from cli import cli # more the robust cli included in the examples folder (requires colorama and pynput, and contains cli_async and cli_queue as demos for hooking to the runtime output)

MODEL, KEY = 'gemini-3.1-flash-lite', 'your key' #google provides a free tier API token

#Create a basic instance of AgentRuntime
session = gemini_agent_runtime(model=MODEL, key=KEY)

#Launch the command line interface to interact with the AgentRuntime runtime. output is color-coded green -> user, red -> agent thinking, yellow -> tool calls, blue -> agent reply
cli(session)