import csv
import hashlib
import io
import json
import os
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from openpyxl import load_workbook

from app.core.config import BASE_DIR, DATA_DIR
from app.core.database import db_session, init_db

SOURCES = {
    "his_outpatient": {"path": "mock_his/his_outpatient.csv", "pk": "visit_id", "date": "visit_date", "required": ["visit_id", "patient_id", "dept_code", "visit_date", "fee_amount"]},
    "his_inpatient": {"path": "mock_his/his_inpatient.csv", "pk": "visit_id", "date": "admit_date", "required": ["visit_id", "patient_id", "dept_code", "admit_date", "discharge_date", "stay_days", "total_fee", "drug_fee", "consumable_fee", "disease_code"]},
    "his_charge": {"path": "mock_his/his_charge.csv", "pk": "charge_id", "date": "fee_date", "required": ["charge_id", "visit_id", "patient_id", "visit_type", "dept_code", "fee_date", "fee_type_code", "fee_type_name", "amount"]},
    "emr_record": {"path": "mock_his/emr_record.csv", "pk": "record_id", "date": "visit_date", "required": ["record_id", "patient_id", "visit_id", "dept_code", "visit_date", "diagnosis", "disease_code"]},
    "lis_report": {"path": "mock_his/lis_report.csv", "pk": "report_id", "date": "report_date", "required": ["report_id", "patient_id", "visit_id", "item_name", "result_text", "report_date"]},
    "finance_excel": {"path": "files/finance_excel.csv", "pk": "record_id", "date": "stat_date", "required": ["record_id", "stat_date", "dept_code", "revenue", "drug_revenue", "consumable_revenue"]},
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def number(value):
    try:
        result = float(value or 0)
        if result != result or result in (float("inf"), float("-inf")):
            raise ValueError
        return result
    except (TypeError, ValueError):
        raise ValueError("数值字段格式错误") from None


def valid_date(value):
    try:
        return date.fromisoformat(str(value or "")[:10]).isoformat()
    except ValueError:
        raise ValueError("日期必须为YYYY-MM-DD") from None


def patient_key(value):
    salt = os.getenv("MEDICAL_HASH_SALT", "local-course-project")
    return hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()[:24]


def read_rows(path: Path):
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            return list(reader.fieldnames or []), [dict(row) for row in reader]
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        book = load_workbook(path, read_only=True, data_only=True)
        sheet = book.active
        values = list(sheet.iter_rows(values_only=True))
        if not values:
            return [], []
        columns = [str(item or "").strip() for item in values[0]]
        return columns, [dict(zip(columns, row)) for row in values[1:]]
    raise ValueError("仅支持CSV、XLSX或XLSM文件")


def detect_source(columns):
    matches = [name for name, spec in SOURCES.items() if set(spec["required"]).issubset(columns)]
    if not matches:
        raise ValueError("无法识别数据模板，缺少必要字段")
    return max(matches, key=lambda name: len(SOURCES[name]["required"]))


def normalize(source, row):
    key = patient_key(row.get("patient_id"))
    if source == "his_outpatient":
        return (row["visit_id"], key, row["dept_code"], valid_date(row["visit_date"]), row.get("visit_type"), number(row.get("fee_amount")))
    if source == "his_inpatient":
        return (row["visit_id"], key, row["dept_code"], row.get("bed_no"), valid_date(row["admit_date"]), valid_date(row["discharge_date"]), number(row.get("stay_days")), number(row.get("total_fee")), number(row.get("drug_fee")), number(row.get("consumable_fee")), row.get("disease_code"))
    if source == "his_charge":
        return (row["charge_id"], row.get("visit_id"), key, row.get("visit_type"), row["dept_code"], valid_date(row["fee_date"]), row.get("fee_type_code"), row.get("fee_type_name"), number(row.get("amount")))
    if source == "emr_record":
        return (row["record_id"], key, row.get("visit_id"), row.get("dept_code"), valid_date(row["visit_date"]), row.get("diagnosis"), row.get("disease_code"))
    if source == "lis_report":
        return (row["report_id"], key, row.get("visit_id"), row.get("item_name"), row.get("result_text"), valid_date(row["report_date"]))
    return (row["record_id"], valid_date(row["stat_date"]), row["dept_code"], number(row.get("revenue")), number(row.get("drug_revenue")), number(row.get("consumable_revenue")))


TARGETS = {
    "his_outpatient": ("dwd_outpatient_visit", "visit_id,patient_key,dept_code,visit_date,visit_type,fee_amount"),
    "his_inpatient": ("dwd_inpatient_stay", "visit_id,patient_key,dept_code,bed_no,admit_date,discharge_date,stay_days,total_fee,drug_fee,consumable_fee,disease_code"),
    "his_charge": ("dwd_charge_detail", "charge_id,visit_id,patient_key,visit_type,dept_code,fee_date,fee_type_code,fee_type_name,amount"),
    "emr_record": ("dwd_emr_record", "record_id,patient_key,visit_id,dept_code,visit_date,diagnosis,disease_code"),
    "lis_report": ("dwd_lis_report", "report_id,patient_key,visit_id,item_name,result_text,report_date"),
    "finance_excel": ("dwd_finance_day", "record_id,stat_date,dept_code,revenue,drug_revenue,consumable_revenue"),
}


def import_file(source: str, path: Path, rebuild=True, incremental=False):
    if source not in SOURCES:
        raise ValueError("未知数据源")
    init_db()
    batch_id = uuid.uuid4().hex
    started = time.perf_counter()
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    with db_session() as conn:
        conn.execute("INSERT INTO etl_batch(batch_id,source_table,source_file,source_sha256,status,started_at) VALUES (?,?,?,?,?,?)",
                     (batch_id, source, path.name, digest, "RUNNING", now_iso()))
        target_table = TARGETS[source][0]
        date_column = SOURCES[source]["date"]
        watermark = conn.execute(f"SELECT MAX({date_column}) FROM {target_table}").fetchone()[0]
    try:
        columns, rows = read_rows(path)
        if not rows:
            raise ValueError("文件没有可导入的数据行")
        if len(rows) > 500000:
            raise ValueError("单批次不能超过500000行")
        missing = [field for field in SOURCES[source]["required"] if field not in columns]
        if missing:
            raise ValueError("模板缺少字段：" + ", ".join(missing))
        pk = SOURCES[source]["pk"]
        date_field = SOURCES[source]["date"]
        seen = {}
        accepted, errors = [], []
        skipped = 0
        for line, row in enumerate(rows, 2):
            try:
                if not str(row.get(pk) or "").strip():
                    raise ValueError("业务主键为空")
                row_date = valid_date(row.get(date_field))
                if incremental and watermark and row_date <= watermark:
                    skipped += 1
                    continue
                normalized = normalize(source, row)
                if any(isinstance(v, float) and v < 0 for v in normalized):
                    raise ValueError("金额或天数不能为负数")
                identity = str(row[pk])
                content = json.dumps(row, ensure_ascii=False, default=str, sort_keys=True)
                if identity in seen:
                    if seen[identity] != content:
                        raise ValueError("业务主键冲突")
                    continue
                seen[identity] = content
                accepted.append((identity, content, normalized))
            except (ValueError, TypeError) as exc:
                errors.append({"row": line, "reason": str(exc)})
        target, fields = TARGETS[source]
        placeholders = ",".join("?" for _ in fields.split(","))
        with db_session() as conn:
            for identity, content, normalized in accepted:
                conn.execute("INSERT OR REPLACE INTO ods_record VALUES (?,?,?,?,?,?)",
                             (source, identity, batch_id, content, hashlib.sha256(content.encode()).hexdigest(), now_iso()))
                conn.execute(f"INSERT OR REPLACE INTO {target}({fields},source_batch) VALUES ({placeholders},?)", (*normalized, batch_id))
            checked = len(accepted) + len(errors)
            conn.execute("UPDATE etl_batch SET status=?,row_count=?,error_count=?,finished_at=?,message=? WHERE batch_id=?",
                         ("SUCCESS" if not errors else "PARTIAL", len(accepted), len(errors), now_iso(), json.dumps(errors[:100], ensure_ascii=False), batch_id))
            conn.execute("UPDATE etl_job SET last_status=?,last_run=? WHERE source_table=?",
                         ("SUCCESS" if not errors else "PARTIAL", now_iso(), source))
            _quality_row(conn, batch_id, "COMPLETENESS", "关键字段完整性与格式", checked, len(errors), started, json.dumps(errors[:20], ensure_ascii=False))
            duplicates = checked - len(seen) - len(errors)
            _quality_row(conn, batch_id, "UNIQUENESS", "业务主键唯一性", checked, max(0, duplicates), started, "重复记录已幂等去重")
        if rebuild:
            rebuild_warehouse()
        return {"batch_id": batch_id, "source_table": source, "row_count": len(accepted), "error_count": len(errors), "skipped_rows": skipped, "incremental": incremental, "errors": errors[:100]}
    except Exception as exc:
        with db_session() as conn:
            conn.execute("UPDATE etl_batch SET status='FAILED',finished_at=?,message=? WHERE batch_id=?", (now_iso(), str(exc)[:500], batch_id))
        raise


def import_with_retry(source: str, path: Path, rebuild=True, incremental=False, retry_limit=2):
    last_error = None
    for attempt in range(1, max(0, int(retry_limit)) + 2):
        try:
            result = import_file(source, path, rebuild=rebuild, incremental=incremental)
            result["attempts"] = attempt
            return result
        except Exception as exc:
            last_error = exc
            if attempt >= max(0, int(retry_limit)) + 1:
                break
            time.sleep(min(attempt * 0.2, 1.0))
    raise last_error


def _quality_row(conn, batch_id, code, name, checked, failed, started, details=""):
    conn.execute("INSERT INTO quality_result(batch_id,rule_code,rule_name,status,checked_rows,failed_rows,duration_ms,details,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                 (batch_id, code, name, "PASS" if failed == 0 else "FAIL", checked, failed, round((time.perf_counter()-started)*1000, 2), details, now_iso()))


THEME_TABLES = (
    "dws_outpatient_day", "dws_inpatient_day", "dws_revenue_day", "dws_drug_day",
    "dws_consumable_day", "dws_disease_day", "dws_resource_day", "dws_service_day",
)
BASE_ADS_CODES = (
    "K01", "K02", "K06", "K07", "K08", "K10", "K11", "K12", "K13", "K14",
    "K16", "K17", "K18", "K19", "K20", "K21", "K22", "K23", "K24", "K37", "K38", "K39",
)
EXTRA_ADS_CODES = ("K09", "K25", "K26", "K27", "K28", "K29", "K31", "K32")
ADS_CODES = BASE_ADS_CODES + EXTRA_ADS_CODES


def _ratio(numerator, denominator, multiplier=1.0):
    return round(numerator / denominator * multiplier, 4) if denominator else None


def _refresh_encounter_wide(conn):
    conn.execute("DELETE FROM dwd_encounter_wide")
    conn.execute("""
        WITH encounters AS (
            SELECT 'outpatient' source_type,visit_id encounter_id,patient_key,dept_code,
                   visit_date start_date,visit_date end_date,visit_type,
                   NULL disease_code,NULL diagnosis,fee_amount outpatient_fee,
                   0 inpatient_total_fee,0 drug_fee,0 consumable_fee,source_batch
            FROM dwd_outpatient_visit
            UNION ALL
            SELECT 'inpatient',visit_id,patient_key,dept_code,admit_date,discharge_date,
                   NULL,disease_code,NULL,0,total_fee,drug_fee,consumable_fee,source_batch
            FROM dwd_inpatient_stay
        ),
        charge_agg AS (
            SELECT visit_id,SUM(amount) amount,COUNT(*) items FROM dwd_charge_detail GROUP BY visit_id
        ),
        lis_agg AS (
            SELECT visit_id,COUNT(*) reports,SUM(CASE WHEN result_text IN ('异常','阳性') THEN 1 ELSE 0 END) abnormal
            FROM dwd_lis_report GROUP BY visit_id
        )
        INSERT INTO dwd_encounter_wide
        SELECT e.source_type,e.encounter_id,e.patient_key,e.dept_code,e.start_date,e.end_date,
               e.visit_type,COALESCE(e.disease_code,em.disease_code),COALESCE(e.diagnosis,em.diagnosis),
               e.outpatient_fee,e.inpatient_total_fee,e.drug_fee,e.consumable_fee,
               COALESCE(c.amount,0),COALESCE(c.items,0),COALESCE(l.reports,0),COALESCE(l.abnormal,0),
               e.source_batch
        FROM encounters e
        LEFT JOIN charge_agg c ON e.encounter_id=c.visit_id
        LEFT JOIN lis_agg l ON e.encounter_id=l.visit_id
        LEFT JOIN (SELECT visit_id,MAX(disease_code) disease_code,MAX(diagnosis) diagnosis FROM dwd_emr_record GROUP BY visit_id) em
          ON e.encounter_id=em.visit_id
    """)
    return conn.execute("SELECT COUNT(*) FROM dwd_encounter_wide").fetchone()[0]


def _refresh_dim_date(conn):
    bounds = conn.execute("SELECT MIN(stat_date),MAX(stat_date) FROM dws_dept_day").fetchone()
    conn.execute("DELETE FROM dim_date")
    if not bounds[0]:
        return 0
    cursor = date.fromisoformat(bounds[0])
    end = date.fromisoformat(bounds[1])
    rows = []
    while cursor <= end:
        iso = cursor.isocalendar()
        rows.append((cursor.isoformat(), cursor.year, (cursor.month-1)//3+1, cursor.month,
                     (cursor-timedelta(days=cursor.weekday())).isoformat(), iso.year, iso.week,
                     cursor.weekday()+1, int(cursor.weekday() >= 5)))
        cursor += timedelta(days=1)
    conn.executemany("INSERT INTO dim_date VALUES (?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


def _refresh_theme_marts(conn):
    for table in THEME_TABLES:
        conn.execute(f"DELETE FROM {table}")
    emergency = {(row[0], row[1]): row[2] for row in conn.execute(
        "SELECT visit_date,dept_code,COUNT(*) FROM dwd_outpatient_visit WHERE visit_type='急诊' GROUP BY 1,2"
    )}
    departments = {row["dept_code"]: row for row in conn.execute("SELECT * FROM dim_department")}
    counts = {table: 0 for table in THEME_TABLES}
    rows = conn.execute("SELECT * FROM dws_dept_day ORDER BY stat_date,dept_code").fetchall()
    for row in rows:
        day, dept = row["stat_date"], row["dept_code"]
        usage = _ratio(row["occupied_bed_days"], row["open_bed_days"], 100)
        avg_stay = _ratio(row["stay_days"], row["discharges"])
        turnover = _ratio(row["discharges"], row["open_bed_days"])
        drug_ratio = _ratio(row["drug_revenue"], row["total_revenue"], 100)
        consumable_ratio = _ratio(row["consumable_revenue"], row["total_revenue"], 100)
        abnormal_rate = _ratio(row["abnormal_lis_reports"], row["lis_reports"], 100)
        staff = (departments.get(dept) or {})["staff_count"] if dept in departments else 0
        beds = (departments.get(dept) or {})["bed_count"] if dept in departments else 0
        items = {
            "dws_outpatient_day": (day, dept, row["outpatient_visits"], row["outpatient_patients"],
                                   _ratio(row["outpatient_visits"]-row["outpatient_patients"], row["outpatient_visits"], 100),
                                   emergency.get((day, dept), 0)),
            "dws_inpatient_day": (day, dept, row["admissions"], row["discharges"], row["occupied_bed_days"],
                                  row["open_bed_days"], row["stay_days"], usage, avg_stay, turnover),
            "dws_revenue_day": (day, dept, row["outpatient_revenue"], row["inpatient_revenue"], row["total_revenue"]),
            "dws_drug_day": (day, dept, row["drug_revenue"], row["total_revenue"], drug_ratio),
            "dws_consumable_day": (day, dept, row["consumable_revenue"], row["total_revenue"], consumable_ratio),
            "dws_resource_day": (day, dept, beds, staff, usage, turnover,
                                 _ratio(row["outpatient_visits"], staff), _ratio(row["total_revenue"], staff)),
            "dws_service_day": (day, dept, row["lis_reports"], row["abnormal_lis_reports"], abnormal_rate),
        }
        for table, values in items.items():
            placeholders = ",".join("?" for _ in values)
            conn.execute(f"INSERT INTO {table} VALUES ({placeholders})", values)
            counts[table] += 1
    disease_rows = conn.execute("""
        SELECT discharge_date,dept_code,disease_code,COUNT(*),SUM(total_fee),SUM(stay_days)
        FROM dwd_inpatient_stay
        WHERE discharge_date IS NOT NULL AND disease_code IS NOT NULL AND disease_code!=''
        GROUP BY discharge_date,dept_code,disease_code
    """).fetchall()
    for row in disease_rows:
        conn.execute("INSERT INTO dws_disease_day VALUES (?,?,?,?,?,?,?,?)",
                     (*row, _ratio(row[4], row[3]), _ratio(row[5], row[3])))
        counts["dws_disease_day"] += 1
    return counts


def _period_key(day, grain):
    if grain == "week":
        return (day-timedelta(days=day.weekday())).isoformat()
    if grain == "month":
        return day.replace(day=1).isoformat()
    return day.isoformat()


def _period_bounds(day, grain):
    if grain == "week":
        start = day-timedelta(days=day.weekday())
        return start, start+timedelta(days=6)
    if grain == "month":
        start = day.replace(day=1)
        return start, (start+timedelta(days=32)).replace(day=1)-timedelta(days=1)
    return day, day


def _period_expr(column, grain):
    if grain == "week":
        return f"date({column}, '-' || ((CAST(strftime('%w', {column}) AS INTEGER)+6)%7) || ' days')"
    if grain == "month":
        return f"substr({column},1,7) || '-01'"
    return column


def _refresh_ads(conn, start=None, end=None, grains=("day", "week", "month"), dept_code=None):
    bounds = conn.execute("SELECT MIN(stat_date),MAX(stat_date) FROM dws_dept_day").fetchone()
    if not bounds[0]:
        return {}
    start = date.fromisoformat(start or bounds[0])
    end = date.fromisoformat(end or bounds[1])
    if start > end:
        raise ValueError("开始日期不能晚于结束日期")
    result = {}
    stamp = now_iso()
    for grain in grains:
        if grain not in ("day", "week", "month"):
            raise ValueError("ADS粒度仅支持day、week或month")
        effective_start, _ = _period_bounds(start, grain)
        _, effective_end = _period_bounds(end, grain)
        delete_sql = "DELETE FROM ads_metric_result WHERE grain=? AND stat_date BETWEEN ? AND ?"
        delete_params = [grain, effective_start.isoformat(), effective_end.isoformat()]
        if dept_code:
            delete_sql += " AND dept_code=?"
            delete_params.append(dept_code)
        conn.execute(delete_sql, delete_params)
        where = "stat_date BETWEEN ? AND ?"
        params = [effective_start.isoformat(), effective_end.isoformat()]
        if dept_code:
            where += " AND dept_code=?"
            params.append(dept_code)
        rows = conn.execute(f"""SELECT stat_date,dept_code,
            SUM(outpatient_visits),SUM(outpatient_revenue),SUM(admissions),SUM(discharges),
            SUM(inpatient_revenue),SUM(drug_revenue),SUM(consumable_revenue),SUM(total_revenue),
            SUM(stay_days),SUM(occupied_bed_days),SUM(open_bed_days),SUM(lis_reports),SUM(abnormal_lis_reports)
            FROM dws_dept_day WHERE {where} GROUP BY stat_date,dept_code""", params).fetchall()
        aggregates = {}
        dates = set()
        for row in rows:
            day = date.fromisoformat(row[0])
            period = _period_key(day, grain)
            dates.add(day)
            key = (period, row[1])
            if key not in aggregates:
                aggregates[key] = [0]*13
            for index, value in enumerate(row[2:]):
                aggregates[key][index] += value or 0
        global_rows = {}
        for (period, _dept), row in aggregates.items():
            if period not in global_rows:
                global_rows[period] = [0]*13
            for index, value in enumerate(row):
                global_rows[period][index] += value or 0
        date_counts = {}
        for day in dates:
            period = _period_key(day, grain)
            date_counts[period] = date_counts.get(period, 0)+1
        outpatient_where = where.replace("stat_date", "visit_date")
        outpatient_period = _period_expr("visit_date", grain)
        out_rows = conn.execute(f"SELECT {outpatient_period},dept_code,COUNT(DISTINCT patient_key) FROM dwd_outpatient_visit WHERE {outpatient_where} GROUP BY 1,2", params).fetchall()
        out_patients = {(row[0], row[1]): row[2] for row in out_rows}
        if not dept_code:
            out_all = conn.execute(f"SELECT {outpatient_period},COUNT(DISTINCT patient_key) FROM dwd_outpatient_visit WHERE {outpatient_where} GROUP BY 1", params).fetchall()
            for period, count in out_all:
                out_patients[(period, "ALL")] = count
        inpatient_where = where.replace("stat_date", "discharge_date")
        inpatient_period = _period_expr("discharge_date", grain)
        in_rows = conn.execute(f"SELECT {inpatient_period},dept_code,COUNT(DISTINCT patient_key) FROM dwd_inpatient_stay WHERE {inpatient_where} GROUP BY 1,2", params).fetchall()
        in_patients = {(row[0], row[1]): row[2] for row in in_rows}
        if not dept_code:
            in_all = conn.execute(f"SELECT {inpatient_period},COUNT(DISTINCT patient_key) FROM dwd_inpatient_stay WHERE {inpatient_where} GROUP BY 1", params).fetchall()
            for period, count in in_all:
                in_patients[(period, "ALL")] = count
        all_aggregates = dict(aggregates)
        if not dept_code:
            for period, values in global_rows.items():
                all_aggregates[(period, "ALL")] = values
        inserted = 0
        for (period, dept), values in all_aggregates.items():
            (visits, outpatient_revenue, admissions, discharges, inpatient_revenue, drug_revenue,
             consumable_revenue, total_revenue, stay_days, occupied_days, open_days, lis_reports, abnormal_reports) = values
            out_unique = out_patients.get((period, dept), 0)
            in_unique = in_patients.get((period, dept), 0)
            day_count = date_counts.get(period, 1)
            metrics = {
                "K01": visits, "K02": out_unique,
                "K06": _ratio(visits-out_unique, visits, 100),
                "K07": admissions, "K08": discharges, "K10": occupied_days, "K11": open_days,
                "K12": _ratio(occupied_days, open_days, 100), "K13": _ratio(stay_days, discharges),
                "K14": _ratio(discharges*day_count, open_days),
                "K16": total_revenue, "K17": outpatient_revenue, "K18": inpatient_revenue,
                "K19": _ratio(outpatient_revenue, visits), "K20": _ratio(inpatient_revenue, discharges),
                "K21": drug_revenue, "K22": _ratio(drug_revenue, total_revenue, 100),
                "K23": consumable_revenue, "K24": _ratio(consumable_revenue, total_revenue, 100),
                "K37": _ratio(visits, out_unique), "K38": _ratio(discharges, in_unique),
                "K39": _ratio(abnormal_reports, lis_reports, 100),
            }
            for code in BASE_ADS_CODES:
                conn.execute("INSERT OR REPLACE INTO ads_metric_result VALUES (?,?,?,?,?,?,?)",
                             (code, period, grain, dept, metrics[code], "SYSTEM-ADS", stamp))
                inserted += 1
            # 复杂指标复用统一指标服务，避免在ADS层复制一套公式。
            from app.services.analytics import metric_summary
            user = {"username": "SYSTEM", "role": "admin", "dept_codes": []}
            _, period_end = _period_bounds(date.fromisoformat(period), grain)
            period_end = min(period_end, effective_end).isoformat()
            for code in EXTRA_ADS_CODES:
                value = metric_summary(code, period, period_end, user, None if dept == "ALL" else dept, conn)
                conn.execute("INSERT OR REPLACE INTO ads_metric_result VALUES (?,?,?,?,?,?,?)",
                             (code, period, grain, dept, value, "SYSTEM-ADS", stamp))
                inserted += 1
        result[grain] = {"rows": inserted, "start": effective_start.isoformat(), "end": effective_end.isoformat()}
    return result


def refresh_ads(start=None, end=None, grains=("day", "week", "month"), dept_code=None):
    init_db()
    with db_session() as conn:
        return _refresh_ads(conn, start, end, grains, dept_code)


def rebuild_warehouse():
    init_db()
    with db_session() as conn:
        conn.execute("DELETE FROM dws_dept_day")
        conn.execute("DELETE FROM dws_disease")
        conn.execute("DELETE FROM ads_metric_result")
        wide_rows = _refresh_encounter_wide(conn)
        conn.execute("""
            INSERT INTO dws_disease
            SELECT disease_code,dept_code,COUNT(*),SUM(total_fee),SUM(stay_days)
            FROM dwd_inpatient_stay WHERE discharge_date IS NOT NULL AND disease_code IS NOT NULL
            GROUP BY disease_code,dept_code
        """)
        rows = {}
        def item(day, dept):
            key = (day, dept)
            if key not in rows:
                rows[key] = dict.fromkeys(("outpatient_visits", "outpatient_patients", "outpatient_revenue", "admissions", "discharges", "inpatient_revenue", "drug_revenue", "consumable_revenue", "total_revenue", "stay_days", "occupied_bed_days", "open_bed_days", "lis_reports", "abnormal_lis_reports"), 0)
            return rows[key]
        for row in conn.execute("SELECT visit_date,dept_code,COUNT(*) n,COUNT(DISTINCT patient_key) p,SUM(fee_amount) fee FROM dwd_outpatient_visit GROUP BY 1,2"):
            item(row[0], row[1]).update(outpatient_visits=row[2], outpatient_patients=row[3])
        for row in conn.execute("SELECT fee_date,dept_code,visit_type,fee_type_code,SUM(amount) amount FROM dwd_charge_detail GROUP BY 1,2,3,4"):
            target = item(row[0], row[1])
            target["total_revenue"] += row[4] or 0
            if row[2] == "门诊": target["outpatient_revenue"] += row[4] or 0
            if row[2] == "住院": target["inpatient_revenue"] += row[4] or 0
            if row[3] in ("XY", "ZC"): target["drug_revenue"] += row[4] or 0
            if row[3] == "CL": target["consumable_revenue"] += row[4] or 0
        for row in conn.execute("SELECT admit_date,discharge_date,dept_code,stay_days,total_fee FROM dwd_inpatient_stay"):
            admit, discharge = date.fromisoformat(row[0]), date.fromisoformat(row[1])
            item(row[0], row[2])["admissions"] += 1
            target = item(row[1], row[2])
            target["discharges"] += 1
            target["stay_days"] += row[3] or 0
            days = max((discharge-admit).days, 1)
            cursor = admit
            while cursor < discharge:
                item(cursor.isoformat(), row[2])["occupied_bed_days"] += 1
                cursor += timedelta(days=1)
            if days == 1 and admit == discharge:
                item(row[0], row[2])["occupied_bed_days"] += 1
        # LIS 按关联就诊科室汇总；未关联记录不进入科室指标。
        lis_sql = """SELECT l.report_date,COALESCE(o.dept_code,i.dept_code) dept,COUNT(*) n,
                     SUM(CASE WHEN l.result_text IN ('异常','阳性') THEN 1 ELSE 0 END) abnormal
                     FROM dwd_lis_report l LEFT JOIN dwd_outpatient_visit o ON l.visit_id=o.visit_id
                     LEFT JOIN dwd_inpatient_stay i ON l.visit_id=i.visit_id
                     WHERE COALESCE(o.dept_code,i.dept_code) IS NOT NULL GROUP BY 1,2"""
        for row in conn.execute(lis_sql):
            item(row[0], row[1]).update(lis_reports=row[2], abnormal_lis_reports=row[3] or 0)
        beds = {row[0]: row[1] for row in conn.execute("SELECT dept_code,bed_count FROM dim_department")}
        for (day, dept), values in rows.items():
            values["open_bed_days"] = beds.get(dept, 0)
            conn.execute("INSERT INTO dws_dept_day VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                         (day, dept, *values.values()))
        dim_date_rows = _refresh_dim_date(conn)
        theme_counts = _refresh_theme_marts(conn)
        ads = _refresh_ads(conn)
    return {"dws_rows": len(rows), "dwd_wide_rows": wide_rows, "dim_date_rows": dim_date_rows, "theme_marts": theme_counts, "ads": ads}


def run_all(incremental=False, retry_limit=2):
    init_db()
    results = []
    for source, spec in SOURCES.items():
        results.append(import_with_retry(source, DATA_DIR / spec["path"], rebuild=False, incremental=incremental, retry_limit=retry_limit))
    stats = rebuild_warehouse()
    return {"sources": results, "incremental": incremental, **stats}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="执行六源全量/增量ETL并重建DWS/ADS")
    parser.add_argument("--incremental", action="store_true", help="按各DWD表最大日期只处理新记录")
    parser.add_argument("--retry-limit", type=int, default=2, help="单个数据源失败后的重试次数")
    args = parser.parse_args()
    print(json.dumps(run_all(incremental=args.incremental, retry_limit=args.retry_limit), ensure_ascii=False, indent=2))
