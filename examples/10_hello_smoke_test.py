#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from pangolin import cli, AdvancedToolbox, BasicToolbox, AdvancedSkillManager,  SQLiteMemoryManager, smoke_test_runtime
from uuid import uuid4
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
                            # toolbox=AdvancedToolbox()
                            )

cli(session)