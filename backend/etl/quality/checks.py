import time
import uuid

from app.core.database import db_session
from etl.jobs.pipeline import now_iso

RULES = [
    ("OP_NOT_NULL", "门诊关键字段完整性", "SELECT COUNT(*),SUM(visit_id IS NULL OR patient_key IS NULL OR dept_code IS NULL OR visit_date IS NULL) FROM dwd_outpatient_visit"),
    ("OP_UNIQUE", "门诊业务主键唯一性", "SELECT COUNT(*),COUNT(*)-COUNT(DISTINCT visit_id) FROM dwd_outpatient_visit"),
    ("IP_DATE", "住院日期逻辑", "SELECT COUNT(*),SUM(discharge_date<admit_date OR stay_days<0) FROM dwd_inpatient_stay"),
    ("IP_UNIQUE", "住院业务主键唯一性", "SELECT COUNT(*),COUNT(*)-COUNT(DISTINCT visit_id) FROM dwd_inpatient_stay"),
    ("CHARGE_AMOUNT", "收费金额值域", "SELECT COUNT(*),SUM(amount<0) FROM dwd_charge_detail"),
    ("CHARGE_UNIQUE", "收费业务主键唯一性", "SELECT COUNT(*),COUNT(*)-COUNT(DISTINCT charge_id) FROM dwd_charge_detail"),
    ("DEPT_MAPPING", "科室字典映射", "SELECT COUNT(*),SUM(d.dept_code IS NULL) FROM dwd_charge_detail c LEFT JOIN dim_department d USING(dept_code)"),
    ("DISEASE_MAPPING", "病种字典映射", "SELECT COUNT(*),SUM(d.disease_code IS NULL) FROM dwd_inpatient_stay i LEFT JOIN dim_disease d USING(disease_code)"),
    ("LIS_RESULT", "检验结果值域", "SELECT COUNT(*),SUM(result_text NOT IN ('正常','异常','偏高','偏低','阴性','阳性','未见异常','在参考范围内')) FROM dwd_lis_report"),
    ("FINANCE_NONNEGATIVE", "财务金额非负", "SELECT COUNT(*),SUM(revenue<0 OR drug_revenue<0 OR consumable_revenue<0) FROM dwd_finance_day"),
]


def run_quality():
    batch_id = uuid.uuid4().hex
    results = []
    with db_session() as conn:
        for code, name, sql in RULES:
            started = time.perf_counter()
            checked, failed = conn.execute(sql).fetchone()
            failed = int(failed or 0)
            checked = int(checked or 0)
            duration = round((time.perf_counter()-started)*1000, 2)
            result = {"rule_code": code, "rule_name": name, "status": "PASS" if failed == 0 else "FAIL", "checked_rows": checked, "failed_rows": failed, "duration_ms": duration, "details": "通过" if failed == 0 else f"发现{failed}条异常，已记录并等待处理"}
            conn.execute("INSERT INTO quality_result(batch_id,rule_code,rule_name,status,checked_rows,failed_rows,duration_ms,details,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                         (batch_id, code, name, result["status"], checked, failed, duration, result["details"], now_iso()))
            results.append(result)
        conn.execute("INSERT INTO etl_batch(batch_id,source_table,source_file,source_sha256,status,row_count,error_count,started_at,finished_at) VALUES (?,?,?,?,?,?,?,?,?)",
                     (batch_id, "quality", "数据质量规则集", "-", "SUCCESS" if all(x["status"] == "PASS" for x in results) else "PARTIAL", sum(x["checked_rows"] for x in results), sum(x["failed_rows"] for x in results), now_iso(), now_iso()))
    return {"batch_id": batch_id, "results": results}


def latest_quality():
    with db_session() as conn:
        batch = conn.execute("SELECT * FROM etl_batch WHERE source_table='quality' ORDER BY started_at DESC LIMIT 1").fetchone()
        if not batch:
            return run_quality()
        results = [dict(row) for row in conn.execute("SELECT rule_code,rule_name,status,checked_rows,failed_rows,duration_ms,details FROM quality_result WHERE batch_id=? ORDER BY id", (batch["batch_id"],))]
        batches = [dict(row) for row in conn.execute("SELECT batch_id,source_table,status,row_count,error_count,finished_at FROM etl_batch ORDER BY started_at DESC LIMIT 12")]
    checked = sum(x["checked_rows"] for x in results)
    failed = sum(x["failed_rows"] for x in results)
    return {"score": round(max(0, 100 - failed / checked * 100), 2) if checked else 100, "generated_at": batch["finished_at"], "results": results, "batches": batches}
