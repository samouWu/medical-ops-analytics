import argparse
import csv
import json
import sqlite3
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SOURCES = {
    "his_outpatient": ("mock_his/his_outpatient.csv", "dwd_outpatient_visit", "visit_id"),
    "his_inpatient": ("mock_his/his_inpatient.csv", "dwd_inpatient_stay", "visit_id"),
    "his_charge": ("mock_his/his_charge.csv", "dwd_charge_detail", "charge_id"),
    "emr_record": ("mock_his/emr_record.csv", "dwd_emr_record", "record_id"),
    "lis_report": ("mock_his/lis_report.csv", "dwd_lis_report", "report_id"),
    "finance_excel": ("files/finance_excel.csv", "dwd_finance_day", "record_id"),
}


def count_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return sum(1 for _ in csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description="源文件、DWD、DWS、ADS全链路对账")
    parser.add_argument("--data-dir", default=str(PROJECT / "data"))
    parser.add_argument("--db", default=str(PROJECT / "data/derived/medical_ops.db"))
    parser.add_argument("--output", default=str(PROJECT / "data/derived/reconciliation_report.json"))
    args = parser.parse_args()
    data_dir = Path(args.data_dir)
    database = Path(args.db)
    if not database.exists():
        raise SystemExit(f"数据库不存在：{database}")
    checks = []
    with sqlite3.connect(database) as conn:
        for source, (relative, table, key) in SOURCES.items():
            csv_rows = count_csv(data_dir / relative)
            db_rows = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            distinct = conn.execute(f"SELECT COUNT(DISTINCT {key}) FROM {table}").fetchone()[0]
            checks.append({"check": f"{source}_row_count", "source": csv_rows, "database": db_rows, "distinct_key": distinct,
                           "passed": csv_rows == db_rows == distinct, "detail": f"{table}.{key}"})
        outpatient = conn.execute("SELECT COUNT(*) FROM dwd_outpatient_visit").fetchone()[0]
        inpatient = conn.execute("SELECT COUNT(*) FROM dwd_inpatient_stay WHERE discharge_date IS NOT NULL").fetchone()[0]
        charge = conn.execute("SELECT ROUND(COALESCE(SUM(amount),0),2) FROM dwd_charge_detail").fetchone()[0]
        dws_visits = conn.execute("SELECT SUM(outpatient_visits) FROM dws_dept_day").fetchone()[0] or 0
        dws_discharges = conn.execute("SELECT SUM(discharges) FROM dws_dept_day").fetchone()[0] or 0
        dws_revenue = round(conn.execute("SELECT SUM(total_revenue) FROM dws_dept_day").fetchone()[0] or 0, 2)
        ads_revenue = round(conn.execute("SELECT SUM(value_num) FROM ads_metric_result WHERE metric_code='K16' AND grain='month' AND dept_code='ALL'").fetchone()[0] or 0, 2)
        ads_visits = conn.execute("SELECT SUM(value_num) FROM ads_metric_result WHERE metric_code='K01' AND grain='month' AND dept_code='ALL'").fetchone()[0] or 0
        for name, source_value, warehouse_value, note in [
            ("K01_source_dws", outpatient, dws_visits, "门诊记录数 vs DWS门诊人次"),
            ("K08_source_dws", inpatient, dws_discharges, "有出院日期住院记录 vs DWS出院人次"),
            ("K16_source_dws", charge, dws_revenue, "收费明细金额 vs DWS总收入"),
            ("K16_dws_ads", dws_revenue, ads_revenue, "DWS总收入 vs ADS月度全院合计"),
            ("K01_dws_ads", dws_visits, ads_visits, "DWS门诊人次 vs ADS月度全院合计"),
        ]:
            checks.append({"check": name, "source": source_value, "database": warehouse_value, "passed": round(float(source_value), 2) == round(float(warehouse_value), 2), "detail": note})
        theme_total = conn.execute("SELECT COUNT(*) FROM dws_outpatient_day").fetchone()[0]
        grains = dict(conn.execute("SELECT grain,COUNT(*) FROM ads_metric_result GROUP BY grain").fetchall())
        metric_count = conn.execute("SELECT COUNT(DISTINCT metric_code) FROM ads_metric_result").fetchone()[0]
    failed = [item for item in checks if not item["passed"]]
    report = {
        "database": str(database),
        "data_dir": str(data_dir),
        "checks": checks,
        "summary": {"total": len(checks), "passed": len(checks)-len(failed), "failed": len(failed)},
        "ads_grains": grains,
        "ads_metric_count": metric_count,
        "theme_day_rows": theme_total,
        "conclusion": "PASS" if not failed else "FAIL",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("database", "summary", "ads_grains", "ads_metric_count", "theme_day_rows", "conclusion")}, ensure_ascii=False, indent=2))
    if failed:
        print(json.dumps(failed, ensure_ascii=False, indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
