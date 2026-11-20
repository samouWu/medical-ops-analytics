-- SQLite 参考 DDL；ADS 预刷核心指标的日/周/月结果，其余指标由服务层按需计算。
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ads_metric_result (
    metric_code TEXT NOT NULL,
    stat_date TEXT NOT NULL,
    grain TEXT NOT NULL,
    dept_code TEXT NOT NULL DEFAULT 'ALL',
    value_num REAL,
    batch_id TEXT NOT NULL,
    calculated_at TEXT NOT NULL,
    PRIMARY KEY (metric_code, stat_date, grain, dept_code)
);

CREATE TABLE IF NOT EXISTS metric_definition (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    topic TEXT NOT NULL,
    unit TEXT NOT NULL,
    supported INTEGER NOT NULL,
    description TEXT NOT NULL,
    formula TEXT NOT NULL DEFAULT ''
);
