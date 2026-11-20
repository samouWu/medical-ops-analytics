import argparse
import json
import time
from pathlib import Path

from app.core.config import BASE_DIR
from app.core.database import db_session
from app.llm.semantic import parse_question
from app.services.analytics import metric_summary

QUESTIONS = Path(__file__).with_name("questions.json")
DEFAULT_OUTPUT = BASE_DIR / "data" / "derived" / "nl2sql_eval_report.json"


def run_evaluation(output=DEFAULT_OUTPUT):
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    results = []
    started = time.perf_counter()
    user = {"username": "evaluator", "role": "admin", "dept_codes": []}
    with db_session() as conn:
        for item in questions:
            record = {"id": item["id"], "question": item["question"], "expected": item}
            try:
                code, dept, start, end = parse_question(item["question"], user, conn)
                value = metric_summary(code, start, end, user, dept, conn)
                checks = {
                    "metric": code == item["metric_code"],
                    "department": dept == item.get("dept_code"),
                    "period": start == item["start"],
                    "value": value is not None,
                }
                record.update({
                    "actual": {"metric_code": code, "dept_code": dept, "start": start, "end": end, "value": value},
                    "checks": checks,
                    "passed": all(checks.values()),
                })
            except (ValueError, PermissionError) as exc:
                record.update({"actual": None, "checks": {}, "passed": False, "error": str(exc)})
            results.append(record)
    passed = sum(1 for item in results if item["passed"])
    summary = {
        "dataset": str(QUESTIONS),
        "question_count": len(questions),
        "passed": passed,
        "failed": len(questions)-passed,
        "accuracy": round(passed/len(questions)*100, 2) if questions else 0,
        "threshold": 85,
        "passed_threshold": passed/len(questions)*100 >= 85 if questions else False,
        "definition": "指标、科室、起始统计期均正确且结果非空才计为通过；不调用外部大模型。",
        "duration_ms": round((time.perf_counter()-started)*1000, 2),
        "results": results,
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description="运行50问受控问数评测")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    result = run_evaluation(args.output)
    print(json.dumps({key: result[key] for key in ("question_count", "passed", "failed", "accuracy", "threshold", "passed_threshold", "duration_ms")}, ensure_ascii=False, indent=2))
    failures = [item for item in result["results"] if not item["passed"]]
    if failures:
        print("FAILURES:")
        for item in failures:
            print(json.dumps(item, ensure_ascii=False))


if __name__ == "__main__":
    main()
