#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from typing import Protocol, Iterator, AsyncGenerator, runtime_checkable
from ...messages.api_event import ApiEvent
from ...messages.chat_record import ChatRecord

@runtime_checkable 
class Client(Protocol):
    ''' provides interaction with the api for chat completions. 
        Must accept a list of Pangolin ChatRecords and convert to the expected api format.
        Must return an Iterator of the Pangolin ApiEvent'''
    def get_stream(self, records: list[ChatRecord], tools: list[dict] | None = None) -> Iterator[ApiEvent]: ...
