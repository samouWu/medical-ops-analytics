import json
import logging
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import DB_PATH

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS etl_batch (
 batch_id TEXT PRIMARY KEY, source_table TEXT NOT NULL, source_file TEXT NOT NULL,
 source_sha256 TEXT NOT NULL, status TEXT NOT NULL, row_count INTEGER DEFAULT 0,
 error_count INTEGER DEFAULT 0, started_at TEXT NOT NULL, finished_at TEXT, message TEXT
);
CREATE TABLE IF NOT EXISTS ods_record (
 source_table TEXT NOT NULL, source_pk TEXT NOT NULL, batch_id TEXT NOT NULL,
 payload_json TEXT NOT NULL, content_hash TEXT NOT NULL, created_at TEXT NOT NULL,
 PRIMARY KEY(source_table, source_pk)
);
CREATE TABLE IF NOT EXISTS dwd_outpatient_visit (
 visit_id TEXT PRIMARY KEY, patient_key TEXT NOT NULL, dept_code TEXT NOT NULL,
 visit_date TEXT NOT NULL, visit_type TEXT, fee_amount REAL DEFAULT 0, source_batch TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dwd_inpatient_stay (
 visit_id TEXT PRIMARY KEY, patient_key TEXT NOT NULL, dept_code TEXT NOT NULL,
 bed_no TEXT, admit_date TEXT NOT NULL, discharge_date TEXT, stay_days REAL DEFAULT 0,
 total_fee REAL DEFAULT 0, drug_fee REAL DEFAULT 0, consumable_fee REAL DEFAULT 0,
 disease_code TEXT, source_batch TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dwd_charge_detail (
 charge_id TEXT PRIMARY KEY, visit_id TEXT, patient_key TEXT, visit_type TEXT,
 dept_code TEXT NOT NULL, fee_date TEXT NOT NULL, fee_type_code TEXT,
 fee_type_name TEXT, amount REAL DEFAULT 0, source_batch TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dwd_emr_record (
 record_id TEXT PRIMARY KEY, patient_key TEXT, visit_id TEXT, dept_code TEXT,
 visit_date TEXT, diagnosis TEXT, disease_code TEXT, source_batch TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dwd_lis_report (
 report_id TEXT PRIMARY KEY, patient_key TEXT, visit_id TEXT, item_name TEXT,
 result_text TEXT, report_date TEXT, source_batch TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dwd_finance_day (
 record_id TEXT PRIMARY KEY, stat_date TEXT NOT NULL, dept_code TEXT NOT NULL,
 revenue REAL DEFAULT 0, drug_revenue REAL DEFAULT 0, consumable_revenue REAL DEFAULT 0,
 source_batch TEXT NOT NULL, UNIQUE(stat_date, dept_code)
);
CREATE TABLE IF NOT EXISTS dwd_encounter_wide (
 source_type TEXT NOT NULL, encounter_id TEXT NOT NULL, patient_key TEXT NOT NULL,
 dept_code TEXT NOT NULL, start_date TEXT NOT NULL, end_date TEXT,
 visit_type TEXT, disease_code TEXT, diagnosis TEXT,
 outpatient_fee REAL DEFAULT 0, inpatient_total_fee REAL DEFAULT 0,
 drug_fee REAL DEFAULT 0, consumable_fee REAL DEFAULT 0,
 charge_amount REAL DEFAULT 0, charge_items INTEGER DEFAULT 0,
 lis_reports INTEGER DEFAULT 0, abnormal_lis_reports INTEGER DEFAULT 0,
 source_batch TEXT NOT NULL, PRIMARY KEY(source_type, encounter_id)
);
CREATE TABLE IF NOT EXISTS dim_department (
 dept_code TEXT PRIMARY KEY, dept_name TEXT NOT NULL, bed_count REAL NOT NULL,
 staff_count REAL NOT NULL, mapping_status TEXT NOT NULL DEFAULT '待业务确认'
);
CREATE TABLE IF NOT EXISTS dim_disease (
 disease_code TEXT PRIMARY KEY, disease_name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dim_fee_type (
 fee_type_code TEXT PRIMARY KEY, fee_type_name TEXT NOT NULL, category TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dim_date (
 date_key TEXT PRIMARY KEY, year INTEGER NOT NULL, quarter INTEGER NOT NULL,
 month INTEGER NOT NULL, week_start TEXT NOT NULL, iso_year INTEGER NOT NULL,
 iso_week INTEGER NOT NULL, weekday INTEGER NOT NULL, is_weekend INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS dws_dept_day (
 stat_date TEXT NOT NULL, dept_code TEXT NOT NULL,
 outpatient_visits INTEGER DEFAULT 0, outpatient_patients INTEGER DEFAULT 0,
 outpatient_revenue REAL DEFAULT 0, admissions INTEGER DEFAULT 0, discharges INTEGER DEFAULT 0,
 inpatient_revenue REAL DEFAULT 0, drug_revenue REAL DEFAULT 0, consumable_revenue REAL DEFAULT 0,
 total_revenue REAL DEFAULT 0, stay_days REAL DEFAULT 0, occupied_bed_days REAL DEFAULT 0,
 open_bed_days REAL DEFAULT 0, lis_reports INTEGER DEFAULT 0, abnormal_lis_reports INTEGER DEFAULT 0,
 PRIMARY KEY(stat_date, dept_code)
);
CREATE TABLE IF NOT EXISTS dws_disease (
 disease_code TEXT NOT NULL, dept_code TEXT NOT NULL, discharges INTEGER DEFAULT 0,
 total_fee REAL DEFAULT 0, stay_days REAL DEFAULT 0,
 PRIMARY KEY(disease_code, dept_code)
);
CREATE TABLE IF NOT EXISTS dws_outpatient_day (
 stat_date TEXT NOT NULL, dept_code TEXT NOT NULL, visits INTEGER DEFAULT 0,
 patients INTEGER DEFAULT 0, revisit_rate REAL, emergency_visits INTEGER DEFAULT 0,
 PRIMARY KEY(stat_date, dept_code)
);
CREATE TABLE IF NOT EXISTS dws_inpatient_day (
 stat_date TEXT NOT NULL, dept_code TEXT NOT NULL, admissions INTEGER DEFAULT 0,
 discharges INTEGER DEFAULT 0, occupied_bed_days REAL DEFAULT 0, open_bed_days REAL DEFAULT 0,
 stay_days REAL DEFAULT 0, bed_usage_pct REAL, avg_stay_days REAL, turnover REAL,
 PRIMARY KEY(stat_date, dept_code)
);
CREATE TABLE IF NOT EXISTS dws_revenue_day (
 stat_date TEXT NOT NULL, dept_code TEXT NOT NULL, outpatient_revenue REAL DEFAULT 0,
 inpatient_revenue REAL DEFAULT 0, total_revenue REAL DEFAULT 0,
 PRIMARY KEY(stat_date, dept_code)
);
CREATE TABLE IF NOT EXISTS dws_drug_day (
 stat_date TEXT NOT NULL, dept_code TEXT NOT NULL, drug_revenue REAL DEFAULT 0,
 total_revenue REAL DEFAULT 0, drug_ratio REAL,
 PRIMARY KEY(stat_date, dept_code)
);
CREATE TABLE IF NOT EXISTS dws_consumable_day (
 stat_date TEXT NOT NULL, dept_code TEXT NOT NULL, consumable_revenue REAL DEFAULT 0,
 total_revenue REAL DEFAULT 0, consumable_ratio REAL,
 PRIMARY KEY(stat_date, dept_code)
);
CREATE TABLE IF NOT EXISTS dws_disease_day (
 stat_date TEXT NOT NULL, dept_code TEXT NOT NULL, disease_code TEXT NOT NULL,
 discharges INTEGER DEFAULT 0, total_fee REAL DEFAULT 0, stay_days REAL DEFAULT 0,
 avg_fee REAL, avg_stay_days REAL,
 PRIMARY KEY(stat_date, dept_code, disease_code)
);
CREATE TABLE IF NOT EXISTS dws_resource_day (
 stat_date TEXT NOT NULL, dept_code TEXT NOT NULL, bed_count REAL DEFAULT 0,
 staff_count REAL DEFAULT 0, bed_usage_pct REAL, turnover REAL,
 visits_per_staff REAL, revenue_per_staff REAL,
 PRIMARY KEY(stat_date, dept_code)
);
CREATE TABLE IF NOT EXISTS dws_service_day (
 stat_date TEXT NOT NULL, dept_code TEXT NOT NULL, lis_reports INTEGER DEFAULT 0,
 abnormal_reports INTEGER DEFAULT 0, abnormal_rate REAL,
 PRIMARY KEY(stat_date, dept_code)
);
CREATE TABLE IF NOT EXISTS ads_metric_result (
 metric_code TEXT NOT NULL, stat_date TEXT NOT NULL, grain TEXT NOT NULL,
 dept_code TEXT NOT NULL DEFAULT 'ALL', value_num REAL, batch_id TEXT NOT NULL,
 calculated_at TEXT NOT NULL, PRIMARY KEY(metric_code, stat_date, grain, dept_code)
);
CREATE TABLE IF NOT EXISTS metric_definition (
 code TEXT PRIMARY KEY, name TEXT NOT NULL, topic TEXT NOT NULL, unit TEXT NOT NULL,
 supported INTEGER NOT NULL, description TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS app_user (
 username TEXT PRIMARY KEY, display_name TEXT NOT NULL, password_hash TEXT NOT NULL,
 role TEXT NOT NULL, dept_codes_json TEXT NOT NULL DEFAULT '[]', enabled INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS audit_log (
 id INTEGER PRIMARY KEY AUTOINCREMENT, trace_id TEXT NOT NULL, username TEXT NOT NULL,
 action TEXT NOT NULL, resource TEXT NOT NULL, detail TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quality_result (
 id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT NOT NULL, rule_code TEXT NOT NULL,
 rule_name TEXT NOT NULL, status TEXT NOT NULL, checked_rows INTEGER DEFAULT 0,
 failed_rows INTEGER DEFAULT 0, duration_ms REAL DEFAULT 0, details TEXT,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS etl_job (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, source_table TEXT NOT NULL,
 schedule TEXT NOT NULL, enabled INTEGER DEFAULT 1, last_status TEXT,
 last_run TEXT, retry_limit INTEGER DEFAULT 3
);
CREATE TABLE IF NOT EXISTS data_source (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL, config_json TEXT NOT NULL,
 enabled INTEGER DEFAULT 1, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_outpatient_date ON dwd_outpatient_visit(visit_date, dept_code);
CREATE INDEX IF NOT EXISTS idx_inpatient_dates ON dwd_inpatient_stay(discharge_date, admit_date, dept_code);
CREATE INDEX IF NOT EXISTS idx_charge_date ON dwd_charge_detail(fee_date, dept_code, visit_type);
CREATE INDEX IF NOT EXISTS idx_charge_fee_date_type_amount ON dwd_charge_detail(fee_date, fee_type_name, amount);
CREATE INDEX IF NOT EXISTS idx_encounter_wide_date ON dwd_encounter_wide(start_date, dept_code);
CREATE INDEX IF NOT EXISTS idx_dws_date ON dws_dept_day(stat_date, dept_code);
CREATE INDEX IF NOT EXISTS idx_dws_outpatient_date ON dws_outpatient_day(stat_date, dept_code);
CREATE INDEX IF NOT EXISTS idx_dws_inpatient_date ON dws_inpatient_day(stat_date, dept_code);
CREATE INDEX IF NOT EXISTS idx_dws_revenue_date ON dws_revenue_day(stat_date, dept_code);
CREATE INDEX IF NOT EXISTS idx_dws_drug_date ON dws_drug_day(stat_date, dept_code);
CREATE INDEX IF NOT EXISTS idx_dws_consumable_date ON dws_consumable_day(stat_date, dept_code);
CREATE INDEX IF NOT EXISTS idx_dws_disease_day ON dws_disease_day(stat_date, dept_code);
CREATE INDEX IF NOT EXISTS idx_dws_resource_date ON dws_resource_day(stat_date, dept_code);
CREATE INDEX IF NOT EXISTS idx_dws_service_date ON dws_service_day(stat_date, dept_code);
CREATE INDEX IF NOT EXISTS idx_ads_lookup ON ads_metric_result(grain, stat_date, dept_code);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(created_at);
"""

DEPARTMENTS = [
    ("HN", "呼吸内科", 45, 24), ("HX", "心血管内科", 50, 26),
    ("XH", "消化内科", 40, 22), ("SJ", "神经内科", 40, 22),
    ("GK", "骨科", 35, 20), ("PW", "普外科", 40, 22),
    ("FC", "妇产科", 30, 18), ("EK", "儿科", 45, 24),
    ("JZ", "急诊科", 30, 20), ("ICU", "重症医学科", 20, 16),
]
DISEASES = [
    ("I10", "原发性高血压"), ("N18", "慢性肾脏病"), ("J18", "肺炎"),
    ("E11", "糖尿病"), ("J44", "慢阻肺"), ("K35", "急性阑尾炎"),
    ("A09", "感染性腹泻"), ("I25", "慢性缺血性心脏病"),
    ("I63", "脑梗死"), ("C16", "胃癌"),
]
FEE_TYPES = [
    ("XY", "西药费", "药品"), ("ZC", "中成药费", "药品"),
    ("JC", "检查费", "检查"), ("JY", "检验费", "检验"),
    ("ZL", "治疗费", "治疗"), ("SS", "手术费", "手术"),
    ("CL", "材料费", "耗材"), ("CW", "床位费", "床位"), ("HL", "护理费", "护理"),
]


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def db_session():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    from app.core.security import hash_password
    from app.services.metrics import METRICS
    with db_session() as conn:
        conn.executescript(SCHEMA)
        conn.executemany("INSERT OR REPLACE INTO dim_department VALUES (?,?,?,?,?)", [(*row, "待业务确认") for row in DEPARTMENTS])
        conn.executemany("INSERT OR REPLACE INTO dim_disease VALUES (?,?)", DISEASES)
        conn.executemany("INSERT OR REPLACE INTO dim_fee_type VALUES (?,?,?)", FEE_TYPES)
        conn.executemany("INSERT OR REPLACE INTO metric_definition VALUES (?,?,?,?,?,?)", METRICS)
        if conn.execute("SELECT COUNT(*) FROM app_user").fetchone()[0] == 0:
            users = [
                ("admin", "系统管理员", hash_password("admin123"), "admin", "[]"),
                ("analyst", "运营分析师", hash_password("analyst123"), "analyst", "[]"),
                ("dept_hn", "呼吸内科负责人", hash_password("dept123"), "department", '["HN"]'),
            ]
            conn.executemany("INSERT INTO app_user VALUES (?,?,?,?,?,1)", users)
        jobs = [
            ("outpatient", "HIS门诊日终采集", "his_outpatient", "0 2 * * *"),
            ("inpatient", "HIS住院日终采集", "his_inpatient", "5 2 * * *"),
            ("charge", "HIS收费日终采集", "his_charge", "10 2 * * *"),
            ("emr", "EMR病历日终采集", "emr_record", "15 2 * * *"),
            ("lis", "LIS报告日终采集", "lis_report", "20 2 * * *"),
            ("finance", "财务文件日终采集", "finance_excel", "25 2 * * *"),
        ]
        conn.executemany("INSERT OR IGNORE INTO etl_job(id,name,source_table,schedule) VALUES (?,?,?,?)", jobs)
        sources = [(name, table, "csv", json.dumps({"path": path}, ensure_ascii=False), datetime.now(timezone.utc).isoformat()) for name, table, path in [
            ("his_outpatient", "HIS门诊", "data/mock_his/his_outpatient.csv"),
            ("his_inpatient", "HIS住院", "data/mock_his/his_inpatient.csv"),
            ("his_charge", "HIS收费", "data/mock_his/his_charge.csv"),
            ("emr_record", "EMR病历", "data/mock_his/emr_record.csv"),
            ("lis_report", "LIS报告", "data/mock_his/lis_report.csv"),
            ("finance_excel", "财务汇总", "data/files/finance_excel.csv"),
        ]]
        conn.executemany("INSERT OR IGNORE INTO data_source VALUES (?,?,?,?,1,?)", sources)


def get_user(username: str) -> dict | None:
    with db_session() as conn:
        row = conn.execute("SELECT * FROM app_user WHERE username=?", (username,)).fetchone()
    if not row:
        return None
    result = dict(row)
    result["dept_codes"] = json.loads(result.pop("dept_codes_json"))
    result.pop("password_hash", None)
    return result


def audit(username: str, action: str, resource: str, detail: str, trace_id: str) -> None:
    """审计为尽力写入：短暂锁冲突重试，最终失败记录告警但不破坏业务响应。"""
    for attempt in range(3):
        try:
            with db_session() as conn:
                conn.execute("INSERT INTO audit_log(trace_id,username,action,resource,detail,created_at) VALUES (?,?,?,?,?,?)",
                             (trace_id, username, action, resource, detail[:500], datetime.now(timezone.utc).isoformat()))
            return
        except sqlite3.OperationalError as exc:
            if attempt < 2 and ("locked" in str(exc).lower() or "readonly" in str(exc).lower()):
                time.sleep(0.05*(attempt+1))
                continue
            logging.getLogger(__name__).warning("audit write failed: %s", exc)
            return
