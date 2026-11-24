#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

#### USE THE SMOKE TEST RUNTIME TO TEST FUNCTIONALITY ESPECIALLY WHEN DEVELOPING NEW NON-CLIENT COMPONENTS (SKILLS, MEMORY, TOOLS, GUARDRAILS)
# smoke_test_runtime can take a set of scripted ApiEvents. This allows testing and development for other components without requiring the cost of connecting to an LLM API.
from pangolin_agent.api_providers.smoke_test_client import smoke_test_runtime
from pangolin_agent import SQLiteMemoryManager, AdvancedSkillManager, PangolinToolbox, DefaultGuardrail
from pangolin_agent.utils import copy_built_in_skills, copy_built_in_tools
#from pangolin_agent import cli # uses the built in low dependency cli
from cli import cli # more the robust cli included in the examples folder (requires colorama and pynput, and contains cli_async and cli_queue as demos for hooking to the runtime output)
from uuid import UUID, uuid4
import logging

logging.basicConfig(
    filename='test.log',
    level=logging.INFO,        # capture everything
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    filemode='w'                # 'a' to append instead of overwrite
)

SYSTEM_PROMPT = 'short test prompt'

CHAT_ID = uuid4()

session = smoke_test_runtime(
                            system_prompt=SYSTEM_PROMPT,
                            # memory_manager=SQLiteMemoryManager(chat_id=CHAT_ID),
                            # skill_manager=AdvancedSkillManager(), 
                            # toolbox=PangolinToolbox()
                            )

cli(session)