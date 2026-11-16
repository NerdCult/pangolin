from dataclasses import dataclass
from datetime import date
from uuid import UUID

@dataclass
class ChatSummary():
    chat_id: UUID
    last_used: date
    name: str | None
    description: str | None
