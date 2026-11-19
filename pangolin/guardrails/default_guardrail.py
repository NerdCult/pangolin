#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import logging
from ..core.interfaces import Guardrail
from ..core.types import GuardrailEvent, GuardrailEventResponse

LOGGER = logging.getLogger(__name__)

class DefaultGuardrail(Guardrail):
    def __init__(self):
        pass

    def handle_guardrail_event(self, event: GuardrailEvent) -> GuardrailEventResponse:
        LOGGER.debug(f'guardrail recieved event: {event.to_json()}')
        if event.event_type == 'tool_call':
            return GuardrailEventResponse(event_type='approve')
            
        if event.event_type == 'tool_call_result':
            return GuardrailEventResponse(event_type='approve')
        
        if event.event_type == 'user_input':
            return GuardrailEventResponse(event_type='approve')
        
        if event.event_type == 'assistant_output':
            return GuardrailEventResponse(event_type='approve')
        
        if event.event_type == 'context_size':
            return GuardrailEventResponse(event_type='approve')

        return GuardrailEventResponse(event_type='deny')