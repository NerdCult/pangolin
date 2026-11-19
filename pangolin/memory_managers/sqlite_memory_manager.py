#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import sqlite3, os, uuid
from datetime import datetime
from uuid import UUID
from pathlib import Path
import logging
from ..core.interfaces.memory_manager import IdTrackedMemoryManger
from ..core.exceptions import PangolinError
from ..core.types import ChatSummary
from ..messages import TARecord, user_record

LOGGER = logging.getLogger(__name__)
DEFAULT_MAX_TO_RELOAD = 25

class SQLiteMemoryManager(IdTrackedMemoryManger):
    '''
    Stores chat histories in a sqlite database by chat id.
    An in-memory list of TARecords is used to maintain what gets provided to AgentRuntime.
    The sqlite database is for persitence after restart.
    '''
    def __init__(self, sqlite_folder: str = f'{os.getcwd()}/db', chat_id: UUID | None = None, max_records_to_reload: int = DEFAULT_MAX_TO_RELOAD):
        '''
        sqlite_path: the folder where the database should be created. default is current working directory /db. the file created is ta_records.db
        chat_id: can be provided to resume a session or one is created.
        max_records_to_reload: the maximum records to reload when resuming a session
        '''
        LOGGER.info(f'__init__ {sqlite_folder} {chat_id} {max_records_to_reload}')
        self.memory: list[TARecord] = []
        self.chat_id: UUID = chat_id or uuid.uuid4()
        self.max_records_to_reload: int = max_records_to_reload

        Path(sqlite_folder).mkdir(parents=True, exist_ok=True)
        self.db_path = f'{sqlite_folder}/ta_records.db'
        try:
            self._verify_tables() # verify the required tables exist
            if self._get_chat_summary(): # check for an existing chat history for the provided chat_id
                LOGGER.info(f'previous session found for {self.chat_id}')
                self._reload()
                if len(self.memory) > 0 and self.memory[0].role != 'user':      # APIs like the first chat  record to be a user message so trim the reloaded context
                    self.trim_context() 
            else: # create a new chat history
                LOGGER.info(f'creating new session history for {self.chat_id}')
                self._set_chat_summary( '', '') # creates a session entry in the chat_summaries table with empty name and description
        except Exception as e:
            raise PangolinError(f'SQLiteMemoryManager failed to connect to database {e}')

    # verify the required tables, create if missing
    def _verify_tables(self):
        db_connection = sqlite3.connect(self.db_path)
        cursor = db_connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_summaries (
                chat_id TEXT UNIQUE,
                last_used DATE,
                name TEXT,
                description TEXT
            );
            ''')

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS chat_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT,
                dtg DATE,
                data JSON
            );
        ''')
        db_connection.commit()
        cursor.close()
        LOGGER.debug('tables verified')

    # gets the chat summary for the selected chat_id if it exists
    def _get_chat_summary(self) -> ChatSummary | None:
        db_connection = sqlite3.connect(self.db_path)
        cursor = db_connection.cursor()
        cursor.execute("SELECT * FROM chat_summaries WHERE chat_id = ?", (f'{self.chat_id.hex}',))
        r = cursor.fetchone()
        if not r: return None
        return ChatSummary(
            chat_id=UUID(r[0]),
            last_used=datetime.fromisoformat(r[1]),
            name= r[2],
            description=r[3]
        )

    # Creates the chat_summaries entry for a new chat_id
    def _set_chat_summary(self, name: str, description: str):
        db_connection = sqlite3.connect(self.db_path)
        cursor = db_connection.cursor()
        cursor.execute('''
            INSERT INTO chat_summaries (chat_id, last_used, name, description)
            VALUES (?, ?, ?, ?)
        ''', (f'{self.chat_id.hex}', datetime.now().isoformat(), name, description))

        db_connection.commit()
        cursor.close()

    # load an existing chat history based on the chat_id
    def _reload(self,):
        self.memory.clear()
        db_connection = sqlite3.connect(self.db_path)
        cursor = db_connection.cursor()
        cursor.execute('''
            SELECT data FROM chat_records 
            WHERE chat_id = ? 
            ORDER BY dtg DESC 
            LIMIT ?
        ''', (f'{self.chat_id.hex}', self.max_records_to_reload))

        results = cursor.fetchall()
        results.reverse() # reverse the list to get it sorted asending by time

        # add the records to memory
        for r in results or []:
            self.memory.append(TARecord.from_json(r[0]))

        LOGGER.debug(f'{len(self.memory)} records reloaded for session {self.chat_id}')

    # update current chat summary with the last time it was used
    def _update_chat_summary_last_used(self):
        db_connection = sqlite3.connect(self.db_path)
        cursor = db_connection.cursor()
        cursor.execute('''
            UPDATE chat_summaries 
            SET last_used = ?
            WHERE chat_id = ?
        ''', ( datetime.now().isoformat(), f'{self.chat_id.hex}'))

        db_connection.commit()
        cursor.close()
        LOGGER.debug(f'last update time updated for session {self.chat_id}')

    # update the chat summary with a name and description could be called by a session aware tool
    def update_chat_summary(self, name: str, description: str):
        db_connection = sqlite3.connect(self.db_path)
        cursor = db_connection.cursor()
        cursor.execute('''
            UPDATE chat_summaries 
            SET name = ?, description = ?
            WHERE chat_id = ?
        ''', (  name, description, f'{self.chat_id.hex}'))

        db_connection.commit()
        cursor.close()

        LOGGER.debug(f'summary updated for session {self.chat_id}')

    def get_context(self) -> list[TARecord]:
        return self.memory

    # append a TARecord to the history both in memory and in the database
    def add_context(self, message: TARecord):
        self.memory.append(message)
        db_connection = sqlite3.connect(self.db_path)
        cursor = db_connection.cursor()
        cursor.execute('''
            INSERT INTO chat_records (chat_id, dtg, data)
            VALUES (?, ?, ?)
        ''', (f'{self.chat_id.hex}', datetime.now().isoformat(), message.to_json()))

        db_connection.commit()
        cursor.close()

        LOGGER.debug(f'message added to session {self.chat_id} {message}')
        self._update_chat_summary_last_used()

    # remove the oldest record from memory and return and tool call ids popped
    def pop_front(self) -> list[str]:
        popped = self.memory.pop(0)
        return [tc.id for tc in popped.tool_calls] if popped.tool_calls else []

    # trim the in-memory history to the first user message
    def _trim_context_to_first_user(self) -> list[str]:
        temp: set[str] = set()
        while self.memory and self.memory[0].role != 'user':
            LOGGER.debug('non user record trimmed')
            temp.update(self.pop_front()) 
        return temp

    # trim the context 
    def trim_context(self):
        LOGGER.debug('trimming context')
        dropped_tool_call_ids: set[str] = set()

        dropped_tool_call_ids.update(self.pop_front() )

        dropped_tool_call_ids.update(self._trim_context_to_first_user())

        if dropped_tool_call_ids:
            self.memory = [ m for m in self.memory if m.tool_call_id not in dropped_tool_call_ids]

        if not self.memory or len(self.memory) == 0:
            LOGGER.error('trimming removed the entire history')
            raise PangolinError('SQLiteMemoryManager.trim_context() dropped all in memory chat history. increase max_tokens in AgentRuntime or reduce system prompt, skills, and or available tools.')
