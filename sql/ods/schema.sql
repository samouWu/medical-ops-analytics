-- SQLite 参考 DDL；对应 backend/app/core/database.py 中的运行表结构。
-- 应用启动时会自行建表，本文件不是迁移框架，也未声明经过 PostgreSQL 验证。
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS etl_batch (
    batch_id TEXT PRIMARY KEY,
    source_table TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    status TEXT NOT NULL,
    row_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    message TEXT
);

CREATE TABLE IF NOT EXISTS ods_record (
    source_table TEXT NOT NULL,
    source_pk TEXT NOT NULL,
    batch_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (source_table, source_pk)
);
