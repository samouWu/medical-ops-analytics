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


def sum_csv(path, column, predicate=None):
    total = 0.0
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if predicate and not predicate(row):
                continue
            total += float(row[column] or 0)
    return round(total, 2)


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
        dws_visits = conn.execute("SELECT SUM(outpatient_visits) FROM dws_dept_day").fetchone()[0] or 0
        dws_discharges = conn.execute("SELECT SUM(discharges) FROM dws_dept_day").fetchone()[0] or 0
        dws_outpatient_revenue = round(conn.execute("SELECT SUM(outpatient_revenue) FROM dws_dept_day").fetchone()[0] or 0, 2)
        dws_inpatient_revenue = round(conn.execute("SELECT SUM(inpatient_revenue) FROM dws_dept_day").fetchone()[0] or 0, 2)
        dws_revenue = round(conn.execute("SELECT SUM(total_revenue) FROM dws_dept_day").fetchone()[0] or 0, 2)
        dws_occupied = conn.execute("SELECT SUM(occupied_bed_days) FROM dws_dept_day").fetchone()[0] or 0
        dws_drug = round(conn.execute("SELECT SUM(drug_revenue) FROM dws_dept_day").fetchone()[0] or 0, 2)
        dws_consumable = round(conn.execute("SELECT SUM(consumable_revenue) FROM dws_dept_day").fetchone()[0] or 0, 2)
        ads_revenue = round(conn.execute("SELECT SUM(value_num) FROM ads_metric_result WHERE metric_code='K16' AND grain='month' AND dept_code='ALL'").fetchone()[0] or 0, 2)
        ads_visits = conn.execute("SELECT SUM(value_num) FROM ads_metric_result WHERE metric_code='K01' AND grain='month' AND dept_code='ALL'").fetchone()[0] or 0
        ads_occupied = conn.execute("SELECT SUM(value_num) FROM ads_metric_result WHERE metric_code='K10' AND grain='month' AND dept_code='ALL'").fetchone()[0] or 0
        ads_open = conn.execute("SELECT SUM(value_num) FROM ads_metric_result WHERE metric_code='K11' AND grain='month' AND dept_code='ALL'").fetchone()[0] or 0
        ads_usage = round(ads_occupied / ads_open * 100, 4) if ads_open else 0
        # 账单口径：门诊收费单金额 + 住院结算总费用
        outpatient_fee = sum_csv(data_dir / "mock_his/his_outpatient.csv", "fee_amount")
        inpatient_fee = sum_csv(data_dir / "mock_his/his_inpatient.csv", "total_fee")
        stay_days = sum_csv(data_dir / "mock_his/his_inpatient.csv", "stay_days")
        charge_drug = sum_csv(data_dir / "mock_his/his_charge.csv", "amount", lambda row: row["fee_type_code"] in ("XY", "ZC"))
        charge_consumable = sum_csv(data_dir / "mock_his/his_charge.csv", "amount", lambda row: row["fee_type_code"] == "CL")
        expected_usage = round(stay_days / (345 * 91) * 100, 4)
        for name, source_value, warehouse_value, note in [
            ("K01_source_dws", outpatient, dws_visits, "门诊记录数 vs DWS门诊人次"),
            ("K08_source_dws", inpatient, dws_discharges, "有出院日期住院记录 vs DWS出院人次"),
            ("K16_source_dws", round(outpatient_fee + inpatient_fee, 2), dws_revenue, "门诊账单+住院结算 vs DWS总收入"),
            ("K17_source_dws", outpatient_fee, dws_outpatient_revenue, "门诊收费单金额 vs DWS门诊收入"),
            ("K18_source_dws", inpatient_fee, dws_inpatient_revenue, "住院结算总费用 vs DWS住院收入"),
            ("K10_source_dws", stay_days, dws_occupied, "源住院天数合计 vs DWS实际占用床日"),
            ("K21_source_dws", charge_drug, dws_drug, "收费明细药品金额 vs DWS药品收入"),
            ("K23_source_dws", charge_consumable, dws_consumable, "收费明细材料金额 vs DWS耗材收入"),
            ("K12_source_ads", expected_usage, ads_usage, "14,317床日/(345床×91天) vs ADS月度床日汇总"),
            ("K16_dws_ads", dws_revenue, ads_revenue, "DWS总收入 vs ADS月度全院合计"),
            ("K01_dws_ads", dws_visits, ads_visits, "DWS门诊人次 vs ADS月度全院合计"),
        ]:
            checks.append({"check": name, "source": source_value, "database": warehouse_value, "passed": round(float(source_value), 2) == round(float(warehouse_value), 2), "detail": note})
        # 新增指标：用源明细独立复算，再与 ADS 月度值按分母加权核对，避免只查行数不查数值。
        ratio_specs = [
            ("K41", "SELECT SUM(visit_type='急诊'),COUNT(*) FROM dwd_outpatient_visit", "K01", 100),
            ("K42", "SELECT SUM(drug_fee),SUM(total_fee) FROM dwd_inpatient_stay", "K18", 100),
            ("K43", "SELECT SUM(consumable_fee),SUM(total_fee) FROM dwd_inpatient_stay", "K18", 100),
            ("K44", "SELECT SUM(total_fee),SUM(stay_days) FROM dwd_inpatient_stay", "K10", 1),
            ("K46", "SELECT SUM(stay_days=0),COUNT(*) FROM dwd_inpatient_stay", "K08", 100),
            ("K48", """SELECT SUM(EXISTS(SELECT 1 FROM dwd_emr_record e WHERE e.visit_id=i.visit_id)),COUNT(*) FROM dwd_inpatient_stay i""", "K08", 100),
            ("K49", """SELECT SUM(EXISTS(SELECT 1 FROM dwd_lis_report l WHERE l.visit_id=i.visit_id)),COUNT(*) FROM dwd_inpatient_stay i""", "K08", 100),
        ]
        for code, sql, weight_code, multiplier in ratio_specs:
            numerator, denominator = conn.execute(sql).fetchone()
            source_value = round((numerator or 0)/denominator*multiplier, 4) if denominator else None
            if code in ("K42", "K43", "K44"):
                # 这三个指标按出院队列计算，权重必须是同月出院患者的结算费用/住院天数，
                # 不能使用按住院日分摊的 K18 或跨期占用的 K10。
                weight_column = "stay_days" if code == "K44" else "total_fee"
                weight_sql = f"SELECT substr(discharge_date,1,7) m,SUM({weight_column}) w FROM dwd_inpatient_stay GROUP BY 1"
                ads_value = conn.execute(f"""SELECT SUM(a.value_num*w.w)/SUM(w.w)
                    FROM ads_metric_result a JOIN ({weight_sql}) w ON w.m=substr(a.stat_date,1,7)
                    WHERE a.metric_code=? AND a.grain='month' AND a.dept_code='ALL'""", (code,)).fetchone()[0]
            else:
                ads_value = conn.execute("""SELECT SUM(a.value_num*w.value_num)/SUM(w.value_num)
                    FROM ads_metric_result a JOIN ads_metric_result w
                    ON w.stat_date=a.stat_date AND w.grain=a.grain AND w.dept_code=a.dept_code
                    WHERE a.metric_code=? AND w.metric_code=? AND a.grain='month' AND a.dept_code='ALL'""", (code, weight_code)).fetchone()[0]
            passed = source_value is not None and ads_value is not None and abs(source_value-ads_value) < 0.02
            checks.append({"check": f"{code}_source_ads", "source": source_value, "database": round(ads_value, 4) if ads_value is not None else None,
                           "passed": passed, "detail": f"源明细独立复算 vs ADS按{weight_code}分母加权"})

        # 日均在院人数：月度值按每月天数加权，必须等于全期占用床日/91天。
        source_daily_census = round(dws_occupied/91, 4)
        ads_daily_census = conn.execute("""SELECT SUM(a.value_num*(SELECT COUNT(*) FROM dim_date d WHERE substr(d.date_key,1,7)=substr(a.stat_date,1,7))) /
            SUM((SELECT COUNT(*) FROM dim_date d WHERE substr(d.date_key,1,7)=substr(a.stat_date,1,7)))
            FROM ads_metric_result a WHERE a.metric_code='K45' AND a.grain='month' AND a.dept_code='ALL'""").fetchone()[0]
        checks.append({"check": "K45_source_ads", "source": source_daily_census, "database": round(ads_daily_census, 4),
                       "passed": abs(source_daily_census-ads_daily_census) < 0.02, "detail": "全期占用床日/91天 vs ADS月度日均在院按天数加权"})

        # 30天再入院率：按每月具有完整观察窗的出院人次加权，6月无完整窗口不参与。
        obs = conn.execute("""WITH observed AS (
            SELECT substr(a.discharge_date,1,7) month_key, COUNT(*) n FROM dwd_inpatient_stay a
            WHERE a.discharge_date<=(SELECT date(MAX(discharge_date),'-30 day') FROM dwd_inpatient_stay) GROUP BY 1)
            SELECT SUM(a.value_num*observed.n)/SUM(observed.n) FROM ads_metric_result a
            JOIN observed ON observed.month_key=substr(a.stat_date,1,7)
            WHERE a.metric_code='K47' AND a.grain='month' AND a.dept_code='ALL'""").fetchone()[0]
        readmit = conn.execute("""SELECT SUM(EXISTS(SELECT 1 FROM dwd_inpatient_stay b
            WHERE b.patient_key=a.patient_key AND b.admit_date>a.discharge_date AND b.admit_date<=date(a.discharge_date,'+30 day'))),COUNT(*)
            FROM dwd_inpatient_stay a
            WHERE a.discharge_date<=(SELECT date(MAX(discharge_date),'-30 day') FROM dwd_inpatient_stay)""").fetchone()
        source_readmit = round(readmit[0]/readmit[1]*100, 4) if readmit[1] else None
        checks.append({"check": "K47_source_ads", "source": source_readmit, "database": round(obs, 4),
                       "passed": abs(source_readmit-obs) < 0.02, "detail": "完整观察窗内30天再入院 vs ADS按观察窗出院人次加权"})

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
