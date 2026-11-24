#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from typing import Protocol, runtime_checkable
from ..types import GuardrailEventResponse, GuardrailEvent

@runtime_checkable
class Guardrail(Protocol):
    def handle_guardrail_event(self, event: GuardrailEvent) -> GuardrailEventResponse: ...

