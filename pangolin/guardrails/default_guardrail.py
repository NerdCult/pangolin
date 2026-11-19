#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import logging
from ..core.interfaces import Guardrail
from ..core.types import GuardrailEvent, GuardrailEventResponse
from ..messages import ToolCallResult, TARecord, Part

LOGGER = logging.getLogger(__name__)

class DefaultGuardrail(Guardrail):
    def __init__(self, blocked_tools: list[str] | None = None):
        self.blocked_tools = blocked_tools or ['create_tool', 'delete_file']

    def handle_guardrail_event(self, event: GuardrailEvent) -> GuardrailEventResponse:
        LOGGER.debug(f'guardrail recieved event: {event.to_json()}')
        if event.event_type == 'tool_call_result':
            return GuardrailEventResponse(event_type='approve')
        
        if event.event_type == 'user_input':
            return GuardrailEventResponse(event_type='approve')
        
        if event.event_type == 'assistant_output':
            if event.ta_record.tool_calls:
                blocked_tool_call_ids = []
                for tc in event.ta_record.tool_calls:
                    if tc.name in self.blocked_tools:
                        blocked_tool_call_ids.append(tc.id)

                ger = GuardrailEventResponse(
                    event_type='modify',
                    reason='tool blocked by the current runtime guardrail policy',
                    ta_record=event.ta_record,
                    rejected_tool_call_ids=blocked_tool_call_ids if len(blocked_tool_call_ids) > 0 else None
                )
                return ger
            return GuardrailEventResponse(event_type='approve')

        return GuardrailEventResponse(event_type='deny')