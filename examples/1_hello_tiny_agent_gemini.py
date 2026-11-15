from tinyagent import gemini_agent_runtime, cli, AdvancedToolbox, BasicToolbox, AdvancedSkillManager, SimpleSkillManager, SQLiteMemoryManager
from uuid import UUID, uuid4
import logging

MODEL, KEY = 'gemini-3.1-flash-lite', 'your key' #google provides a free tier API token

CHAT_ID = uuid4()

print (CHAT_ID)

#Create a basic instance of AgentRuntime
session = gemini_agent_runtime( 
                               model=MODEL, 
                               key=KEY)

#Launch the command line interface to interact with the AgentRuntime runtime. output is color-coded green -> user, red -> agent thinking, yellow -> tool calls, blue -> agent reply
cli(session)