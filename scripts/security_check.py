import argparse
import json
from pathlib import Path

import httpx

PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = PROJECT / "data" / "derived" / "security_check_report.json"


def main():
    parser = argparse.ArgumentParser(description="课程平台安全冒烟检查，不替代渗透测试")
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--admin-password", default="admin123")
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    checks = []

    def check(name, passed, actual, expected):
        checks.append({"check": name, "passed": bool(passed), "actual": actual, "expected": expected})

    with httpx.Client(base_url=args.base_url, timeout=20) as client:
        health = client.get("/health")
        check("health_public", health.status_code == 200, health.status_code, 200)

        unauth = client.get("/api/v1/dashboards/management")
        check("unauthenticated_401", unauth.status_code == 401, unauth.status_code, 401)

        invalid = client.get("/api/v1/dashboards/management", headers={"Authorization": "Bearer invalid.jwt.token"})
        check("invalid_jwt_401", invalid.status_code == 401, invalid.status_code, 401)

        login = client.post("/api/v1/auth/login", json={"username": "admin", "password": args.admin_password})
        check("admin_login", login.status_code == 200, login.status_code, 200)
        admin = {"Authorization": "Bearer "+login.json()["data"]["token"]}

        dept_login = client.post("/api/v1/auth/login", json={"username": "dept_hn", "password": "dept123"})
        check("department_login", dept_login.status_code == 200, dept_login.status_code, 200)
        dept = {"Authorization": "Bearer "+dept_login.json()["data"]["token"]}

        allowed = client.get("/api/v1/dashboards/management?dept_code=HN", headers=dept)
        check("department_allowed_200", allowed.status_code == 200, allowed.status_code, 200)
        denied = client.get("/api/v1/dashboards/management?dept_code=HX", headers=dept)
        check("department_cross_403", denied.status_code == 403, denied.status_code, 403)
        admin_api = client.get("/api/v1/users", headers=dept)
        check("department_admin_api_403", admin_api.status_code == 403, admin_api.status_code, 403)

        dangerous = client.post("/api/v1/ai/ask", headers=admin, json={"question": "DROP TABLE患者姓名"})
        check("dangerous_question_403", dangerous.status_code == 403, dangerous.status_code, 403)

        unsupported = client.get("/api/v1/metrics/K03/values", headers=admin)
        check("unsupported_metric_422", unsupported.status_code == 422, unsupported.status_code, 422)

        bad_upload = client.post("/api/v1/imports/auto", headers=admin, files={"file": ("bad.txt", b"not-a-csv", "text/plain")})
        check("invalid_upload_400", bad_upload.status_code == 400, bad_upload.status_code, 400)

        nl2sql = client.post("/api/v1/ai/nl2sql", headers=admin, json={"question": "各科室医疗收入是多少"})
        check("nl2sql_safe_gate", nl2sql.status_code in (200, 503), nl2sql.status_code, "200(有Key)或503(无Key)")
        if nl2sql.status_code == 200:
            payload = nl2sql.json()["data"]
            check("nl2sql_readonly_sql", payload["sql"].lower().startswith("select"), payload["sql"], "SELECT 聚合查询")

        trace_header = allowed.headers.get("X-Trace-ID")
        check("trace_id_header", bool(trace_header), trace_header, "非空X-Trace-ID")

    failed = [item for item in checks if not item["passed"]]
    report = {
        "base_url": args.base_url,
        "summary": {"total": len(checks), "passed": len(checks)-len(failed), "failed": len(failed)},
        "checks": checks,
        "conclusion": "PASS" if not failed else "FAIL",
        "scope": "仅课程平台HTTP安全冒烟；不包含渗透、暴力破解、依赖漏洞、TLS和限流专项。",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
