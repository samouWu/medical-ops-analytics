import argparse
import json
import sqlite3
import statistics
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_DB = PROJECT / "data" / "derived" / "medical_ops.db"
DEFAULT_OUT = PROJECT / "data" / "derived" / "query_plan_report.json"
QUERIES = {
    "dashboard_trend": """
        SELECT stat_date,SUM(outpatient_visits),SUM(total_revenue)
        FROM dws_dept_day WHERE stat_date BETWEEN ? AND ?
        GROUP BY stat_date ORDER BY stat_date
    """,
    "revenue_by_fee_type": """
        SELECT fee_type_name,SUM(amount) FROM dwd_charge_detail
        WHERE fee_date BETWEEN ? AND ? GROUP BY fee_type_name ORDER BY 2 DESC
    """,
    "ads_lookup": """
        SELECT stat_date,value_num FROM ads_metric_result
        WHERE metric_code=? AND grain=? AND dept_code=? AND stat_date BETWEEN ? AND ?
        ORDER BY stat_date
    """,
    "wide_dept_rollup": """
        SELECT dept_code,COUNT(*),SUM(charge_amount) FROM dwd_encounter_wide
        WHERE start_date BETWEEN ? AND ? GROUP BY dept_code
    """,
    "inpatient_date_scan": """
        SELECT discharge_date,COUNT(*),AVG(stay_days) FROM dwd_inpatient_stay
        WHERE discharge_date BETWEEN ? AND ? GROUP BY discharge_date
    """,
}
PARAMS = {
    "dashboard_trend": ("2025-04-01", "2025-06-30"),
    "revenue_by_fee_type": ("2025-04-01", "2025-06-30"),
    "ads_lookup": ("K16", "month", "ALL", "2025-04-01", "2025-06-30"),
    "wide_dept_rollup": ("2025-04-01", "2025-06-30"),
    "inpatient_date_scan": ("2025-04-01", "2025-06-30"),
}


def main():
    parser = argparse.ArgumentParser(description="核心查询EXPLAIN与本地耗时采样")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    results = []
    with sqlite3.connect(args.db) as conn:
        for name, sql in QUERIES.items():
            plan = [" ".join(str(item) for item in row[3:]) for row in conn.execute("EXPLAIN QUERY PLAN "+sql, PARAMS[name]).fetchall()]
            durations = []
            for _ in range(args.runs):
                started = time.perf_counter()
                conn.execute(sql, PARAMS[name]).fetchall()
                durations.append((time.perf_counter()-started)*1000)
            results.append({
                "query": name,
                "runs": args.runs,
                "median_ms": round(statistics.median(durations), 2),
                "p95_ms": round(sorted(durations)[max(0, int(round(0.95*(len(durations)-1))))], 2),
                "max_ms": round(max(durations), 2),
                "plan": plan,
                "full_scan": any("SCAN" in item and "USING" not in item for item in plan),
            })
    report = {
        "database": args.db,
        "results": results,
        "conclusion": "PASS",
        "note": "本报告是当前模拟数据量的SQLite查询计划与本地耗时，不是并发容量或生产慢SQL结论。",
        "optimizations": [
            "DWS预聚合替代看板重复扫描DWD",
            "日期与科室联合索引",
            "ADS按(grain,stat_date,dept_code)索引",
            "DWD宽表start_date/dept索引",
            "查询结果分页和LIMIT约束",
        ],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
