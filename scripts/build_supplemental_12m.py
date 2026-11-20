"""生成12个月附加模拟数据集，并在独立SQLite库中验证ETL与ADS。

原始2025-04-01至2025-06-30六源数据保持不变；仅向后扩展9个月。
输出目录和数据库与主平台完全隔离，不进入当前主题页面或主库。
"""
import argparse
import csv
import hashlib
import json
import os
import random
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SOURCE_DATA = PROJECT / "data"
DEFAULT_OUTPUT = PROJECT / "data" / "supplemental_12m"
END_DATE = date(2026, 3, 31)
SEED = 20261120
RNG = random.Random(SEED)

DEPARTMENTS = ["HN", "HX", "XH", "SJ", "GK", "PW", "FC", "EK", "JZ", "ICU"]
DISEASES = {
    "I10": "原发性高血压", "N18": "慢性肾脏病", "J18": "肺炎", "E11": "糖尿病",
    "J44": "慢阻肺", "K35": "急性阑尾炎", "A09": "感染性腹泻",
    "I25": "慢性缺血性心脏病", "I63": "脑梗死", "C16": "胃癌",
}
LIS_ITEMS = ["肾功能", "血脂", "血常规", "尿常规", "血糖", "电解质", "凝血功能", "肝功能"]
LIS_RESULTS = ["阴性", "未见异常", "正常", "在参考范围内", "阳性", "偏低", "异常", "偏高"]
FEE_TYPES = {
    "XY": "西药费", "ZC": "中成药费", "JC": "检查费", "JY": "检验费",
    "ZL": "治疗费", "SS": "手术费", "CL": "材料费", "CW": "床位费", "HL": "护理费",
}


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def write_rows(path, headers, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def jitter(value, low=0.88, high=1.12):
    return round(float(value) * RNG.uniform(low, high), 2)


def make_outpatient_patients(count=6000):
    patients = []
    for index in range(1, count + 1):
        patients.append({
            "patient_id": f"SIM-OP-{index:06d}",
            "patient_name": f"模拟门诊患者{index:05d}",
            "id_card": f"SIMIDOP{index:011d}",
            "phone": f"SIMPHOP{index:010d}",
            "gender": "男" if RNG.random() < 0.49 else "女",
            "age": RNG.randint(18, 88),
        })
    return patients


def make_inpatient_patients(count=1800):
    patients = []
    for index in range(1, count + 1):
        patients.append({
            "patient_id": f"SIM-IP-{index:06d}",
            "patient_name": f"模拟住院患者{index:05d}",
            "id_card": f"SIMIDIP{index:011d}",
            "phone": f"SIMPHIP{index:010d}",
            "gender": "男" if RNG.random() < 0.5 else "女",
            "age": RNG.randint(1, 92),
        })
    return patients


def build_templates(outpatient, inpatient, charges):
    visit_info = {row["visit_id"]: row for row in outpatient}
    charges_by_visit = defaultdict(list)
    for row in charges:
        charges_by_visit[row["visit_id"]].append(row)
    outpatient_templates = defaultdict(list)
    inpatient_templates = defaultdict(list)
    for row in outpatient:
        key = (row["dept_code"], row["visit_type"])
        if charges_by_visit.get(row["visit_id"]):
            outpatient_templates[key].append((row, charges_by_visit[row["visit_id"]]))
    for row in inpatient:
        if charges_by_visit.get(row["visit_id"]):
            inpatient_templates[row["dept_code"]].append((row, charges_by_visit[row["visit_id"]]))
    return visit_info, outpatient_templates, inpatient_templates


def generate(args):
    output = Path(args.output).resolve()
    data_root = output
    if output == SOURCE_DATA or SOURCE_DATA in output.parents and output.name != "supplemental_12m":
        raise ValueError("拒绝写入主数据目录；必须是独立的 supplemental_12m 目录")
    data_root.mkdir(parents=True, exist_ok=True)

    paths = {
        "his_outpatient": SOURCE_DATA / "mock_his" / "his_outpatient.csv",
        "his_inpatient": SOURCE_DATA / "mock_his" / "his_inpatient.csv",
        "his_charge": SOURCE_DATA / "mock_his" / "his_charge.csv",
        "emr_record": SOURCE_DATA / "mock_his" / "emr_record.csv",
        "lis_report": SOURCE_DATA / "mock_his" / "lis_report.csv",
        "finance_excel": SOURCE_DATA / "files" / "finance_excel.csv",
    }
    headers = {name: read_rows(path)[0] for name, path in paths.items()}
    original = {name: read_rows(path)[1] for name, path in paths.items()}
    outpatient = original["his_outpatient"]
    inpatient = original["his_inpatient"]
    charges = original["his_charge"]
    visit_info, outpatient_templates, inpatient_templates = build_templates(outpatient, inpatient, charges)
    type_by_dept = defaultdict(Counter)
    for row in outpatient:
        type_by_dept[row["dept_code"]][row["visit_type"]] += 1
    op_patients = make_outpatient_patients()
    ip_patients = make_inpatient_patients()

    extension_start = date(2025, 7, 1)
    generated = {key: [] for key in original}
    op_charge_seq = ip_charge_seq = 1
    ov_seq = iv_seq = emr_seq = lis_seq = fin_seq = 1
    day = extension_start
    while day <= END_DATE:
        day_text = day.isoformat()
        for dept in DEPARTMENTS:
            # 门诊：沿用原始每科约9.9人次/日，随机9或10人次。
            for _ in range(RNG.choice([9, 10])):
                patient = RNG.choice(op_patients)
                visit_type = RNG.choices(list(type_by_dept[dept]), weights=list(type_by_dept[dept].values()), k=1)[0]
                template_pool = outpatient_templates.get((dept, visit_type)) or outpatient_templates.get((dept, "普通"))
                if not template_pool:
                    continue
                template, template_charges = RNG.choice(template_pool)
                visit_id = f"12M-OV-{ov_seq:07d}"
                ov_seq += 1
                fee = jitter(template["fee_amount"])
                generated["his_outpatient"].append({
                    "visit_id": visit_id, "patient_id": patient["patient_id"], "patient_name": patient["patient_name"],
                    "id_card": patient["id_card"], "phone": patient["phone"], "gender": patient["gender"], "age": patient["age"],
                    "dept_code": dept, "visit_date": day_text, "visit_type": visit_type, "fee_amount": f"{fee:.2f}",
                })
                for charge in template_charges:
                    generated["his_charge"].append({
                        "charge_id": f"12M-OC-{op_charge_seq:08d}", "visit_id": visit_id,
                        "patient_id": patient["patient_id"], "visit_type": "门诊", "dept_code": dept,
                        "fee_date": day_text, "fee_type_code": charge["fee_type_code"],
                        "fee_type_name": charge["fee_type_name"], "amount": f"{jitter(charge['amount']):.2f}",
                    })
                    op_charge_seq += 1

            # 住院：每科每日1—2人，保持原数据约1.65人/日/科。
            for _ in range(2 if RNG.random() < 0.65 else 1):
                templates = inpatient_templates.get(dept, [])
                if not templates:
                    continue
                template, template_charges = RNG.choice(templates)
                patient = RNG.choice(ip_patients)
                los = max(0, int(round(float(template["stay_days"]) + RNG.gauss(0, 2))))
                admit = day
                discharge = min(admit + timedelta(days=los), END_DATE)
                stay_days = max(0, (discharge - admit).days)
                visit_id = f"12M-IV-{iv_seq:07d}"
                iv_seq += 1
                disease = template["disease_code"] if template["disease_code"] in DISEASES else RNG.choice(list(DISEASES))
                generated["his_inpatient"].append({
                    "visit_id": visit_id, "patient_id": patient["patient_id"], "patient_name": patient["patient_name"],
                    "id_card": patient["id_card"], "phone": patient["phone"], "gender": patient["gender"], "age": patient["age"],
                    "dept_code": dept, "bed_no": f"{dept}{RNG.randint(1, 60):02d}", "admit_date": admit.isoformat(),
                    "discharge_date": discharge.isoformat(), "stay_days": str(stay_days),
                    "total_fee": f"{jitter(template['total_fee']):.2f}",
                    "drug_fee": f"{jitter(template['drug_fee']):.2f}",
                    "consumable_fee": f"{jitter(template['consumable_fee']):.2f}",
                    "disease_code": disease,
                })
                generated["emr_record"].append({
                    "record_id": f"12M-EMR-{emr_seq:07d}", "patient_id": patient["patient_id"], "visit_id": visit_id,
                    "dept_code": dept, "visit_date": admit.isoformat(),
                    "diagnosis": f"{DISEASES[disease]};主诉:因不适入院诊治", "disease_code": disease,
                })
                emr_seq += 1
                for _ in range(RNG.choice([1, 2, 2, 3])):
                    report_offset = RNG.randint(0, max(stay_days, 0))
                    generated["lis_report"].append({
                        "report_id": f"12M-LIS-{lis_seq:07d}", "patient_id": patient["patient_id"], "visit_id": visit_id,
                        "item_name": RNG.choice(LIS_ITEMS), "result_text": RNG.choice(LIS_RESULTS),
                        "report_date": (admit + timedelta(days=report_offset)).isoformat(),
                    })
                    lis_seq += 1
                for charge in template_charges:
                    offset = RNG.randint(0, max(stay_days, 0))
                    generated["his_charge"].append({
                        "charge_id": f"12M-IC-{ip_charge_seq:08d}", "visit_id": visit_id,
                        "patient_id": patient["patient_id"], "visit_type": "住院", "dept_code": dept,
                        "fee_date": (admit + timedelta(days=offset)).isoformat(),
                        "fee_type_code": charge["fee_type_code"], "fee_type_name": charge["fee_type_name"],
                        "amount": f"{jitter(charge['amount']):.2f}",
                    })
                    ip_charge_seq += 1
        day += timedelta(days=1)

    # 财务：每个科室每日一行，围绕原始均值做季节和随机波动。
    finance_by_dept = defaultdict(list)
    for row in original["finance_excel"]:
        finance_by_dept[row["dept_code"]].append(row)
    day = extension_start
    while day <= END_DATE:
        month_factor = 1 + 0.08 * ((day.month % 6) - 2.5) / 2.5
        for dept in DEPARTMENTS:
            template = RNG.choice(finance_by_dept[dept])
            revenue = max(1, float(template["revenue"]) * month_factor * RNG.uniform(0.9, 1.1))
            drug_ratio = float(template["drug_revenue"]) / max(float(template["revenue"]), 1)
            consumable_ratio = float(template["consumable_revenue"]) / max(float(template["revenue"]), 1)
            generated["finance_excel"].append({
                "record_id": f"12M-FIN-{fin_seq:07d}", "stat_date": day.isoformat(), "dept_code": dept,
                "revenue": f"{revenue:.2f}", "drug_revenue": f"{revenue * drug_ratio * RNG.uniform(0.92, 1.08):.2f}",
                "consumable_revenue": f"{revenue * consumable_ratio * RNG.uniform(0.92, 1.08):.2f}",
            })
            fin_seq += 1
        day += timedelta(days=1)

    primary_keys = {
        "his_outpatient": "visit_id", "his_inpatient": "visit_id", "his_charge": "charge_id",
        "emr_record": "record_id", "lis_report": "report_id", "finance_excel": "record_id",
    }
    output_files = {}
    for name, header in headers.items():
        rows = original[name] + generated[name]
        keys = [row[primary_keys[name]] for row in rows]
        if len(keys) != len(set(keys)):
            raise AssertionError(f"生成数据业务主键重复: {name}")
        target = data_root / ("files/finance_excel.csv" if name == "finance_excel" else f"mock_his/{name}.csv")
        write_rows(target, header, rows)
        output_files[name] = {"path": str(target.relative_to(output)), "rows": len(rows), "generated_extension_rows": len(generated[name]), "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}

    manifest = {
        "seed": SEED,
        "generated_at": "2026-11-20",
        "range": {"start": "2025-04-01", "end": END_DATE.isoformat(), "months": 12},
        "real_data_range": {"start": "2025-04-01", "end": "2025-06-30"},
        "simulated_extension_range": {"start": extension_start.isoformat(), "end": END_DATE.isoformat()},
        "note": "前3个月为课程给定数据，后9个月为基于原模板的确定性模拟扩展；不得当作真实医院数据。",
        "files": output_files,
    }
    (data_root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return output, manifest


def run_etl(output):
    db_path = output / "derived" / "supplemental_12m.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    for suffix in ("", "-wal", "-shm"):
        Path(str(db_path) + suffix).unlink(missing_ok=True)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PROJECT / "backend")
    env["MEDICAL_DATA_DIR"] = str(output)
    env["MEDICAL_DB_PATH"] = str(db_path)
    result = subprocess.run(
        [sys.executable, "-m", "etl.jobs.pipeline"],
        cwd=PROJECT, env=env, check=True, capture_output=True, text=True,
    )
    return db_path, json.loads(result.stdout)


def summarize(database):
    import sqlite3
    with sqlite3.connect(database) as conn:
        bounds = conn.execute("SELECT MIN(stat_date),MAX(stat_date),COUNT(DISTINCT substr(stat_date,1,7)) FROM dws_dept_day").fetchone()
        monthly = [{"month": row[0], "days": row[1], "outpatient_visits": int(row[2]), "discharges": int(row[3]), "revenue": round(row[4], 2)}
                   for row in conn.execute("""
                       SELECT substr(stat_date,1,7),COUNT(DISTINCT stat_date),SUM(outpatient_visits),SUM(discharges),SUM(total_revenue)
                       FROM dws_dept_day GROUP BY 1 ORDER BY 1
                   """)]
        grains = dict(conn.execute("SELECT grain,COUNT(*) FROM ads_metric_result GROUP BY grain").fetchall())
        themes = conn.execute("SELECT COUNT(*) FROM dws_outpatient_day").fetchone()[0]
        metric_count = conn.execute("SELECT COUNT(*) FROM metric_definition").fetchone()[0]
    return {
        "database": str(database),
        "date_range": {"start": bounds[0], "end": bounds[1]},
        "month_count": bounds[2],
        "monthly": monthly,
        "ads_grains": grains,
        "theme_rows": themes,
        "metric_definitions": metric_count,
    }


def main():
    parser = argparse.ArgumentParser(description="生成并独立验证12个月附加模拟数据")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--skip-etl", action="store_true")
    args = parser.parse_args()
    output, manifest = generate(args)
    summary = {"dataset": manifest, "etl": None}
    if not args.skip_etl:
        db_path, etl_result = run_etl(output)
        summary["etl"] = etl_result
        summary["verification"] = summarize(db_path)
        (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        with (output / "monthly_summary.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["month", "days", "outpatient_visits", "discharges", "revenue"])
            for row in summary["verification"]["monthly"]:
                writer.writerow([row["month"], row["days"], row["outpatient_visits"], row["discharges"], row["revenue"]])
    print(json.dumps({
        "output": str(output),
        "dataset_rows": sum(item["rows"] for item in manifest["files"].values()),
        "original_rows": sum(item["rows"] - item["generated_extension_rows"] for item in manifest["files"].values()),
        "extension_rows": sum(item["generated_extension_rows"] for item in manifest["files"].values()),
        "verification": summary.get("verification"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
