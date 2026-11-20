-- SQLite 参考 DDL；字段顺序与 ETL 的 INSERT 语句保持一致。
-- DWD 不设置维度外键，以便先落地再由质量规则识别未映射记录。
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS dwd_outpatient_visit (
    visit_id TEXT PRIMARY KEY,
    patient_key TEXT NOT NULL,
    dept_code TEXT NOT NULL,
    visit_date TEXT NOT NULL,
    visit_type TEXT,
    fee_amount REAL DEFAULT 0,
    source_batch TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dwd_inpatient_stay (
    visit_id TEXT PRIMARY KEY,
    patient_key TEXT NOT NULL,
    dept_code TEXT NOT NULL,
    bed_no TEXT,
    admit_date TEXT NOT NULL,
    discharge_date TEXT,
    stay_days REAL DEFAULT 0,
    total_fee REAL DEFAULT 0,
    drug_fee REAL DEFAULT 0,
    consumable_fee REAL DEFAULT 0,
    disease_code TEXT,
    source_batch TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dwd_charge_detail (
    charge_id TEXT PRIMARY KEY,
    visit_id TEXT,
    patient_key TEXT,
    visit_type TEXT,
    dept_code TEXT NOT NULL,
    fee_date TEXT NOT NULL,
    fee_type_code TEXT,
    fee_type_name TEXT,
    amount REAL DEFAULT 0,
    source_batch TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dwd_emr_record (
    record_id TEXT PRIMARY KEY,
    patient_key TEXT,
    visit_id TEXT,
    dept_code TEXT,
    visit_date TEXT,
    diagnosis TEXT,
    disease_code TEXT,
    source_batch TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dwd_lis_report (
    report_id TEXT PRIMARY KEY,
    patient_key TEXT,
    visit_id TEXT,
    item_name TEXT,
    result_text TEXT,
    report_date TEXT,
    source_batch TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dwd_finance_day (
    record_id TEXT PRIMARY KEY,
    stat_date TEXT NOT NULL,
    dept_code TEXT NOT NULL,
    revenue REAL DEFAULT 0,
    drug_revenue REAL DEFAULT 0,
    consumable_revenue REAL DEFAULT 0,
    source_batch TEXT NOT NULL,
    UNIQUE (stat_date, dept_code)
);

CREATE TABLE IF NOT EXISTS dwd_encounter_wide (
    source_type TEXT NOT NULL,
    encounter_id TEXT NOT NULL,
    patient_key TEXT NOT NULL,
    dept_code TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    visit_type TEXT,
    disease_code TEXT,
    diagnosis TEXT,
    outpatient_fee REAL DEFAULT 0,
    inpatient_total_fee REAL DEFAULT 0,
    drug_fee REAL DEFAULT 0,
    consumable_fee REAL DEFAULT 0,
    charge_amount REAL DEFAULT 0,
    charge_items INTEGER DEFAULT 0,
    lis_reports INTEGER DEFAULT 0,
    abnormal_lis_reports INTEGER DEFAULT 0,
    source_batch TEXT NOT NULL,
    PRIMARY KEY (source_type, encounter_id)
);

CREATE INDEX IF NOT EXISTS idx_outpatient_date
    ON dwd_outpatient_visit (visit_date, dept_code);
CREATE INDEX IF NOT EXISTS idx_inpatient_dates
    ON dwd_inpatient_stay (discharge_date, admit_date, dept_code);
CREATE INDEX IF NOT EXISTS idx_charge_date
    ON dwd_charge_detail (fee_date, dept_code, visit_type);
CREATE INDEX IF NOT EXISTS idx_encounter_wide_date
    ON dwd_encounter_wide (start_date, dept_code);
