import sqlite3
import logging
from contextlib import closing
from pathlib import Path
from typing import Any, List, Dict

logger = logging.getLogger(__name__)


class NotesDatabase:
    def __init__(
        self,
        db_path: str = "~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite",
    ):
        self.db_path = str(Path(db_path).expanduser())
        self._init_database()

    def _init_database(self):
        logger.debug("Initializing database connection")
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                # Verify we can access key Apple Notes tables
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='ZICCLOUDSYNCINGOBJECT'"
                )
                if not cursor.fetchone():
                    raise ValueError(
                        "This doesn't appear to be an Apple Notes database - missing required tables"
                    )
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _execute_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a SQL query and return results as a list of dictionaries"""
        logger.debug(f"Executing query: {query}")
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                with closing(conn.cursor()) as cursor:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)

                    results = [dict(row) for row in cursor.fetchall()]
                    logger.debug(f"Query returned {len(results)} rows")
                    return results
        except sqlite3.Error as e:
            logger.error(f"Database error executing query: {e}")
            raise

    def get_all_notes(self) -> List[Dict[str, Any]]:
        """Retrieve all notes with their metadata"""
        query = """
        SELECT
            'x-coredata://' || zmd.z_uuid || '/ICNote/p' || note.z_pk AS id,
            note.z_pk AS pk,
            note.ztitle1 AS title,
            folder.ztitle2 AS folder,
            datetime(note.zmodificationdate1 + 978307200, 'unixepoch') AS modifiedAt,
            note.zsnippet AS snippet,
            acc.zname AS account,
            note.zidentifier AS UUID,
            (note.zispasswordprotected = 1) as locked,
            (note.zispinned = 1) as pinned,
            (note.zhaschecklist = 1) as checklist,
            (note.zhaschecklistinprogress = 1) as checklistInProgress
        FROM 
            ziccloudsyncingobject AS note
        INNER JOIN ziccloudsyncingobject AS folder 
            ON note.zfolder = folder.z_pk
        LEFT JOIN ziccloudsyncingobject AS acc 
            ON note.zaccount4 = acc.z_pk
        LEFT JOIN z_metadata AS zmd ON 1=1
        WHERE
            note.ztitle1 IS NOT NULL AND
            note.zmodificationdate1 IS NOT NULL AND
            note.z_pk IS NOT NULL AND
            note.zmarkedfordeletion != 1 AND
            folder.zmarkedfordeletion != 1
        ORDER BY
            note.zmodificationdate1 DESC
        """
        results = self._execute_query(query)

        return results

    def get_note_by_title(self, title: str) -> Dict[str, Any] | None:
        """Retrieve a specific note by its title including content and metadata"""
        query = """
        SELECT
            'x-coredata://' || zmd.z_uuid || '/ICNote/p' || note.z_pk AS id,
            note.z_pk AS pk,
            note.ztitle1 AS title,
            folder.ztitle2 AS folder,
            datetime(note.zmodificationdate1 + 978307200, 'unixepoch') AS modifiedAt,
            datetime(note.zcreationdate1 + 978307200, 'unixepoch') AS createdAt,
            note.zsnippet AS snippet,
            notedata.zdata AS content,
            acc.zname AS account,
            note.zidentifier AS UUID,
            (note.zispasswordprotected = 1) as locked,
            (note.zispinned = 1) as pinned,
            (note.zhaschecklist = 1) as checklist,
            (note.zhaschecklistinprogress = 1) as checklistInProgress
        FROM 
            ziccloudsyncingobject AS note
        INNER JOIN ziccloudsyncingobject AS folder 
            ON note.zfolder = folder.z_pk
        LEFT JOIN ziccloudsyncingobject AS acc 
            ON note.zaccount4 = acc.z_pk
        LEFT JOIN zicnotedata AS notedata
            ON note.znotedata = notedata.z_pk
        LEFT JOIN z_metadata AS zmd ON 1=1
        WHERE
            note.ztitle1 = ? AND
            note.zmarkedfordeletion != 1 AND
            folder.zmarkedfordeletion != 1
        LIMIT 1
        """
        results = self._execute_query(query, (title,))
        return results[0] if results else None

    def search_notes(self, query_text: str) -> List[Dict[str, Any]]:
        """Search notes by title, content, or snippet with ranking by relevance"""
        query = """
        SELECT
            'x-coredata://' || zmd.z_uuid || '/ICNote/p' || note.z_pk AS id,
            note.z_pk AS pk,
            note.ztitle1 AS title,
            folder.ztitle2 AS folder,
            datetime(note.zmodificationdate1 + 978307200, 'unixepoch') AS modifiedAt,
            datetime(note.zcreationdate1 + 978307200, 'unixepoch') AS createdAt,
            note.zsnippet AS snippet,
            notedata.zdata AS content,
            acc.zname AS account,
            note.zidentifier AS UUID,
            (note.zispasswordprotected = 1) as locked,
            (note.zispinned = 1) as pinned,
            (note.zhaschecklist = 1) as checklist,
            (note.zhaschecklistinprogress = 1) as checklistInProgress,
            CASE
                WHEN note.ztitle1 LIKE ? THEN 3
                WHEN note.zsnippet LIKE ? THEN 2
                WHEN notedata.zdata LIKE ? THEN 1
                ELSE 0
            END as relevance
        FROM 
            ziccloudsyncingobject AS note
        INNER JOIN ziccloudsyncingobject AS folder 
            ON note.zfolder = folder.z_pk
        LEFT JOIN ziccloudsyncingobject AS acc 
            ON note.zaccount4 = acc.z_pk
        LEFT JOIN zicnotedata AS notedata
            ON note.znotedata = notedata.z_pk
        LEFT JOIN z_metadata AS zmd ON 1=1
        WHERE
            note.zmarkedfordeletion != 1 AND
            folder.zmarkedfordeletion != 1 AND
            (note.ztitle1 LIKE ? OR 
            note.zsnippet LIKE ? OR 
            notedata.zdata LIKE ?)
        ORDER BY 
            relevance DESC,
            note.zmodificationdate1 DESC
        """
        search_pattern = f"%{query_text}%"
        # We need 6 parameters because the pattern is used twice in the query
        # 3 times for relevance scoring and 3 times for WHERE clause
        params = (search_pattern,) * 6

        return self._execute_query(query, params)

    def get_note_content(self, note_id: str) -> Dict[str, Any] | None:
        """
        Retrieve full note content and metadata by note ID
        This note ID is provided by the resource URI inside Claude
        """
        query = """
        SELECT
            'x-coredata://' || zmd.z_uuid || '/ICNote/p' || note.z_pk AS id,
            note.z_pk AS pk,
            note.ztitle1 AS title,
            folder.ztitle2 AS folder,
            datetime(note.zmodificationdate1 + 978307200, 'unixepoch') AS modifiedAt,
            datetime(note.zcreationdate1 + 978307200, 'unixepoch') AS createdAt,
            note.zsnippet AS snippet,
            notedata.zdata AS content,
            acc.zname AS account,
            note.zidentifier AS UUID,
            (note.zispasswordprotected = 1) as locked,
            (note.zispinned = 1) as pinned
        FROM 
            ziccloudsyncingobject AS note
        INNER JOIN ziccloudsyncingobject AS folder 
            ON note.zfolder = folder.z_pk
        LEFT JOIN ziccloudsyncingobject AS acc 
            ON note.zaccount4 = acc.z_pk
        LEFT JOIN zicnotedata AS notedata
            ON note.znotedata = notedata.z_pk
        LEFT JOIN z_metadata AS zmd ON 1=1
        WHERE
            note.z_pk = ? AND
            note.zmarkedfordeletion != 1 AND
            folder.zmarkedfordeletion != 1
        LIMIT 1
        """

        results = self._execute_query(query, (note_id,))
        return results[0] if results else None
