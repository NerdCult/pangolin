#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from typing import Protocol, Iterator
from ...messages import TARecord, AgentMessage

class AgentRuntime(Protocol):
    '''
    The central orchestration class and entry point for running inference.
    manages the ApiAggregator, SkillsManager, Toolbox, and Memory Manager
    routes steps between the different components.
    '''
    def handle_user_message(self, message: TARecord) -> Iterator[AgentMessage]: ...