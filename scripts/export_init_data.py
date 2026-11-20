import csv
import hashlib
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "backend"))

from app.core.database import DEPARTMENTS, DISEASES, FEE_TYPES  # noqa: E402
from app.services.metrics import METRICS  # noqa: E402
from etl.quality.checks import RULES  # noqa: E402

OUTPUT = PROJECT / "data" / "init"


def write_csv(name, headers, rows):
    path = OUTPUT / name
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(rows)
    return path


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    files = []
    files.append(write_csv("dim_department.csv", ["dept_code", "dept_name", "bed_count", "staff_count", "mapping_status"],
                           [(*row, "待业务确认") for row in DEPARTMENTS]))
    files.append(write_csv("dim_disease.csv", ["disease_code", "disease_name"], DISEASES))
    files.append(write_csv("dim_fee_type.csv", ["fee_type_code", "fee_type_name", "category"], FEE_TYPES))
    files.append(write_csv("metric_definition.csv", ["metric_code", "metric_name", "topic", "unit", "supported", "description", "formula"], METRICS))
    quality_rows = [
        (code, name, "HIGH" if code.endswith("UNIQUE") or "NOT_NULL" in code else "MEDIUM", sql, "failed_rows = 0", "隔离异常行并通知数据责任人")
        for code, name, sql in RULES
    ]
    files.append(write_csv("quality_rules.csv", ["rule_code", "rule_name", "severity", "check_sql", "pass_condition", "disposition"], quality_rows))
    manifest = {
        "generated_from": "backend/app/core/database.py + backend/app/services/metrics.py + backend/etl/quality/checks.py",
        "note": "初始化快照，不作为独立主数据源；运行时以代码常量和数据库为准。",
        "files": [],
    }
    for path in files:
        data = path.read_bytes()
        manifest["files"].append({"name": path.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "files": [item["name"] for item in manifest["files"]]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
