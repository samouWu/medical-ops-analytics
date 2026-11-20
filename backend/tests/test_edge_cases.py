import pytest

from app.core.security import check_department_scope, hash_password, token_subject, verify_password
from app.llm.nl2sql import NL2SQLError, validate_sql
from app.llm.semantic import resolve_period
from app.services.analytics import metric_values, normalize_period
from app.services.reports import previous_period, resolve_report_period
from app.core.database import db_session


def test_api_error_and_validation_branches(client, admin_headers):
    assert client.get("/").status_code == 200
    assert client.get("/api/v1/dashboards/unknown", headers=admin_headers).status_code == 404
    assert client.get("/api/v1/dashboards/department", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/dashboards/topic", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/metrics?topic=门诊&keyword=床位", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/metrics?topic=不存在", headers=admin_headers).json()["data"] == []
    assert client.get("/api/v1/metrics/K999/values", headers=admin_headers).status_code == 400
    assert client.get("/api/v1/metrics/K01/values?grain=year", headers=admin_headers).status_code == 400

    assert client.post("/api/v1/reports/generate", headers=admin_headers, json={"period": "year"}).status_code == 400
    invalid_metric = client.post("/api/v1/reports/query", headers=admin_headers, json={"metrics": ["K999"]})
    assert invalid_metric.status_code == 422
    invalid_grain = client.post("/api/v1/reports/query", headers=admin_headers, json={"metrics": ["K01"], "grain": "year"})
    assert invalid_grain.status_code == 422
    invalid_comparison = client.post("/api/v1/reports/query", headers=admin_headers, json={"metrics": ["K01"], "comparisons": ["qoq"]})
    assert invalid_comparison.status_code == 422

    duplicate = client.post("/api/v1/users", headers=admin_headers, json={
        "username": "admin", "display_name": "重复", "password": "password123", "role": "analyst", "dept_codes": [],
    })
    assert duplicate.status_code == 409
    missing_user = client.put("/api/v1/users/not_exists", headers=admin_headers, json={"display_name": "x"})
    assert missing_user.status_code == 404
    no_user_changes = client.put("/api/v1/users/admin", headers=admin_headers, json={})
    assert no_user_changes.status_code == 400
    assert client.delete("/api/v1/users/admin", headers=admin_headers).status_code == 400
    bad_role = client.post("/api/v1/users", headers=admin_headers, json={
        "username": "bad_role_user", "display_name": "无效", "password": "password123", "role": "owner", "dept_codes": [],
    })
    assert bad_role.status_code == 422

    assert client.post("/api/v1/data-sources/missing/test", headers=admin_headers).status_code == 404
    assert client.put("/api/v1/data-sources/missing", headers=admin_headers, json={"name": "x"}).status_code == 404
    assert client.delete("/api/v1/data-sources/missing", headers=admin_headers).status_code == 404
    assert client.post("/api/v1/etl/jobs/missing/run", headers=admin_headers).status_code == 404
    assert client.delete("/api/v1/etl/jobs/missing", headers=admin_headers).status_code == 404
    assert client.put("/api/v1/etl/jobs/missing", headers=admin_headers, json={}).status_code == 400


def test_security_helper_edge_cases():
    assert verify_password("password", "not-a-valid-hash") is False
    stored = hash_password("password123")
    assert verify_password("password123", stored) is True
    assert verify_password("wrong", stored) is False
    assert token_subject("not-a-jwt") is None
    assert check_department_scope({"dept_codes": ["HN"]}, "HN") is None
    with pytest.raises(Exception):
        check_department_scope({"dept_codes": ["HN"]}, "HX")


def test_period_and_metric_boundary_errors():
    with db_session() as conn:
        assert resolve_report_period("week", "2025-06-15", conn) == ("2025-06-09", "2025-06-15")
        with pytest.raises(ValueError):
            resolve_report_period("year", None, conn)
        with pytest.raises(ValueError):
            normalize_period(conn, "2025-06-30", "2025-06-01")
        with pytest.raises(ValueError):
            normalize_period(conn, "not-a-date", "2025-06-01")
        with pytest.raises(ValueError):
            metric_values("K01", "2025-04-01", "2025-06-30", {"dept_codes": []}, grain="year")
    assert previous_period("month", "2025-05-01", "2025-05-31") == ("2025-04-01", "2025-04-30")
    assert previous_period("week", "2025-06-09", "2025-06-15") == ("2025-06-02", "2025-06-08")


def test_semantic_relative_period_and_errors():
    available = {"min": "2025-04-01", "max": "2025-06-30"}
    assert resolve_period("本月门诊量", available) == ("2025-06-01", "2025-06-30")
    assert resolve_period("上月门诊量", available) == ("2025-05-01", "2025-05-31")
    assert resolve_period("最近7天门诊量", available) == ("2025-06-24", "2025-06-30")
    assert resolve_period("本周门诊量", available)[0] == "2025-06-30"
    with pytest.raises(ValueError):
        resolve_period("2025年13月门诊量", available)


def test_nl2sql_validation_edge_cases():
    assert validate_sql("SELECT COUNT(*) FROM dwd_charge_detail").endswith("LIMIT 200")
    with pytest.raises(NL2SQLError):
        validate_sql("")
    with pytest.raises(NL2SQLError):
        validate_sql("-- comment\nSELECT COUNT(*) FROM dwd_charge_detail")
    with pytest.raises(NL2SQLError):
        validate_sql("SELECT COUNT(*) FROM no_such_table")
