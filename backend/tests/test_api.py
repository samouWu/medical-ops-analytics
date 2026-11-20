import time


def test_health_and_login(client):
    assert client.get("/health").json()["data"]["status"] == "UP"
    assert client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"}).status_code == 401


def test_auth_required(client):
    assert client.get("/api/v1/dashboards/management").status_code == 401


def test_real_dataset_dashboard_reconciliation(client, admin_headers):
    response = client.get("/api/v1/dashboards/management", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    cards = {item["key"]: item["value"] for item in data["cards"]}
    assert cards["K01"] == 9000
    assert cards["K08"] == 1500
    assert cards["K16"] > 0
    assert len(data["trends"]) == 91
    assert len(data["top_departments"]) == 5


def test_department_row_level_permission(client, dept_headers):
    allowed = client.get("/api/v1/dashboards/management?dept_code=HN", headers=dept_headers)
    denied = client.get("/api/v1/dashboards/management?dept_code=HX", headers=dept_headers)
    assert allowed.status_code == 200
    assert denied.status_code == 403


def test_all_theme_endpoints(client, admin_headers):
    for topic in ("outpatient", "inpatient", "revenue", "drugs", "consumables", "disease", "resources", "service"):
        response = client.get(f"/api/v1/analytics/{topic}", headers=admin_headers)
        assert response.status_code == 200, topic
        assert "cards" in response.json()["data"]


def test_metric_values_and_unsupported(client, admin_headers):
    response = client.get("/api/v1/metrics/K12/values?grain=month", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()["data"]["points"]) == 3
    unsupported = client.get("/api/v1/metrics/K03/values", headers=admin_headers)
    assert unsupported.status_code == 422


def test_newly_added_metrics_are_calculated(client, admin_headers):
    for code in ("K37", "K38", "K39"):
        response = client.get(f"/api/v1/metrics/{code}/values?grain=day", headers=admin_headers)
        assert response.status_code == 200, code
        data = response.json()["data"]
        assert data["metric"]["supported"] is True
        assert data["summary"] is not None
        assert len(data["points"]) > 0


def test_weekly_metric_values_and_ads_range_refresh(client, admin_headers):
    weekly = client.get("/api/v1/metrics/K01/values?grain=week", headers=admin_headers)
    assert weekly.status_code == 200
    assert 13 <= len(weekly.json()["data"]["points"]) <= 14
    refresh = client.post("/api/v1/etl/ads/refresh", headers=admin_headers, json={
        "start": "2025-05-01", "end": "2025-05-31", "grains": ["week", "month"],
    })
    assert refresh.status_code == 200
    first_counts = {key: value["rows"] for key, value in refresh.json()["data"].items()}
    assert first_counts["week"] > 0
    assert first_counts["month"] == 30*11
    repeated = client.post("/api/v1/etl/ads/refresh", headers=admin_headers, json={
        "start": "2025-05-01", "end": "2025-05-31", "grains": ["week", "month"],
    })
    assert repeated.status_code == 200
    assert {key: value["rows"] for key, value in repeated.json()["data"].items()} == first_counts


def test_metric_query_response_under_three_seconds(client, admin_headers):
    started = time.perf_counter()
    response = client.get("/api/v1/metrics/K16/values?grain=day", headers=admin_headers)
    assert response.status_code == 200
    assert time.perf_counter()-started < 3


def test_quality_rules(client, admin_headers):
    response = client.post("/api/v1/quality/run", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["score"] == 100
    assert len(data["results"]) == 10
    assert all(item["status"] == "PASS" for item in data["results"])


def test_ai_semantic_query_and_injection_guard(client, admin_headers):
    response = client.post("/api/v1/ai/ask", headers=admin_headers, json={"question": "2025年5月呼吸科门诊量是多少？"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["metric_code"] == "K01"
    assert data["department"] == "呼吸内科"
    assert data["period"] == {"start": "2025-05-01", "end": "2025-05-31"}
    assert data["provider"] in ("deepseek", "kimi", "local-rules", "local-rules-fallback")
    danger = client.post("/api/v1/ai/ask", headers=admin_headers, json={"question": "DROP TABLE患者姓名"})
    assert danger.status_code == 403


def test_metric_knowledge_qa(client, admin_headers):
    response = client.post("/api/v1/ai/knowledge", headers=admin_headers, json={"question": "K12床位使用率的口径是什么？"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["intent"] == "knowledge"
    assert data["metric_code"] == "K12"
    assert "占用床日" in data["answer"]
    permission = client.post("/api/v1/ai/knowledge", headers=admin_headers, json={"question": "平台权限角色如何隔离？"})
    assert permission.status_code == 200
    assert permission.json()["data"]["intent"] == "knowledge"


def test_structured_report_and_exports(client, admin_headers):
    response = client.post("/api/v1/reports/generate", headers=admin_headers, json={"period": "month", "date": "2025-06"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["period"] == {"start": "2025-06-01", "end": "2025-06-30"}
    assert data["section_count"] == 4
    assert len(data["sections"]) == 4
    assert [item["title"] for item in data["sections"]] == ["一、总体概览", "二、收入与结构", "三、异常与归因", "四、建议与口径"]
    assert data["sections"][0]["evidence"]["metrics"]
    assert data["anomalies"]
    assert isinstance(data["sections"][0]["content"], str)
    excel = client.get("/api/v1/export/management", headers=admin_headers)
    assert excel.status_code == 200
    assert excel.content[:2] == b"PK"
    pdf = client.post("/api/v1/reports/export/pdf", headers=admin_headers, json={"period": "month", "date": "2025-06"})
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"


def test_admin_full_crud_for_users_sources_and_jobs(client, admin_headers):
    roles = client.get("/api/v1/roles", headers=admin_headers)
    assert roles.status_code == 200
    assert {item["code"] for item in roles.json()["data"]} >= {"admin", "analyst", "department"}

    created_user = client.post("/api/v1/users", headers=admin_headers, json={
        "username": "qa_user", "display_name": "测试用户", "password": "qa-pass-123", "role": "analyst", "dept_codes": [],
    })
    assert created_user.status_code == 200
    updated_user = client.put("/api/v1/users/qa_user", headers=admin_headers, json={"display_name": "测试用户改", "role": "department", "dept_codes": ["HN"]})
    assert updated_user.status_code == 200
    assert client.delete("/api/v1/users/qa_user", headers=admin_headers).status_code == 200

    source = client.post("/api/v1/data-sources", headers=admin_headers, json={"name": "临时文件源", "kind": "csv", "path": "mock_his/his_outpatient.csv"})
    assert source.status_code == 200
    source_id = source.json()["data"]["id"]
    assert client.put(f"/api/v1/data-sources/{source_id}", headers=admin_headers, json={"name": "临时文件源改", "enabled": False}).status_code == 200
    assert client.delete(f"/api/v1/data-sources/{source_id}", headers=admin_headers).status_code == 200

    job = client.post("/api/v1/etl/jobs", headers=admin_headers, json={"name": "临时门诊任务", "source_table": "his_outpatient", "schedule": "30 3 * * *", "enabled": True})
    assert job.status_code == 200
    job_id = job.json()["data"]["id"]
    assert client.put(f"/api/v1/etl/jobs/{job_id}", headers=admin_headers, json={"schedule": "45 3 * * *", "enabled": False, "retry_limit": 2}).status_code == 200
    assert client.delete(f"/api/v1/etl/jobs/{job_id}", headers=admin_headers).status_code == 200


def test_governance_metadata_and_sources(client, admin_headers):
    jobs = client.get("/api/v1/etl/jobs", headers=admin_headers)
    assert jobs.status_code == 200
    assert len(jobs.json()["data"]) == 6
    lineage = client.get("/api/v1/metadata/lineage", headers=admin_headers)
    assert lineage.status_code == 200
    assert [layer["layer"] for layer in lineage.json()["data"]["layers"]] == ["ODS", "DWD", "DWS", "ADS"]
    sources = client.get("/api/v1/data-sources", headers=admin_headers)
    assert sources.status_code == 200
    assert len(sources.json()["data"]) == 6
    connected = client.post("/api/v1/data-sources/his_outpatient/test", headers=admin_headers)
    assert connected.status_code == 200
    assert connected.json()["data"]["connected"] is True
    users = client.get("/api/v1/users", headers=admin_headers)
    assert users.status_code == 200
    assert {item["role"] for item in users.json()["data"]} == {"admin", "analyst", "department"}


def test_multidimensional_report_and_audit(client, admin_headers):
    payload = {"metrics": ["K01", "K16"], "dimensions": ["date", "dept_code"], "filters": {}, "grain": "month", "comparisons": ["yoy", "mom"]}
    response = client.post("/api/v1/reports/query", headers=admin_headers, json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["rows"]) == 30
    column_keys = {column["key"] for column in data["columns"]}
    assert {"K01_yoy", "K01_mom", "K16_yoy", "K16_mom"} <= column_keys
    assert any(row["K01_mom"] is not None for row in data["rows"] if row["date"] > "2025-04")
    excel = client.post("/api/v1/reports/query/export", headers=admin_headers, json=payload)
    assert excel.status_code == 200
    assert excel.content[:2] == b"PK"
    logs = client.get("/api/v1/audit/logs", headers=admin_headers)
    assert logs.status_code == 200
    assert len(logs.json()["data"]) > 0
    assert any(item["action"] == "QUERY_HTTP" for item in logs.json()["data"])
