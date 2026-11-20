-- SQLite 参考 DDL；汇总逻辑以 backend/etl/jobs/pipeline.py 为准。
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS dws_dept_day (
    stat_date TEXT NOT NULL,
    dept_code TEXT NOT NULL,
    outpatient_visits INTEGER DEFAULT 0,
    outpatient_patients INTEGER DEFAULT 0,
    outpatient_revenue REAL DEFAULT 0,
    admissions INTEGER DEFAULT 0,
    discharges INTEGER DEFAULT 0,
    inpatient_revenue REAL DEFAULT 0,
    drug_revenue REAL DEFAULT 0,
    consumable_revenue REAL DEFAULT 0,
    total_revenue REAL DEFAULT 0,
    stay_days REAL DEFAULT 0,
    occupied_bed_days REAL DEFAULT 0,
    open_bed_days REAL DEFAULT 0,
    lis_reports INTEGER DEFAULT 0,
    abnormal_lis_reports INTEGER DEFAULT 0,
    PRIMARY KEY (stat_date, dept_code)
);

CREATE TABLE IF NOT EXISTS dws_disease (
    disease_code TEXT NOT NULL,
    dept_code TEXT NOT NULL,
    discharges INTEGER DEFAULT 0,
    total_fee REAL DEFAULT 0,
    stay_days REAL DEFAULT 0,
    PRIMARY KEY (disease_code, dept_code)
);

CREATE TABLE IF NOT EXISTS dws_outpatient_day (
    stat_date TEXT NOT NULL,
    dept_code TEXT NOT NULL,
    visits INTEGER DEFAULT 0,
    patients INTEGER DEFAULT 0,
    revisit_rate REAL,
    emergency_visits INTEGER DEFAULT 0,
    PRIMARY KEY (stat_date, dept_code)
);

CREATE TABLE IF NOT EXISTS dws_inpatient_day (
    stat_date TEXT NOT NULL,
    dept_code TEXT NOT NULL,
    admissions INTEGER DEFAULT 0,
    discharges INTEGER DEFAULT 0,
    occupied_bed_days REAL DEFAULT 0,
    open_bed_days REAL DEFAULT 0,
    stay_days REAL DEFAULT 0,
    bed_usage_pct REAL,
    avg_stay_days REAL,
    turnover REAL,
    PRIMARY KEY (stat_date, dept_code)
);

CREATE TABLE IF NOT EXISTS dws_revenue_day (
    stat_date TEXT NOT NULL,
    dept_code TEXT NOT NULL,
    outpatient_revenue REAL DEFAULT 0,
    inpatient_revenue REAL DEFAULT 0,
    total_revenue REAL DEFAULT 0,
    PRIMARY KEY (stat_date, dept_code)
);

CREATE TABLE IF NOT EXISTS dws_drug_day (
    stat_date TEXT NOT NULL,
    dept_code TEXT NOT NULL,
    drug_revenue REAL DEFAULT 0,
    total_revenue REAL DEFAULT 0,
    drug_ratio REAL,
    PRIMARY KEY (stat_date, dept_code)
);

CREATE TABLE IF NOT EXISTS dws_consumable_day (
    stat_date TEXT NOT NULL,
    dept_code TEXT NOT NULL,
    consumable_revenue REAL DEFAULT 0,
    total_revenue REAL DEFAULT 0,
    consumable_ratio REAL,
    PRIMARY KEY (stat_date, dept_code)
);

CREATE TABLE IF NOT EXISTS dws_disease_day (
    stat_date TEXT NOT NULL,
    dept_code TEXT NOT NULL,
    disease_code TEXT NOT NULL,
    discharges INTEGER DEFAULT 0,
    total_fee REAL DEFAULT 0,
    stay_days REAL DEFAULT 0,
    avg_fee REAL,
    avg_stay_days REAL,
    PRIMARY KEY (stat_date, dept_code, disease_code)
);

CREATE TABLE IF NOT EXISTS dws_resource_day (
    stat_date TEXT NOT NULL,
    dept_code TEXT NOT NULL,
    bed_count REAL DEFAULT 0,
    staff_count REAL DEFAULT 0,
    bed_usage_pct REAL,
    turnover REAL,
    visits_per_staff REAL,
    revenue_per_staff REAL,
    PRIMARY KEY (stat_date, dept_code)
);

CREATE TABLE IF NOT EXISTS dws_service_day (
    stat_date TEXT NOT NULL,
    dept_code TEXT NOT NULL,
    lis_reports INTEGER DEFAULT 0,
    abnormal_reports INTEGER DEFAULT 0,
    abnormal_rate REAL,
    PRIMARY KEY (stat_date, dept_code)
);

CREATE INDEX IF NOT EXISTS idx_dws_date
    ON dws_dept_day (stat_date, dept_code);
CREATE INDEX IF NOT EXISTS idx_dws_outpatient_date
    ON dws_outpatient_day (stat_date, dept_code);
CREATE INDEX IF NOT EXISTS idx_dws_inpatient_date
    ON dws_inpatient_day (stat_date, dept_code);
CREATE INDEX IF NOT EXISTS idx_dws_disease_day
    ON dws_disease_day (stat_date, dept_code);
CREATE INDEX IF NOT EXISTS idx_dws_service_date
    ON dws_service_day (stat_date, dept_code);
