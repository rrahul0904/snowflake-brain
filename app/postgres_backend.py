from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator

from psycopg import errors, sql
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import (
    BRAIN_DB,
    DATABASE_SCHEMA,
    DATABASE_URL,
    DB_POOL_MAX_SIZE,
    DB_POOL_MIN_SIZE,
    DB_POOL_TIMEOUT_SECONDS,
    POSTGRES_TEST_ISOLATION,
    POSTGRES_TEST_SCHEMA_PREFIX,
    ROOT_DIR,
)


GLOBAL_WRITE_LOCK = 7_542_181_501
MIGRATION_LOCK = 7_542_181_502
_SERIAL_ID_TABLES = {
    "candidate_accounts",
    "candidate_sessions",
    "membership_events",
    "candidate_memberships",
    "candidate_bookmarks",
    "candidate_notes",
    "question_attempts",
    "exam_sessions",
    "exam_session_answers",
    "question_bank_imports",
    "candidate_question_history",
    "candidate_exam_pack_sets",
    "bookmarks",
    "notes",
    "learning_events",
    "candidate_identities",
    "billing_customers",
    "billing_checkout_sessions",
    "billing_subscriptions",
    "billing_purchases",
    "billing_events",
    "membership_audit_log",
    "question_versions",
    "question_bank_releases",
    "question_bank_release_events",
    "exam_entitlement_reservations",
    "feedback_submissions",
}
_REPLACE_CONFLICT_TARGETS: dict[str, tuple[str, ...]] = {
    "pending_identity_links": ("token_hash",),
    "oauth_login_flows": ("state_hash",),
}
_POOL: ConnectionPool | None = None
_POOL_LOCK = threading.RLock()
_SCHEMA_LOCK = threading.RLock()
_READY_SCHEMAS: set[str] = set()


def is_postgres() -> bool:
    return bool(DATABASE_URL) and DATABASE_URL.lower().startswith(("postgresql://", "postgres://"))


def _safe_identifier(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", value or "")
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"db_{cleaned}"
    return cleaned[:63]


def current_schema_name() -> str:
    if POSTGRES_TEST_ISOLATION:
        seed = f"{BRAIN_DB}:{os.getpid()}".encode("utf-8")
        suffix = hashlib.sha1(seed).hexdigest()[:12]
        return _safe_identifier(f"{POSTGRES_TEST_SCHEMA_PREFIX}_{suffix}")
    return _safe_identifier(DATABASE_SCHEMA)


def _pool() -> ConnectionPool:
    global _POOL
    if _POOL is not None:
        return _POOL
    if not is_postgres():
        raise RuntimeError("DATABASE_URL must be a PostgreSQL URL")
    with _POOL_LOCK:
        if _POOL is None:
            _POOL = ConnectionPool(
                conninfo=DATABASE_URL,
                min_size=DB_POOL_MIN_SIZE,
                max_size=DB_POOL_MAX_SIZE,
                timeout=DB_POOL_TIMEOUT_SECONDS,
                kwargs={"row_factory": dict_row},
                open=True,
            )
            _POOL.wait(timeout=DB_POOL_TIMEOUT_SECONDS)
    return _POOL


def _prepare_connection(raw: Any) -> None:
    schema = current_schema_name()
    if schema not in _READY_SCHEMAS:
        with _SCHEMA_LOCK:
            if schema not in _READY_SCHEMAS:
                previous = raw.autocommit
                raw.autocommit = True
                try:
                    raw.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema)))
                finally:
                    raw.autocommit = previous
                _READY_SCHEMAS.add(schema)
    raw.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema)))
    raw.commit()


def _qmark_to_postgres(statement: str) -> str:
    output: list[str] = []
    single = False
    double = False
    index = 0
    while index < len(statement):
        char = statement[index]
        if char == "'" and not double:
            if single and index + 1 < len(statement) and statement[index + 1] == "'":
                output.extend(["'", "'"])
                index += 2
                continue
            single = not single
            output.append(char)
        elif char == '"' and not single:
            double = not double
            output.append(char)
        elif char == "?" and not single and not double:
            output.append("%s")
        else:
            output.append(char)
        index += 1
    return "".join(output)


