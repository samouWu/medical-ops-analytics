import sqlite3
from contextlib import closing
from pathlib import Path

from app.core.database import SCHEMA

PROJECT = Path(__file__).resolve().parents[2]
DDL_FILES = [
    PROJECT / "sql" / "ods" / "schema.sql",
    PROJECT / "sql" / "dwd" / "schema.sql",
    PROJECT / "sql" / "dim" / "schema.sql",
    PROJECT / "sql" / "dws" / "schema.sql",
    PROJECT / "sql" / "ads" / "schema.sql",
]


def test_reference_ddl_matches_runtime_layered_schema():
    with closing(sqlite3.connect(":memory:")) as runtime, closing(sqlite3.connect(":memory:")) as reference:
        runtime.executescript(SCHEMA)
        for path in DDL_FILES:
            reference.executescript(path.read_text(encoding="utf-8"))
        layered_tables = {
            row[0] for row in reference.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        }
        assert len(layered_tables) == 26
        for table in layered_tables:
            runtime_columns = runtime.execute(f"PRAGMA table_info({table})").fetchall()
            reference_columns = reference.execute(f"PRAGMA table_info({table})").fetchall()
            assert runtime_columns, table
            assert [(row[1], row[2], row[5]) for row in runtime_columns] == [(row[1], row[2], row[5]) for row in reference_columns], table
