import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.common import ok, trace_context
from app.core.config import DATA_DIR
from app.core.database import audit, db_session
from app.core.security import current_user, require_roles, hash_password
from app.schemas import (AdsRefreshRequest, DataSourceRequest, DataSourceUpdateRequest, EtlJobRequest,
                         EtlJobUpdateRequest, UserRequest, UserUpdateRequest)
from etl.jobs.pipeline import SOURCES, detect_source, import_file, import_with_retry, read_rows, refresh_ads, run_all
from etl.quality.checks import latest_quality, run_quality

router = APIRouter(tags=["数据治理"])


@router.get("/quality/latest")
def quality_latest(user: dict = Depends(current_user)):
    return ok(latest_quality())


@router.post("/quality/run")
def quality_run(user: dict = Depends(require_roles("admin", "analyst"))):
    run_quality()
    audit(user["username"], "RUN", "quality", "执行质量规则", trace_context.get())
    return ok(latest_quality())


@router.post("/imports/auto")
async def import_auto(file: UploadFile = File(...), user: dict = Depends(require_roles("admin", "analyst"))):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".csv", ".xlsx", ".xlsm"):
        raise HTTPException(400, "仅支持CSV、XLSX或XLSM文件")
    content = await file.read(20*1024*1024+1)
    if len(content) > 20*1024*1024:
        raise HTTPException(413, "文件不能超过20MB")
    upload_dir = DATA_DIR / "derived" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    path = upload_dir / (uuid.uuid4().hex+suffix)
    path.write_bytes(content)
    try:
        columns, _ = read_rows(path)
        source = detect_source(columns)
        result = import_file(source, path)
        audit(user["username"], "IMPORT", source, f"{result['row_count']}行，{result['error_count']}错误", trace_context.get())
        return ok(result)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    finally:
        path.unlink(missing_ok=True)


@router.get("/etl/jobs")
def jobs(user: dict = Depends(current_user)):
    with db_session() as conn:
        return ok([dict(row) for row in conn.execute("SELECT * FROM etl_job ORDER BY rowid")])


@router.post("/etl/jobs")
def create_job(payload: EtlJobRequest, user: dict = Depends(require_roles("admin"))):
    job_id = uuid.uuid4().hex[:12]
    with db_session() as conn:
        conn.execute("INSERT INTO etl_job VALUES (?,?,?,?,?,?,?,?)",
                     (job_id, payload.name, payload.source_table, payload.schedule, int(payload.enabled), None, None, payload.retry_limit))
    audit(user["username"], "CREATE", "etl_job", job_id, trace_context.get())
    return ok({"id": job_id, **payload.model_dump()})


@router.put("/etl/jobs/{job_id}")
def update_job(job_id: str, payload: EtlJobUpdateRequest, user: dict = Depends(require_roles("admin"))):
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(400, "没有可更新字段")
    fields, values = [], []
    for key, value in changes.items():
        fields.append(f"{key}=?")
        values.append(int(value) if key == "enabled" else value)
    with db_session() as conn:
        if not conn.execute("SELECT 1 FROM etl_job WHERE id=?", (job_id,)).fetchone():
            raise HTTPException(404, "任务不存在")
        conn.execute(f"UPDATE etl_job SET {','.join(fields)} WHERE id=?", (*values, job_id))
    audit(user["username"], "UPDATE", "etl_job", job_id, trace_context.get())
    return ok({"id": job_id, **changes})


