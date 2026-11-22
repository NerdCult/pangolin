#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from pangolin.api_providers.open_ai_provider import openai_agent_runtime
from pangolin import SQLiteMemoryManager, AdvancedSkillManager, PangolinToolbox, DefaultGuardrail
from pangolin.utils import copy_built_in_skills, copy_built_in_tools
#from pangolin import cli # use the built in low dependency cli
from cli import cli # color-coded output cli included in the examples folder (requires colorama and pynput, and contains cli_async and cli_queue as demos for hooking to the runtime output)
from uuid import UUID, uuid4

#### ONLY NEEDS TO BE RUN ONCE, OR IF THE COPIES GET DELETED OR ALTERED. ####
from pangolin.utils import copy_built_in_skills, copy_built_in_tools
copy_built_in_tools() # copies the basic built-in tools to current working directory/tools/  use copy_built_in_power_tools for create_tool, write_file, delete_file, and run_sh, review and understand these tools before letting you agent use them
copy_built_in_skills() # copies the built-in skills to current working directory/skills/   (built-in skills are primarily so the agent can help develop against this library)
####

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
    url='https://api.openai.com/v1',   
    model='gpt-4o-mini',              
    key='your-key-here',
    # does the thing system prompts do (tells the agent how to act and behave)
    system_prompt=SYSTEM_PROMPT,

    # writes full history and keeps a configurable size of the conversation in-memory 
    memory_manager=SQLiteMemoryManager(chat_id=CHAT_ID),

    # provides a menu of available skills and guidance on how to load/unload/create them. must be paired with a toolbox that implmenets ToolboxAdvanced
    skill_manager=AdvancedSkillManager(),

    # the default ToolboxAdvanced implementation. can load session aware tools that can affect the runtime and other components.
    toolbox=PangolinToolbox(), # use BasicToolbox() to restrict your agent to web and file browsing or use DefaultGuardrail to block tool creation and file deletes or a custom list of blocked tools.

    # handles hook events for new user message, new agent message w/tool calls, and tool call results. can approve, modify, or deny (deny raises a PangolinError and ends the turn.)
    guardrail=DefaultGuardrail() # blocks a list of tools provided to the constructor. default blocks all 'power tools'
    
    # max_tokens=32_000 # control the max size to send to the api on a given turn (approx)
    # max_rounds=10 # control how many times the agent loop can run per a single user input
    )

#Launch the command line interface to interact with the AgentRuntime runtime. output is color-coded green -> user, red -> agent thinking, yellow -> tool calls, blue -> agent reply
cli(session)