def _rewrite_insert_or_replace(statement: str) -> str:
    match = re.match(
        r"\s*INSERT\s+OR\s+REPLACE\s+INTO\s+([a-zA-Z0-9_]+)\s*\(([^)]+)\)\s*VALUES\s*\((.*)\)\s*;?\s*$",
        statement,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        raise RuntimeError("PostgreSQL compatibility requires explicit ON CONFLICT for this INSERT OR REPLACE statement")
    table = match.group(1)
    columns = [item.strip() for item in match.group(2).split(",")]
    values = match.group(3).strip()
    conflict = _REPLACE_CONFLICT_TARGETS.get(table.lower())
    if not conflict:
        raise RuntimeError(f"No PostgreSQL replacement conflict target is registered for {table}")
    updates = [column for column in columns if column not in conflict]
    assignments = ", ".join(f"{column}=excluded.{column}" for column in updates)
    return (
        f"INSERT INTO {table}({', '.join(columns)}) VALUES ({values}) "
        f"ON CONFLICT ({', '.join(conflict)}) DO UPDATE SET {assignments}"
    )


def _rewrite_sql(statement: str) -> str:
    rewritten = statement.strip()
    if re.match(r"^INSERT\s+OR\s+REPLACE\b", rewritten, flags=re.IGNORECASE):
        rewritten = _rewrite_insert_or_replace(rewritten)
    ignore = bool(re.match(r"^INSERT\s+OR\s+IGNORE\b", rewritten, flags=re.IGNORECASE))
    rewritten = re.sub(r"^INSERT\s+OR\s+IGNORE\s+INTO\b", "INSERT INTO", rewritten, flags=re.IGNORECASE)
    rewritten = re.sub(r"\s+COLLATE\s+NOCASE\b", "", rewritten, flags=re.IGNORECASE)
    rewritten = re.sub(
        r"INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT",
        "BIGSERIAL PRIMARY KEY",
        rewritten,
        flags=re.IGNORECASE,
    )
    rewritten = re.sub(r"\bAUTOINCREMENT\b", "", rewritten, flags=re.IGNORECASE)
    rewritten = re.sub(r"\bIFNULL\s*\(", "COALESCE(", rewritten, flags=re.IGNORECASE)
    if ignore and " on conflict " not in f" {rewritten.lower()} ":
        rewritten = rewritten.rstrip(";") + " ON CONFLICT DO NOTHING"
    return _qmark_to_postgres(rewritten)


def _insert_target(statement: str) -> str | None:
    match = re.match(r"\s*INSERT\s+INTO\s+([a-zA-Z0-9_]+)\b", statement, flags=re.IGNORECASE)
    return match.group(1).lower() if match else None


def _needs_returning_id(statement: str) -> bool:
    lowered = statement.lower()
    target = _insert_target(statement)
    return bool(
        target in _SERIAL_ID_TABLES
        and " returning " not in f" {lowered} "
        and re.search(r"\bvalues\s*\(", lowered)
    )


class MemoryCursor:
    def __init__(self, rows: Iterable[dict[str, Any]] = (), *, rowcount: int | None = None, lastrowid: int | None = None):
        self._rows = list(rows)
        self._index = 0
        self.rowcount = len(self._rows) if rowcount is None else rowcount
        self.lastrowid = lastrowid
        self.description = None

    def fetchone(self) -> dict[str, Any] | None:
        if self._index >= len(self._rows):
            return None
        row = self._rows[self._index]
        self._index += 1
        return row

    def fetchall(self) -> list[dict[str, Any]]:
        rows = self._rows[self._index :]
        self._index = len(self._rows)
        return rows

    def __iter__(self):
        return iter(self.fetchall())


class PostgresCursorAdapter:
    def __init__(self, cursor: Any, *, lastrowid: int | None = None):
        self._cursor = cursor
        self.lastrowid = lastrowid

    @property
    def rowcount(self) -> int:
        return int(self._cursor.rowcount)

    @property
    def description(self) -> Any:
        return self._cursor.description

    def fetchone(self) -> dict[str, Any] | None:
        return self._cursor.fetchone()

    def fetchall(self) -> list[dict[str, Any]]:
        return list(self._cursor.fetchall())

    def __iter__(self):
        return iter(self._cursor)


def _sqlite_master_cursor(raw: Any, statement: str) -> MemoryCursor:
    lowered = statement.lower()
    type_match = re.search(r"type\s*=\s*'([^']+)'", lowered)
    name_match = re.search(r"name\s*=\s*'([^']+)'", lowered)
    object_type = type_match.group(1) if type_match else "table"
    object_name = name_match.group(1) if name_match else ""
    if object_type == "trigger":
        row = raw.execute(
            "SELECT COUNT(*) AS count FROM pg_trigger WHERE tgname=%s AND NOT tgisinternal",
            (object_name,),
        ).fetchone()
    else:
        row = raw.execute(
            "SELECT COUNT(*) AS count FROM information_schema.tables WHERE table_schema=current_schema() AND table_name=%s",
            (object_name,),
        ).fetchone()
    count = int((row or {}).get("count", 0))
    alias_match = re.search(r"count\s*\([^)]*\)\s+as\s+([a-zA-Z0-9_]+)", lowered)
    alias = alias_match.group(1) if alias_match else "count"
    return MemoryCursor([{alias: count}])


class PostgresConnectionAdapter:
    def __init__(self, raw: Any, pool: ConnectionPool):
        self._raw = raw
        self._pool = pool
        self._closed = False

    @property
    def raw_connection(self) -> Any:
        return self._raw

    def execute(self, statement: str, params: Iterable[Any] | None = None):
        compact = statement.strip()
        lowered = compact.lower()
        if lowered == "begin immediate":
            cursor = self._raw.execute("SELECT pg_advisory_xact_lock(%s)", (GLOBAL_WRITE_LOCK,))
            return PostgresCursorAdapter(cursor)
        if lowered.startswith("pragma database_list"):
            return MemoryCursor([{"seq": 0, "name": "main", "file": f"postgresql:{current_schema_name()}"}])
        table_info = re.match(r"pragma\s+table_info\s*\(\s*([a-zA-Z0-9_]+)\s*\)", lowered)
        if table_info:
            rows = self._raw.execute(
                """
                SELECT ordinal_position - 1 AS cid, column_name AS name, data_type AS type,
                       CASE WHEN is_nullable='NO' THEN 1 ELSE 0 END AS notnull,
                       column_default AS dflt_value, 0 AS pk
                FROM information_schema.columns
                WHERE table_schema=current_schema() AND table_name=%s
                ORDER BY ordinal_position
                """,
                (table_info.group(1),),
            ).fetchall()
            return MemoryCursor(rows)
        if lowered.startswith("pragma foreign_key_check"):
            return MemoryCursor([])
        if lowered.startswith("pragma integrity_check"):
            return MemoryCursor([{"integrity_check": "ok"}])
        if "from sqlite_master" in lowered:
            return _sqlite_master_cursor(self._raw, compact)

        rewritten = _rewrite_sql(compact)
        returning = _needs_returning_id(rewritten)
        if returning:
            rewritten = rewritten.rstrip(";") + " RETURNING id"
        try:
            cursor = self._raw.cursor(row_factory=dict_row)
            cursor.execute(rewritten, tuple(params or ()))
            lastrowid = None
            if returning:
                returned = cursor.fetchone()
                lastrowid = int(returned["id"]) if returned and returned.get("id") is not None else None
            return PostgresCursorAdapter(cursor, lastrowid=lastrowid)
        except errors.UniqueViolation as exc:
            raise sqlite3.IntegrityError("UNIQUE constraint failed") from exc
        except errors.ForeignKeyViolation as exc:
            raise sqlite3.IntegrityError("FOREIGN KEY constraint failed") from exc
        except errors.CheckViolation as exc:
            raise sqlite3.IntegrityError("CHECK constraint failed") from exc

    def executemany(self, statement: str, params: Iterable[Iterable[Any]]):
        rewritten = _rewrite_sql(statement)
        try:
            cursor = self._raw.cursor(row_factory=dict_row)
            cursor.executemany(rewritten, params)
            return PostgresCursorAdapter(cursor)
        except errors.UniqueViolation as exc:
            raise sqlite3.IntegrityError("UNIQUE constraint failed") from exc
        except errors.ForeignKeyViolation as exc:
            raise sqlite3.IntegrityError("FOREIGN KEY constraint failed") from exc

    def executescript(self, script: str):
        # PostgreSQL schema ownership is centralized in migrations/postgres.
        # Legacy ensure_* helpers still call executescript defensively; once the
        # baseline migration is present, replaying SQLite DDL would be both
        # redundant and unsafe. Runtime single-statement DDL goes through execute.
        return MemoryCursor([], rowcount=0)

    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._pool.putconn(self._raw)


def get_conn() -> PostgresConnectionAdapter:
    pool = _pool()
    raw = pool.getconn()
    try:
        _prepare_connection(raw)
        return PostgresConnectionAdapter(raw, pool)
    except Exception:
        pool.putconn(raw)
        raise


@contextmanager
def connect() -> Iterator[PostgresConnectionAdapter]:
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _split_sql_script(script: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    single = False
    double = False
    line_comment = False
    block_comment = False
    dollar_tag: str | None = None
    index = 0
    while index < len(script):
        if line_comment:
            char = script[index]
            buffer.append(char)
            if char == "\n":
                line_comment = False
            index += 1
            continue
        if block_comment:
            if script.startswith("*/", index):
                buffer.extend(["*", "/"])
                index += 2
                block_comment = False
            else:
                buffer.append(script[index])
                index += 1
            continue
        if dollar_tag:
            if script.startswith(dollar_tag, index):
                buffer.append(dollar_tag)
                index += len(dollar_tag)
                dollar_tag = None
            else:
                buffer.append(script[index])
                index += 1
            continue
        if not single and not double and script.startswith("--", index):
            buffer.extend(["-", "-"])
            index += 2
            line_comment = True
            continue
        if not single and not double and script.startswith("/*", index):
            buffer.extend(["/", "*"])
            index += 2
            block_comment = True
            continue
        if not single and not double and script[index] == "$":
            tag_match = re.match(r"\$[a-zA-Z0-9_]*\$", script[index:])
            if tag_match:
                dollar_tag = tag_match.group(0)
                buffer.append(dollar_tag)
                index += len(dollar_tag)
                continue
        char = script[index]
        if char == "'" and not double:
            if single and index + 1 < len(script) and script[index + 1] == "'":
                buffer.extend(["'", "'"])
                index += 2
                continue
            single = not single
            buffer.append(char)
        elif char == '"' and not single:
            double = not double
            buffer.append(char)
        elif char == ";" and not single and not double:
            statement = "".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
        else:
            buffer.append(char)
        index += 1
    trailing = "".join(buffer).strip()
    if trailing:
        statements.append(trailing)
    return statements


def run_postgres_migrations() -> None:
    migrations_dir = Path(ROOT_DIR) / "migrations" / "postgres"
    pool = _pool()
    raw = pool.getconn()
    try:
        _prepare_connection(raw)
        raw.execute("SELECT pg_advisory_xact_lock(%s)", (MIGRATION_LOCK,))
        raw.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              version TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              applied_at TEXT NOT NULL DEFAULT to_char(clock_timestamp() AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')
            )
            """
        )
        for path in sorted(migrations_dir.glob("*.sql")):
            version = path.stem
            if raw.execute("SELECT 1 FROM schema_migrations WHERE version=%s", (version,)).fetchone():
                continue
            for statement in _split_sql_script(path.read_text(encoding="utf-8")):
                raw.execute(statement)
            raw.execute(
                "INSERT INTO schema_migrations(version,name) VALUES (%s,%s)",
                (version, path.name),
            )
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        pool.putconn(raw)


def database_health() -> dict[str, Any]:
    pool = _pool()
    with connect() as conn:
        row = conn.execute("SELECT 1 AS ok").fetchone()
    stats = pool.get_stats()
    return {
        "status": "ok" if row and int(row["ok"]) == 1 else "error",
        "backend": "postgresql",
        "schema": current_schema_name(),
        "pool_size": int(stats.get("pool_size", 0)),
        "pool_available": int(stats.get("pool_available", 0)),
    }


def close_pool() -> None:
    global _POOL
    with _POOL_LOCK:
        if _POOL is not None:
            _POOL.close()
            _POOL = None