@router.delete("/etl/jobs/{job_id}")
def delete_job(job_id: str, user: dict = Depends(require_roles("admin"))):
    with db_session() as conn:
        row = conn.execute("SELECT name FROM etl_job WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise HTTPException(404, "任务不存在")
        conn.execute("DELETE FROM etl_job WHERE id=?", (job_id,))
    audit(user["username"], "DELETE", "etl_job", job_id, trace_context.get())
    return ok({"id": job_id, "deleted": True})


@router.post("/etl/jobs/{job_id}/run")
def run_job(job_id: str, user: dict = Depends(require_roles("admin", "analyst"))):
    with db_session() as conn:
        job = conn.execute("SELECT * FROM etl_job WHERE id=?", (job_id,)).fetchone()
    if not job:
        raise HTTPException(404, "任务不存在")
    source = job["source_table"]
    result = import_with_retry(source, DATA_DIR / SOURCES[source]["path"], retry_limit=job["retry_limit"])
    audit(user["username"], "RUN", "etl_job", job_id, trace_context.get())
    return ok({"job_id": job_id, "status": "SUCCESS", **result})


@router.post("/etl/run-all")
def run_pipeline(user: dict = Depends(require_roles("admin"))):
    result = run_all()
    audit(user["username"], "RUN", "etl_pipeline", "全量重跑", trace_context.get())
    return ok(result)


@router.post("/etl/ads/refresh")
def refresh_metric_ads(payload: AdsRefreshRequest, user: dict = Depends(require_roles("admin", "analyst"))):
    try:
        result = refresh_ads(payload.start, payload.end, tuple(payload.grains), payload.dept_code)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    audit(user["username"], "RUN", "ads_refresh", f"{payload.start or 'MIN'}至{payload.end or 'MAX'}:{','.join(payload.grains)}", trace_context.get())
    return ok(result)


@router.get("/data-sources")
def list_sources(user: dict = Depends(current_user)):
    with db_session() as conn:
        rows = []
        for row in conn.execute("SELECT * FROM data_source ORDER BY id"):
            item = dict(row)
            item["config"] = json.loads(item.pop("config_json"))
            rows.append(item)
        return ok(rows)


@router.post("/data-sources")
def create_source(payload: DataSourceRequest, user: dict = Depends(require_roles("admin"))):
    source_id = uuid.uuid4().hex[:12]
    config = {"path": payload.path} if payload.path else {}
    with db_session() as conn:
        conn.execute("INSERT INTO data_source VALUES (?,?,?,?,?,?)", (source_id, payload.name, payload.kind, json.dumps(config), int(payload.enabled), __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()))
    audit(user["username"], "CREATE", "data_source", payload.name, trace_context.get())
    return ok({"id": source_id, "name": payload.name, "kind": payload.kind})


@router.put("/data-sources/{source_id}")
def update_source(source_id: str, payload: DataSourceUpdateRequest, user: dict = Depends(require_roles("admin"))):
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(400, "没有可更新字段")
    with db_session() as conn:
        row = conn.execute("SELECT * FROM data_source WHERE id=?", (source_id,)).fetchone()
        if not row:
            raise HTTPException(404, "数据源不存在")
        config = json.loads(row["config_json"] or "{}")
        if "path" in changes:
            config["path"] = changes.pop("path")
        fields, values = ["config_json=?"], [json.dumps(config)]
        for key, value in changes.items():
            fields.append(f"{key}=?")
            values.append(int(value) if key == "enabled" else value)
        conn.execute(f"UPDATE data_source SET {','.join(fields)} WHERE id=?", (*values, source_id))
    audit(user["username"], "UPDATE", "data_source", source_id, trace_context.get())
    return ok({"id": source_id, **payload.model_dump(exclude_unset=True)})


@router.delete("/data-sources/{source_id}")
def delete_source(source_id: str, user: dict = Depends(require_roles("admin"))):
    with db_session() as conn:
        row = conn.execute("SELECT name FROM data_source WHERE id=?", (source_id,)).fetchone()
        if not row:
            raise HTTPException(404, "数据源不存在")
        conn.execute("DELETE FROM data_source WHERE id=?", (source_id,))
    audit(user["username"], "DELETE", "data_source", source_id, trace_context.get())
    return ok({"id": source_id, "deleted": True})


@router.post("/data-sources/{source_id}/test")
def test_source(source_id: str, user: dict = Depends(require_roles("admin", "analyst"))):
    with db_session() as conn:
        row = conn.execute("SELECT * FROM data_source WHERE id=?", (source_id,)).fetchone()
    if not row:
        raise HTTPException(404, "数据源不存在")
    if row["kind"] not in ("csv", "excel"):
        return ok({"connected": False, "message": "初版仅实现文件源连通测试，数据库/API需配置专用连接器"})
    config = json.loads(row["config_json"])
    path = DATA_DIR.parent / config.get("path", "")
    return ok({"connected": path.is_file(), "message": "文件可读取" if path.is_file() else "文件不存在"})


@router.get("/metadata/lineage")
def metadata_lineage(user: dict = Depends(current_user)):
    return ok({"layers": [
        {"layer": "ODS", "tables": ["ods_record"], "source": "六份源文件", "description": "保留源记录、批次与内容哈希"},
        {"layer": "DWD", "tables": list({"his_outpatient": "dwd_outpatient_visit", "his_inpatient": "dwd_inpatient_stay", "his_charge": "dwd_charge_detail", "emr_record": "dwd_emr_record", "lis_report": "dwd_lis_report", "finance_excel": "dwd_finance_day"}.values()), "source": "ODS", "description": "标准化、幂等去重、患者标识散列化"},
        {"layer": "DWS", "tables": ["dws_outpatient_day", "dws_inpatient_day", "dws_revenue_day", "dws_drug_day", "dws_consumable_day", "dws_disease_day", "dws_resource_day", "dws_service_day"], "source": "DWD+DIM", "description": "八大主题日汇总集市，另保留dws_dept_day公共汇总"},
        {"layer": "ADS", "tables": ["ads_metric_result"], "source": "DWS", "description": "核心指标日/周/月结果，支持按区间回刷"},
    ]})


@router.get("/users")
def users(user: dict = Depends(require_roles("admin"))):
    with db_session() as conn:
        rows = []
        for row in conn.execute("SELECT username,display_name,role,dept_codes_json,enabled FROM app_user ORDER BY username"):
            item = dict(row)
            item["dept_codes"] = json.loads(item.pop("dept_codes_json"))
            rows.append(item)
        return ok(rows)


@router.get("/roles")
def roles(user: dict = Depends(require_roles("admin"))):
    return ok([
        {"code": "admin", "name": "系统管理员", "description": "全院数据、用户、数据源、全量ETL与审计", "department_scoped": False},
        {"code": "analyst", "name": "运营分析师", "description": "全院查询、导入、单任务ETL、质量与ADS回刷", "department_scoped": False},
        {"code": "department", "name": "科室用户", "description": "仅授权科室查询和导出", "department_scoped": True},
        {"code": "engineer", "name": "数据工程师", "description": "预留角色，当前仅登记不授予额外接口权限", "department_scoped": False},
    ])


@router.post("/users")
def create_user(payload: UserRequest, user: dict = Depends(require_roles("admin"))):
    with db_session() as conn:
        if conn.execute("SELECT 1 FROM app_user WHERE username=?", (payload.username,)).fetchone():
            raise HTTPException(409, "用户名已存在")
        conn.execute("INSERT INTO app_user VALUES (?,?,?,?,?,1)", (payload.username, payload.display_name, hash_password(payload.password), payload.role, json.dumps(payload.dept_codes)))
    audit(user["username"], "CREATE", "user", payload.username, trace_context.get())
    return ok({"username": payload.username, "role": payload.role})


@router.put("/users/{username}")
def update_user(username: str, payload: UserUpdateRequest, user: dict = Depends(require_roles("admin"))):
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(400, "没有可更新字段")
    if username == user["username"] and (changes.get("enabled") is False or changes.get("role") not in (None, "admin")):
        raise HTTPException(400, "不能禁用或降级当前管理员自身")
    fields, values = [], []
    for key, value in changes.items():
        if key == "password":
            fields.append("password_hash=?")
            values.append(hash_password(value))
        elif key == "dept_codes":
            fields.append("dept_codes_json=?")
            values.append(json.dumps(value))
        elif key == "enabled":
            fields.append("enabled=?")
            values.append(int(value))
        else:
            fields.append(f"{key}=?")
            values.append(value)
    with db_session() as conn:
        row = conn.execute("SELECT role,enabled FROM app_user WHERE username=?", (username,)).fetchone()
        if not row:
            raise HTTPException(404, "用户不存在")
        if row["role"] == "admin" and (changes.get("enabled") is False or changes.get("role") not in (None, "admin")):
            admins = conn.execute("SELECT COUNT(*) FROM app_user WHERE role='admin' AND enabled=1 AND username!=?", (username,)).fetchone()[0]
            if admins == 0:
                raise HTTPException(400, "不能移除最后一个启用的管理员")
        conn.execute(f"UPDATE app_user SET {','.join(fields)} WHERE username=?", (*values, username))
    audit(user["username"], "UPDATE", "user", username, trace_context.get())
    return ok({"username": username, "updated": True})


@router.delete("/users/{username}")
def delete_user(username: str, user: dict = Depends(require_roles("admin"))):
    if username == user["username"]:
        raise HTTPException(400, "不能删除当前登录用户")
    with db_session() as conn:
        row = conn.execute("SELECT role FROM app_user WHERE username=?", (username,)).fetchone()
        if not row:
            raise HTTPException(404, "用户不存在")
        if row["role"] == "admin":
            admins = conn.execute("SELECT COUNT(*) FROM app_user WHERE role='admin' AND enabled=1").fetchone()[0]
            if admins <= 1:
                raise HTTPException(400, "不能删除最后一个启用的管理员")
        conn.execute("DELETE FROM app_user WHERE username=?", (username,))
    audit(user["username"], "DELETE", "user", username, trace_context.get())
    return ok({"username": username, "deleted": True})


@router.get("/audit/logs")
def audit_logs(limit: int = 100, user: dict = Depends(require_roles("admin"))):
    limit = min(max(limit, 1), 500)
    with db_session() as conn:
        return ok([dict(row) for row in conn.execute("SELECT created_at,username,action,resource,detail,trace_id FROM audit_log ORDER BY id DESC LIMIT ?", (limit,))])
