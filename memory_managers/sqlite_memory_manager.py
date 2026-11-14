#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import sqlite3, os, uuid
from datetime import datetime
from uuid import UUID
from pathlib import Path
import logging
from ..core.interfaces.memory_manager import IdTrackedMemoryManger
from ..core.types import ChatSummary
from ..messages import TARecord, user_record

LOGGER = logging.getLogger(__name__)

class SQLiteMemoryManager(IdTrackedMemoryManger):
    '''
    Stores chat histories in a sqlite database by chat id.
    An in-memory list of TARecords is used to maintain what gets provided to AgentRuntime.
    The sqlite database is for persitence after restart.
    '''
    def __init__(self, sqlite_path: str = f'{os.getcwd()}/db', chat_id: UUID =uuid.uuid4(), max_records_to_reload: int = 10):
        LOGGER.info(f'__init__ {sqlite_path} {chat_id} {max_records_to_reload}')
        self.memory: list = []
        self.chat_id: UUID = chat_id
        self.max_records_to_reload: int = max_records_to_reload

        Path(sqlite_path).mkdir(parents=True, exist_ok=True)
        self.db_connection = sqlite3.connect(f'{sqlite_path}/ta_records.db')
        self._verify_tables()
        if self._get_chat_summary():
            LOGGER.info(f'previous session found for {self.chat_id}')
            self._reload()
        else:
            LOGGER.info(f'creating new session history for {self.chat_id}')
            self._set_chat_summary( '', '')

    def _verify_tables(self):
        cursor = self.db_connection.cursor()
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
        self.db_connection.commit()
        cursor.close()
        LOGGER.debug('tables verified')

    def _get_chat_summary(self) -> ChatSummary | None:
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT * FROM chat_summaries WHERE chat_id = ?", (f'{self.chat_id.hex}',))
        r = cursor.fetchone()
        if not r: return None
        return ChatSummary(
            chat_id=UUID(r[0]),
            last_used=datetime.fromisoformat(r[1]),
            name= r[2],
            description=r[3]
        )

    def _set_chat_summary(self, name: str, description: str):
        cursor = self.db_connection.cursor()
        cursor.execute('''
            INSERT INTO chat_summaries (chat_id, last_used, name, description)
            VALUES (?, ?, ?, ?)
        ''', (f'{self.chat_id.hex}', datetime.now().isoformat(), name, description))

        self.db_connection.commit()
        cursor.close()

    def _reload(self):
        self.memory.clear()
        cursor = self.db_connection.cursor()
        cursor.execute('''
            SELECT data FROM chat_records 
            WHERE chat_id = ? 
            ORDER BY dtg DESC 
            LIMIT ?
        ''', (f'{self.chat_id.hex}', self.max_records_to_reload))

        results = cursor.fetchall()
        results.reverse()

        for r in results or []:
            tar = TARecord.from_json(r[0])
            self.memory.append(tar)

        LOGGER.debug(f'history reloaded for session {self.chat_id}')

    def _update_chat_summary_last_used(self):
        cursor = self.db_connection.cursor()
        cursor.execute('''
            UPDATE chat_summaries 
            SET last_used = ?
            WHERE chat_id = ?
        ''', ( datetime.now().isoformat(), f'{self.chat_id.hex}'))

        self.db_connection.commit()
        cursor.close()
        LOGGER.debug(f'last update time updated for session {self.chat_id}')

    def update_chat_summary(self, name: str, description: str):
        cursor = self.db_connection.cursor()
        cursor.execute('''
            UPDATE chat_summaries 
            SET name = ?, description = ?
            WHERE chat_id = ?
        ''', (  name, description, f'{self.chat_id.hex}'))

        self.db_connection.commit()
        cursor.close()

        LOGGER.debug(f'summary updated for session {self.chat_id}')

    def set_id(self, id, max_records_to_reload):
        self.chat_id = id
        self.max_records_to_reload = max_records_to_reload
        self._reload()

    def delete_chat(self):
        cursor = self.db_connection.cursor()
        cursor.execute("DELETE FROM chat_summaries WHERE ichat_id = ?", (self.chat_id,))
        cursor.execute("DELETE FROM chat_records WHERE ichat_id = ?", (self.chat_id,))
        self.db_connection.commit()
        cursor.close()
        LOGGER.info(f'history deleted for sessiion {self.chat_id}')

    def get_context(self) -> list[TARecord]:
        return self.memory

    def add_context(self, message: TARecord):
        self.memory.append(message)
        cursor = self.db_connection.cursor()
        cursor.execute('''
            INSERT INTO chat_records (chat_id, dtg, data)
            VALUES (?, ?, ?)
        ''', (f'{self.chat_id.hex}', datetime.now().isoformat(), message.to_json()))

        self.db_connection.commit()
        cursor.close()

        LOGGER.debug(f'message added to session {self.chat_id} {message}')
        self._update_chat_summary_last_used()

    def trim_context(self):
        LOGGER.debug('trimming context')
        dropped_tool_call_ids: set[str] = set()

        def pop_front():
            popped = self.memory.pop(0)
            if popped.tool_calls:
                dropped_tool_call_ids.update(tc.id for tc in popped.tool_calls)

        pop_front()

        while self.memory and self.memory[0].role != 'user':
            pop_front()

        if dropped_tool_call_ids:
            self.memory = [ m for m in self.memory if m.tool_call_id not in dropped_tool_call_ids]

        if not self.memory or len(self.memory) == 0:
            LOGGER.info('trimming removed the entire history')
            self.memory.append(user_record('run away context trimming, deleted that whole context!'))
