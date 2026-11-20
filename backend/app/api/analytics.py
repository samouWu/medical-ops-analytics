import io
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openpyxl import Workbook

from app.api.common import ok, trace_context
from app.core.database import audit, db_session
from app.core.security import current_user
from app.schemas import ReportQuery
from app.services.analytics import analytics, management, metric_summary, metric_values, normalize_period
from app.services.metrics import METRIC_MAP, METRICS

router = APIRouter(tags=["运营分析"])


@router.get("/meta")
def meta(user: dict = Depends(current_user)):
    with db_session() as conn:
        if user.get("dept_codes"):
            marks = ",".join("?" for _ in user["dept_codes"])
            departments = [dict(row) for row in conn.execute(f"SELECT dept_code,dept_name,mapping_status FROM dim_department WHERE dept_code IN ({marks})", user["dept_codes"])]
        else:
            departments = [dict(row) for row in conn.execute("SELECT dept_code,dept_name,mapping_status FROM dim_department ORDER BY rowid")]
        row = conn.execute("SELECT MIN(stat_date),MAX(stat_date) FROM dws_dept_day").fetchone()
        sources = conn.execute("SELECT COUNT(*) FROM data_source WHERE enabled=1").fetchone()[0]
    return ok({"departments": departments, "date_range": {"min": row[0], "max": row[1]}, "source_count": sources, "dataset": "课程提供模拟数据集"})


@router.get("/dashboards/management")
def dashboard(start: str | None = None, end: str | None = None, dept_code: str | None = None, user: dict = Depends(current_user)):
    return ok(management(start, end, user, dept_code))


@router.get("/dashboards/{kind}")
def dashboard_alias(kind: str, start: str | None = None, end: str | None = None, dept_code: str | None = None, user: dict = Depends(current_user)):
    if kind == "management":
        return ok(management(start, end, user, dept_code))
    if kind in ("department", "topic"):
        topic = "resources" if kind == "department" else "revenue"
        return ok(analytics(topic, start, end, user, dept_code))
    raise HTTPException(404, "看板不存在")


@router.get("/analytics/{topic}")
def topic(topic: str, start: str | None = None, end: str | None = None, dept_code: str | None = None, user: dict = Depends(current_user)):
    try:
        return ok(analytics(topic, start, end, user, dept_code))
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from None
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None


@router.get("/metrics")
def metrics(topic: str | None = None, keyword: str | None = None, include_unsupported: bool = False, user: dict = Depends(current_user)):
    result = []
    for item in METRICS:
        entry = dict(zip(("code", "name", "topic", "unit", "supported", "description"), item))
        if not include_unsupported and not entry["supported"]:
            continue
        if topic and entry["topic"] != topic:
            continue
        if keyword and keyword.lower() not in (entry["name"]+entry["description"]).lower():
            continue
        result.append(entry)
    return ok(result)


@router.get("/metrics/{code}/values")
def values(code: str, start: str | None = None, end: str | None = None, dept_code: str | None = None, grain: str = "day", user: dict = Depends(current_user)):
    code = code.upper()
    try:
        with db_session() as conn:
            start, end = normalize_period(conn, start, end)
            summary = metric_summary(code, start, end, user, dept_code, conn)
        points = metric_values(code, start, end, user, dept_code, grain)
        return ok({"metric": METRIC_MAP.get(code), "summary": summary, "points": points, "period": {"start": start, "end": end}})
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from None
    except ValueError as exc:
        raise HTTPException(422 if code in METRIC_MAP and not METRIC_MAP[code]["supported"] else 400, str(exc)) from None


def _comparison_label(label, comparison, grain):
    if not isinstance(label, str) or len(label) not in (7, 10) or "至" in label:
        return None
    try:
        if len(label) == 7:
            day = date.fromisoformat(label+"-01")
            if comparison == "yoy":
                return day.replace(year=day.year-1).strftime("%Y-%m")
            return (day-timedelta(days=1)).strftime("%Y-%m") if day.month > 1 else f"{day.year-1}-12"
        day = date.fromisoformat(label)
        if comparison == "yoy":
            return (day-timedelta(days=364 if grain == "week" else 365)).isoformat()
        return (day-timedelta(days=7 if grain == "week" else 1)).isoformat()
    except ValueError:
        return None


