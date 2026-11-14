#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from google import genai
import logging
from typing import Iterator
from ..core.interfaces import Provider, Client
from ..messages import TARecord, Part, ApiEvent, ToolCall

LOGGER = logging.getLogger(__name__)

class GeminiClient(Client):
    def __init__(self, client: genai.Client, model_name: str):
        self.client = client
        self.model_name = model_name
    
    def _convert_tools(self, tools: list[dict] | None):
        if not tools:
            return None
        # Gemini uses function_declarations in tools dict
        return {"function_declarations": [t["function"] for t in tools]}  # adjust per your toolbox schemas
    
    def _part_to_gemini(self, part: Part):
        # Map your Part to Gemini content (text, inline_data for images, etc.)
        if part.type == "text":
            return part.data.get("text", "")
        # Add image/audio handling as needed
        return part.data

    def _message_to_gemini(self, message: TARecord):
        record_type = message.content[0].type
        text= message.content[0].data['text']
        return {'text' : record_type, 'text': text}
    

    def _messages_to_gemini(self, messages: list[TARecord]):
        gemini_messages = []
        for record in messages:
            gemini_messages.append(self._message_to_gemini(record))
        return gemini_messages
    
    def get_stream(self, messages: list[TARecord], tools: list[dict] | None = None) -> Iterator[ApiEvent]:
        # Convert messages to Gemini history format (system prompt separate, alternating user/model)
        # ... (implement conversion; Gemini history is list of Content)
        #gemini_tools = self._convert_tools(tools)
        gemini_messages = self._messages_to_gemini(messages)
        stream = self.client.interactions.create(
            model=self.model_name,
            input=[{'type': 'text', 'text' :"hello"}],
            stream=True
        )

        for event in stream:
            if event.event_type == "step.delta":
                if event.delta.type == "text":
                    yield ApiEvent(event_type="replying", content=event.delta.text, raw=event)

class GeminiProvider(Provider):
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
    
    def list_models(self):
        return [m.name for m in self.client.models.list() if "image" not in m.name]
    
    def make_client(self, model_name: str):
        return GeminiClient(self.client, model_name)