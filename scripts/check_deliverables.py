import csv
import hashlib
import json
import re
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]

REQUIRED = {
    "docs": [
        "README.md", "docs/项目说明.md", "docs/开发流程.md", "docs/培养目标.md",
        "docs/需求规格说明书.md", "docs/概要设计说明书.md", "docs/详细设计说明书.md",
        "docs/指标口径手册.md", "docs/数据字典.md", "docs/测试计划与报告.md",
        "docs/测试用例与缺陷清单.md", "docs/代码评审记录.md", "docs/部署运维手册.md",
        "docs/用户操作手册.md", "docs/试运行与培训记录.md", "docs/验收报告.md",
        "docs/项目总结.md", "docs/开发计划与进度记录.md", "docs/50问评测报告.md",
        "docs/答辩材料.md", "docs/答辩材料/答辩材料.pptx", "docs/成果物清单.md",
        "docs/screenshots/README.md", "docs/附加材料-12个月模拟数据说明.md",
    ],
    "code": [
        "backend/app/main.py", "backend/app/llm/semantic.py", "backend/etl/jobs/pipeline.py",
        "backend/etl/jobs/ads_refresh.py", "backend/etl/quality/checks.py",
        "backend/etl/evaluation/questions.json", "backend/etl/evaluation/run_eval.py",
        "frontend/src/api/client.js", "frontend/src/views/SystemAdminView.vue", "frontend/src/views/ResourcesView.vue",
        "frontend/src/components/DatePicker.vue",
        "frontend/src/components/charts/LineChart.vue", "frontend/src/components/charts/BarChart.vue",
        "frontend/src/components/charts/PieChart.vue", "frontend/src/components/charts/GaugeChart.vue",
        "frontend/src/components/charts/ScatterChart.vue", "frontend/e2e/smoke.mjs",
        "sql/ods/schema.sql", "sql/dwd/schema.sql", "sql/dim/schema.sql",
        "sql/dws/schema.sql", "sql/ads/schema.sql", "deploy/docker-compose.yml",
        "scripts/export_init_data.py", "scripts/check_reconciliation.py", "scripts/load_test.py",
        "scripts/security_check.py", "backend/app/llm/nl2sql.py", "backend/app/services/knowledge.py",
        "backend/tests/test_edge_cases.py",
    ],
    "data": [
        "data/mock_his/his_outpatient.csv", "data/mock_his/his_inpatient.csv",
        "data/mock_his/his_charge.csv", "data/mock_his/emr_record.csv",
        "data/mock_his/lis_report.csv", "data/files/finance_excel.csv",
        "data/init/dim_department.csv", "data/init/dim_disease.csv",
        "data/init/dim_fee_type.csv", "data/init/metric_definition.csv",
        "data/init/quality_rules.csv", "data/init/manifest.json",
        "data/supplemental_12m/mock_his/his_outpatient.csv",
        "data/supplemental_12m/mock_his/his_inpatient.csv",
        "data/supplemental_12m/mock_his/his_charge.csv",
        "data/supplemental_12m/mock_his/emr_record.csv",
        "data/supplemental_12m/mock_his/lis_report.csv",
        "data/supplemental_12m/files/finance_excel.csv",
        "data/supplemental_12m/manifest.json", "data/supplemental_12m/summary.json",
        "data/supplemental_12m/monthly_summary.csv",
        "data/derived/reconciliation_report.json", "data/derived/e2e_report.json",
        "data/derived/security_check_report.json", "data/derived/load_test_report.json",
        "data/derived/query_plan_report.json",
    ],
}


def csv_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def check_links():
    errors = []
    for path in [PROJECT / "README.md", *sorted((PROJECT / "docs").glob("*.md"))]:
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)#]+)\)", text):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                errors.append(f"{path.relative_to(PROJECT)} -> {target}")
    return errors


