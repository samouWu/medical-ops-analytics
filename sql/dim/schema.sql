-- SQLite 参考 DDL；床位、人力和 mapping_status 均为教学配置，不是院内主数据。
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS dim_department (
    dept_code TEXT PRIMARY KEY,
    dept_name TEXT NOT NULL,
    bed_count REAL NOT NULL,
    staff_count REAL NOT NULL,
    mapping_status TEXT NOT NULL DEFAULT '待业务确认'
);

CREATE TABLE IF NOT EXISTS dim_disease (
    disease_code TEXT PRIMARY KEY,
    disease_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_fee_type (
    fee_type_code TEXT PRIMARY KEY,
    fee_type_name TEXT NOT NULL,
    category TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key TEXT PRIMARY KEY,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    week_start TEXT NOT NULL,
    iso_year INTEGER NOT NULL,
    iso_week INTEGER NOT NULL,
    weekday INTEGER NOT NULL,
    is_weekend INTEGER NOT NULL
);
