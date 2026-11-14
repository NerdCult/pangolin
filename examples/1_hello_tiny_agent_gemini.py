from tinyagent import gemini_agent_runtime, cli, AdvancedToolbox, BasicToolbox, AdvancedSkillManager, SimpleSkillManager, SQLiteMemoryManager
from uuid import UUID, uuid4
import logging

MODEL, KEY = 'gemini-3.1-flash-lite', 'your key' #google provides a free tier API token

CHAT_ID = uuid4()

print (CHAT_ID)

session = gemini_agent_runtime( 
                               model=MODEL, 
                               key=KEY)

cli(session)