def _build_multi_report(payload, user):
    if any(code not in METRIC_MAP or not METRIC_MAP[code]["supported"] for code in payload.metrics):
        raise HTTPException(422, "包含不存在或暂不可计算的指标")
    if payload.grain not in ("day", "week", "month"):
        raise HTTPException(422, "粒度仅支持day、week或month")
    invalid_comparisons = set(payload.comparisons)-{"yoy", "mom"}
    if invalid_comparisons:
        raise HTTPException(422, "对比方式仅支持yoy或mom")
    with db_session() as conn:
        start = payload.filters.get("start")
        end = payload.filters.get("end")
        start, end = normalize_period(conn, start, end)
    dept = payload.filters.get("dept_code")
    dept_name = None
    if dept:
        with db_session() as conn:
            row = conn.execute("SELECT dept_name FROM dim_department WHERE dept_code=?", (dept,)).fetchone()
            dept_name = row[0] if row else None
    periods = {}
    for code in payload.metrics:
        for point in metric_values(code, start, end, user, dept, payload.grain):
            base = {"date": point["date"]}
            if dept:
                base.update(dept_code=dept, dept_name=dept_name)
            periods.setdefault(point["date"], base)[code] = point["value"]
    if "dept_code" in payload.dimensions and "date" in payload.dimensions and not dept:
        with db_session() as conn:
            departments = conn.execute("SELECT dept_code,dept_name FROM dim_department").fetchall()
        rows = []
        for department in departments:
            if user.get("dept_codes") and department[0] not in user["dept_codes"]:
                continue
            department_points = {}
            for code in payload.metrics:
                for point in metric_values(code, start, end, user, department[0], payload.grain):
                    department_points.setdefault(point["date"], {"date": point["date"], "dept_code": department[0], "dept_name": department[1]})[code] = point["value"]
            rows.extend(department_points.values())
    elif "dept_code" in payload.dimensions and not dept:
        with db_session() as conn:
            departments = conn.execute("SELECT dept_code,dept_name FROM dim_department").fetchall()
        rows = []
        for department in departments:
            if user.get("dept_codes") and department[0] not in user["dept_codes"]:
                continue
            row = {"date": f"{start}至{end}", "dept_code": department[0], "dept_name": department[1]}
            with db_session() as conn:
                for code in payload.metrics:
                    row[code] = metric_summary(code, start, end, user, department[0], conn)
            rows.append(row)
    else:
        rows = list(periods.values())
    for comparison in payload.comparisons:
        label = "同比" if comparison == "yoy" else "环比"
        by_key = {(row.get("date"), row.get("dept_code")): row for row in rows}
        for row in rows:
            previous_label = _comparison_label(row.get("date"), comparison, payload.grain)
            previous = by_key.get((previous_label, row.get("dept_code")))
            for code in payload.metrics:
                current_value = row.get(code)
                previous_value = previous.get(code) if previous else None
                if current_value is None or previous_value in (None, 0):
                    row[f"{code}_{comparison}"] = None
                else:
                    row[f"{code}_{comparison}"] = round((current_value-previous_value)/abs(previous_value)*100, 4)
    columns = [{"key": "date", "label": "统计期"}]
    if "dept_code" in payload.dimensions:
        columns.append({"key": "dept_name", "label": "科室"})
    columns += [{"key": code, "label": f"{METRIC_MAP[code]['name']}（{METRIC_MAP[code]['unit']}）", "format": "money" if METRIC_MAP[code]["unit"].startswith("元") else "percent" if METRIC_MAP[code]["unit"] == "%" else "number"} for code in payload.metrics]
    for comparison in payload.comparisons:
        suffix = "同比" if comparison == "yoy" else "环比"
        columns += [{"key": f"{code}_{comparison}", "label": f"{METRIC_MAP[code]['name']}{suffix}", "format": "percent"} for code in payload.metrics]
    return {"columns": columns, "rows": rows, "period": {"start": start, "end": end}, "grain": payload.grain}


@router.post("/reports/query")
def multi_report(payload: ReportQuery, user: dict = Depends(current_user)):
    result = _build_multi_report(payload, user)
    audit(user["username"], "QUERY", "multi_report", ",".join(payload.metrics), trace_context.get())
    return ok(result)


@router.post("/reports/query/export")
def export_multi_report(payload: ReportQuery, user: dict = Depends(current_user)):
    result = _build_multi_report(payload, user)
    book = Workbook()
    sheet = book.active
    sheet.title = "多维报表"
    money_keys = {column["key"] for column in result["columns"] if column.get("format") == "money"}
    sheet.append([column["label"].replace("元", "万元") if column["key"] in money_keys else column["label"] for column in result["columns"]])
    for row in result["rows"]:
        values = []
        for column in result["columns"]:
            value = row.get(column["key"])
            if column["key"] in money_keys and isinstance(value, (int, float)):
                value = round(value/10000, 2)
            values.append(value)
        sheet.append(values)
    sheet.freeze_panes = "A2"
    output = io.BytesIO()
    book.save(output)
    output.seek(0)
    audit(user["username"], "EXPORT", "multi_report", ",".join(payload.metrics), trace_context.get())
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="medical-multidimensional.xlsx"'})


@router.get("/export/{topic}")
def export_topic(topic: str, start: str | None = None, end: str | None = None, dept_code: str | None = None, user: dict = Depends(current_user)):
    data = management(start, end, user, dept_code) if topic == "management" else analytics(topic, start, end, user, dept_code)
    book = Workbook()
    sheet = book.active
    sheet.title = "运营指标"
    sheet.append(["指标", "数值", "单位"])
    for item in data["cards"]:
        value, unit = item["value"], item["unit"]
        if unit.startswith("元") and isinstance(value, (int, float)) and abs(value) >= 100000:
            value, unit = round(value/10000, 2), unit.replace("元", "万元")
        sheet.append([item["label"], value, unit])
    detail = book.create_sheet("维度明细")
    columns = data.get("table", {}).get("columns") or [{"key": "dept_name", "label": "科室"}, {"key": "revenue", "label": "收入"}]
    money_columns = {col["key"] for col in columns if "元" in str(col.get("label", ""))}
    detail.append([col["label"].replace("元", "万元") if col["key"] in money_columns else col["label"] for col in columns])
    rows = data.get("table", {}).get("rows") or data.get("top_departments", [])
    for row in rows:
        values = []
        for col in columns:
            value = row.get(col["key"])
            if col["key"] in money_columns and isinstance(value, (int, float)):
                value = round(value/10000, 2)
            values.append(value)
        detail.append(values)
    output = io.BytesIO()
    book.save(output)
    output.seek(0)
    audit(user["username"], "EXPORT", topic, f"{start}至{end}", trace_context.get())
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="medical-{topic}.xlsx"'})
