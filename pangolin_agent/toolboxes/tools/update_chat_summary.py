#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from pangolin_agent.core.interfaces.memory_manager import IdTrackedMemoryManager

SCHEMA = {
    "name": "update_chat_summary",
    "description": "Set the name and description of the current chat. Only works when the memory manager tracks chats by id.",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Short name for this chat."},
            "description": {"type": "string", "description": "One-line description of this chat."},
        },
        "required": ["name", "description"],
    },
}

def make_session_aware_run(session):
    def run(name: str, description: str) -> str:
        try:
            memory = session.memory_manager
            if memory and isinstance(memory, IdTrackedMemoryManager):
                memory.update_chat_summary(name, description)
                return f'chat summary updated: {name}'
            return 'Current memory manager does not implement IdTrackedMemoryManager'
        except Exception as e:
            return f"Couldn't update chat summary: {e}"

    return run
