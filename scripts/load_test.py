import argparse
import json
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = PROJECT / "data" / "derived" / "load_test_report.json"
ENDPOINTS = [
    "/api/v1/dashboards/management",
    "/api/v1/analytics/outpatient",
    "/api/v1/metrics/K01/values?grain=day",
    "/api/v1/reports/query",
]


def percentile(values, p):
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered)-1, max(0, int(round((p/100)*(len(ordered)-1)))))
    return round(ordered[index], 2)


def main():
    parser = argparse.ArgumentParser(description="本机API并发冒烟压测，不是生产容量测试")
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admin123")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--requests", type=int, default=120)
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    lock = threading.Lock()
    with httpx.Client(base_url=args.base_url, timeout=20) as client:
        login = client.post("/api/v1/auth/login", json={"username": args.username, "password": args.password})
        login.raise_for_status()
        token = login.json()["data"]["token"]
    headers = {"Authorization": "Bearer "+token, "Accept": "application/json"}

    samples = []
    failures = []

    def call(index):
        endpoint = ENDPOINTS[index % len(ENDPOINTS)]
        body = {"metrics": ["K01", "K16"], "dimensions": ["date", "dept_code"], "filters": {}, "grain": "month", "comparisons": ["mom"]} if endpoint.endswith("reports/query") else None
        started = time.perf_counter()
        try:
            with httpx.Client(base_url=args.base_url, timeout=20) as client:
                response = client.post(endpoint, headers=headers, json=body) if body else client.get(endpoint, headers=headers)
            elapsed = (time.perf_counter()-started)*1000
            ok = response.status_code == 200 and response.json().get("code") == 0
            return {"endpoint": endpoint, "status": response.status_code, "ms": elapsed, "ok": ok}
        except Exception as exc:
            return {"endpoint": endpoint, "status": None, "ms": (time.perf_counter()-started)*1000, "ok": False, "error": str(exc)}

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(call, index) for index in range(args.requests)]
        for future in as_completed(futures):
            item = future.result()
            with lock:
                if item["ok"]:
                    samples.append(item["ms"])
                else:
                    failures.append(item)
    duration = time.perf_counter()-started
    report = {
        "base_url": args.base_url,
        "workers": args.workers,
        "requests": args.requests,
        "duration_seconds": round(duration, 2),
        "throughput_rps": round(args.requests/duration, 2) if duration else None,
        "success": len(samples),
        "failure": len(failures),
        "error_rate_pct": round(len(failures)/args.requests*100, 2),
        "latency_ms": {
            "min": round(min(samples), 2) if samples else None,
            "mean": round(statistics.mean(samples), 2) if samples else None,
            "p50": percentile(samples, 50),
            "p95": percentile(samples, 95),
            "p99": percentile(samples, 99),
            "max": round(max(samples), 2) if samples else None,
        },
        "failures": failures[:20],
        "scope": f"{args.workers}并发、{args.requests}请求、单机SQLite与模拟数据；不是生产容量结论。",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