def check_manifest():
    manifest_path = PROJECT / "data/init/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest["files"]:
        path = manifest_path.parent / item["name"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            raise AssertionError(f"初始化快照哈希不一致: {item['name']}")


def check_supplemental_db():
    db = PROJECT / "data/supplemental_12m/derived/supplemental_12m.db"
    if not db.exists():
        raise AssertionError("12个月附加数据库不存在")
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
        bounds = conn.execute("SELECT MIN(stat_date),MAX(stat_date),COUNT(DISTINCT substr(stat_date,1,7)) FROM dws_dept_day").fetchone()
        assert bounds == ("2025-04-01", "2026-03-31", 12), bounds
        charge_total = conn.execute("SELECT ROUND(SUM(amount),2) FROM dwd_charge_detail").fetchone()[0]
        revenue_total = conn.execute("SELECT ROUND(SUM(total_revenue),2) FROM dws_dept_day").fetchone()[0]
        bill_total = conn.execute("""SELECT ROUND((SELECT SUM(fee_amount) FROM dwd_outpatient_visit)
            + (SELECT SUM(total_fee) FROM dwd_inpatient_stay),2)""").fetchone()[0]
        # 账单口径（门诊收费单+住院结算）必须与DWS总收入一致；收费明细是另一套口径，仅用于费别结构。
        assert bill_total == revenue_total, (bill_total, revenue_total)
        duplicate_charge = conn.execute("SELECT COUNT(*)-COUNT(DISTINCT charge_id) FROM dwd_charge_detail").fetchone()[0]
        assert duplicate_charge == 0
        grains = dict(conn.execute("SELECT grain,COUNT(*) FROM ads_metric_result GROUP BY grain").fetchall())
        themes = conn.execute("SELECT COUNT(*) FROM dws_outpatient_day").fetchone()[0]
        ads_metrics = conn.execute("SELECT COUNT(DISTINCT metric_code),COUNT(*) FROM ads_metric_result").fetchone()
        wide = conn.execute("SELECT COUNT(*) FROM dwd_encounter_wide").fetchone()[0]
    assert ads_metrics == (31, 146630), ads_metrics
    assert wide == 41022, wide
    return {"date_range": {"start": bounds[0], "end": bounds[1]}, "month_count": bounds[2],
            "charge_total": charge_total, "bill_total": bill_total, "revenue_total": revenue_total,
            "duplicate_charge_ids": duplicate_charge, "ads_grains": grains, "theme_rows": themes,
            "ads_metrics": ads_metrics, "dwd_wide_rows": wide}


def check_data():
    db = PROJECT / "data/derived/medical_ops.db"
    if not db.exists():
        return {"database": "missing", "note": "运行数据库未生成；不阻塞源代码归档"}
    with sqlite3.connect(db) as conn:
        metrics = conn.execute("SELECT COUNT(*),SUM(supported) FROM metric_definition").fetchone()
        grains = dict(conn.execute("SELECT grain,COUNT(*) FROM ads_metric_result GROUP BY grain").fetchall())
        themes = dict(conn.execute("SELECT 'dws_outpatient_day',COUNT(*) FROM dws_outpatient_day UNION ALL SELECT 'dws_inpatient_day',COUNT(*) FROM dws_inpatient_day UNION ALL SELECT 'dws_revenue_day',COUNT(*) FROM dws_revenue_day UNION ALL SELECT 'dws_drug_day',COUNT(*) FROM dws_drug_day UNION ALL SELECT 'dws_consumable_day',COUNT(*) FROM dws_consumable_day UNION ALL SELECT 'dws_disease_day',COUNT(*) FROM dws_disease_day UNION ALL SELECT 'dws_resource_day',COUNT(*) FROM dws_resource_day UNION ALL SELECT 'dws_service_day',COUNT(*) FROM dws_service_day").fetchall())
        dim_date = conn.execute("SELECT COUNT(*) FROM dim_date").fetchone()[0]
        ads_metrics = conn.execute("SELECT COUNT(DISTINCT metric_code),COUNT(*) FROM ads_metric_result").fetchone()
        wide = conn.execute("SELECT COUNT(*) FROM dwd_encounter_wide").fetchone()[0]
    assert metrics == (40, 31), metrics
    assert ads_metrics == (31, 36828), ads_metrics
    assert sum(themes.values()) == 7679
    assert dim_date == 91
    assert wide == 10500
    return {"metrics": metrics, "ads_grains": grains, "ads_metrics": ads_metrics, "theme_rows": themes, "theme_total": sum(themes.values()), "dim_date": dim_date, "dwd_wide_rows": wide}


def main():
    missing = []
    for group, files in REQUIRED.items():
        for item in files:
            if not (PROJECT / item).exists():
                missing.append(f"{group}:{item}")
    link_errors = check_links()
    check_manifest()
    data = check_data()
    metric_rows = csv_rows(PROJECT / "data/init/metric_definition.csv")
    quality_rows = csv_rows(PROJECT / "data/init/quality_rules.csv")
    supplemental = json.loads((PROJECT / "data/supplemental_12m/summary.json").read_text(encoding="utf-8"))
    supplemental_verification = supplemental["verification"]
    assert supplemental_verification["month_count"] == 12
    supplemental_db = check_supplemental_db()
    e2e = json.loads((PROJECT / "data/derived/e2e_report.json").read_text(encoding="utf-8"))
    security = json.loads((PROJECT / "data/derived/security_check_report.json").read_text(encoding="utf-8"))
    reconciliation = json.loads((PROJECT / "data/derived/reconciliation_report.json").read_text(encoding="utf-8"))
    load = json.loads((PROJECT / "data/derived/load_test_report.json").read_text(encoding="utf-8"))
    assert e2e["failed"] == 0
    assert security["summary"]["failed"] == 0
    assert reconciliation["summary"]["failed"] == 0
    assert load["failure"] == 0
    coverage_root = ET.parse(PROJECT / "data/derived/coverage.xml").getroot()
    coverage_rate = round(float(coverage_root.attrib["line-rate"])*100, 2)
    assert coverage_rate >= 85, coverage_rate
    report = {
        "required_files": sum(len(items) for items in REQUIRED.values()),
        "missing_files": missing,
        "broken_markdown_links": link_errors,
        "metric_rows": len(metric_rows),
        "supported_metrics": sum(1 for row in metric_rows if row["supported"] == "True"),
        "quality_rules": len(quality_rows),
        "data": data,
        "supplemental_12m": {
            "summary": {
                "date_range": supplemental_verification["date_range"],
                "month_count": supplemental_verification["month_count"],
                "ads_grains": supplemental_verification["ads_grains"],
                "theme_rows": supplemental_verification["theme_rows"],
            },
            "database_recheck": supplemental_db,
        },
        "test_evidence": {
            "e2e": f"{e2e['passed']}/{e2e['total']}",
            "security": f"{security['summary']['passed']}/{security['summary']['total']}",
            "reconciliation": f"{reconciliation['summary']['passed']}/{reconciliation['summary']['total']}",
            "load": f"{load['success']}/{load['requests']}",
            "p95_ms": load["latency_ms"]["p95"],
            "backend_coverage_pct": coverage_rate,
        },
        "screenshot_status": "用户提交项，目录和命名清单已准备",
        "demo_video": "按用户要求不制作",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if missing or link_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
