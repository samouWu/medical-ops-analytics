from datetime import date, datetime, timedelta, timezone

from app.core.database import db_session
from app.services.analytics import metric_summary, normalize_period, scope
from app.llm.semantic import format_value, llm_interpretation


def resolve_report_period(period, value, conn):
    available = conn.execute("SELECT MAX(stat_date) FROM dws_dept_day").fetchone()[0]
    if not available:
        raise ValueError("暂无数据，请先执行ETL")
    anchor = available
    if value:
        anchor = value if len(value) == 10 else value+"-01"
    day = date.fromisoformat(anchor)
    if period == "week":
        start = day-timedelta(days=day.weekday())
        end = start+timedelta(days=6)
    elif period == "month":
        start = day.replace(day=1)
        end = (start.replace(day=28)+timedelta(days=5)).replace(day=1)-timedelta(days=1)
    else:
        raise ValueError("报告周期仅支持week或month")
    return start.isoformat(), end.isoformat()


def previous_period(period, start, end):
    first = date.fromisoformat(start)
    last = date.fromisoformat(end)
    previous_end = (first-timedelta(days=1)).isoformat()
    if period == "month":
        previous_start = (first-timedelta(days=1)).replace(day=1).isoformat()
    else:
        previous_start = (last-timedelta(days=7)).isoformat()
    return previous_start, previous_end


def _department_totals(conn, start, end, user, dept_code):
    where, params = scope(user, dept_code, "s.dept_code")
    rows = conn.execute(
        "SELECT d.dept_name,SUM(s.total_revenue),SUM(s.outpatient_visits),SUM(s.discharges) "
        "FROM dws_dept_day s JOIN dim_department d USING(dept_code) "
        f"WHERE s.stat_date BETWEEN ? AND ? AND {where} GROUP BY 1",
        [start, end, *params],
    ).fetchall()
    return {row[0]: {"revenue": row[1] or 0, "visits": row[2] or 0, "discharges": row[3] or 0} for row in rows}


def generate_report(period, value, user, dept_code=None):
    with db_session() as conn:
        start, end = resolve_report_period(period, value, conn)
        previous_start, previous_end = previous_period(period, start, end)
        codes = ("K01", "K08", "K16", "K12", "K13", "K22", "K24")
        values = {code: metric_summary(code, start, end, user, dept_code, conn) for code in codes}
        previous = {code: metric_summary(code, previous_start, previous_end, user, dept_code, conn) for code in codes}
        departments = _department_totals(conn, start, end, user, dept_code)
        previous_departments = _department_totals(conn, previous_start, previous_end, user, dept_code)
        where, params = scope(user, dept_code, "s.dept_code")
        bed_rows = conn.execute(
            "SELECT d.dept_name,SUM(s.occupied_bed_days)*100.0/NULLIF(SUM(s.open_bed_days),0) usage "
            "FROM dws_dept_day s JOIN dim_department d USING(dept_code) "
            f"WHERE s.stat_date BETWEEN ? AND ? AND {where} GROUP BY 1 ORDER BY usage DESC LIMIT 3",
            [start, end, *params],
        ).fetchall()

    def change(code):
        current_value = values[code]
        previous_value = previous[code]
        if current_value is None or previous_value in (None, 0):
            return None
        return round((current_value-previous_value)/abs(previous_value)*100, 2)

    def change_text(code):
        value = change(code)
        return "无可比数据" if value is None else f"{value:+.2f}%"

    revenue_top = sorted(departments.items(), key=lambda item: item[1]["revenue"], reverse=True)[:3]
    revenue_drivers = []
    for name, metrics in departments.items():
        before = previous_departments.get(name, {"revenue": 0, "visits": 0})
        revenue_delta = metrics["revenue"] - before["revenue"]
        visit_delta = metrics["visits"] - before["visits"]
        revenue_drivers.append((name, revenue_delta, visit_delta, metrics["revenue"]))
    revenue_drivers.sort(key=lambda item: abs(item[1]), reverse=True)
    top_driver_text = "；".join(
        f"{name}{'增加' if delta >= 0 else '减少'}{abs(delta)/10000:.2f}万元"
        for name, delta, _visits, _revenue in revenue_drivers[:3]
    ) or "暂无可比科室数据"

    anomalies = []
    revenue_change = change("K16")
    visit_change = change("K01")
    if revenue_change is not None and abs(revenue_change) >= 5:
        anomalies.append({
            "code": "K16",
            "level": "WARN" if revenue_change < 0 else "INFO",
            "title": "医疗总收入变化超过5%",
            "change_pct": revenue_change,
            "drivers": [name for name, _delta, _visits, _revenue in revenue_drivers[:3]],
            "evidence": {"current": values["K16"], "previous": previous["K16"], "period": [start, end], "previous_period": [previous_start, previous_end]},
        })
    if visit_change is not None and abs(visit_change) >= 10:
        visit_drivers = sorted(revenue_drivers, key=lambda item: abs(item[2]), reverse=True)
        anomalies.append({
            "code": "K01",
            "level": "WARN" if visit_change < 0 else "INFO",
            "title": "门诊人次变化超过10%",
            "change_pct": visit_change,
            "drivers": [name for name, _delta, _visits, _revenue in visit_drivers[:3]],
            "evidence": {"current": values["K01"], "previous": previous["K01"], "period": [start, end], "previous_period": [previous_start, previous_end]},
        })
    if values["K22"] is not None and values["K22"] > 35:
        anomalies.append({
            "code": "K22",
            "level": "WARN",
            "title": "药占比超过35%教学警戒线",
            "change_pct": change("K22"),
            "drivers": [],
            "evidence": {"current": values["K22"], "threshold": 35, "period": [start, end]},
        })
    if not anomalies:
        anomalies.append({
            "code": "NONE",
            "level": "INFO",
            "title": "未触发教学异常阈值",
            "change_pct": None,
            "drivers": [name for name, _delta, _visits, _revenue in revenue_drivers[:3]],
            "evidence": {"thresholds": {"revenue_change_pct": 5, "visit_change_pct": 10, "drug_ratio_pct": 35}},
        })

    title = ("医疗运营周报" if period == "week" else "医疗运营月报")+f"（{start[:7] if period == 'month' else start}）"
    sections = [
        {
            "title": "一、总体概览",
            "content": f"统计期门诊{values['K01'] or 0:,.0f}人次，较上期{change_text('K01')}；出院{values['K08'] or 0:,.0f}人次，较上期{change_text('K08')}；医疗总收入{format_value('K16', values['K16'])}，较上期{change_text('K16')}。床位使用率{format_value('K12', values['K12'])}，平均住院日{format_value('K13', values['K13'])}。",
            "evidence": {"metrics": ["K01", "K08", "K16", "K12", "K13"], "current": [start, end], "previous": [previous_start, previous_end], "source": "dws_dept_day"},
        },
        {
            "title": "二、收入与结构",
            "content": f"药占比{format_value('K22', values['K22'])}，耗占比{format_value('K24', values['K24'])}。收入前三科室："+"；".join(f"{name} {metrics['revenue']/10000:.2f}万元" for name, metrics in revenue_top)+"。",
            "evidence": {"metrics": ["K16", "K22", "K24"], "departments": [name for name, _metrics in revenue_top], "period": [start, end], "source": "dws_dept_day"},
        },
        {
            "title": "三、异常与归因",
            "content": "；".join(
                f"{item['title']}（变化{item['change_pct']}%）" if item["change_pct"] is not None else item["title"]
                for item in anomalies
            )+f"。科室贡献："+top_driver_text+"。",
            "evidence": anomalies,
        },
        {
            "title": "四、建议与口径",
            "content": (
                "建议优先复核收入变化贡献最大的科室，并同时核对门诊人次、出院人次和次均费用，避免把单一金额变化直接归因。"
                "床位使用率前三科室："+"；".join(f"{row[0]} {row[1]:.2f}%" for row in bed_rows if row[1] is not None)+"。"
                "收入采用HIS收费明细净额；门诊人数与人次分离；比率先汇总分子分母再相除。DRG估算指标不纳入本报告正式评价，床位和人力为教学配置。"
            ),
            "evidence": {"metrics": ["K16", "K01", "K08", "K12", "K22", "K24"], "thresholds": {"revenue_change_pct": 5, "visit_change_pct": 10, "drug_ratio_pct": 35}, "boundary": "教学口径，不用于真实绩效"},
        },
    ]

    generated, provider = llm_interpretation("生成运营报告解读", "\n".join(f"{item['title']}：{item['content']}" for item in sections))
    if generated:
        sections[0]["content"] += " 智能解读（仅解释以上已计算事实）："+generated
    return {
        "title": title,
        "period": {"start": start, "end": end},
        "previous_period": {"start": previous_start, "end": previous_end},
        "section_count": len(sections),
        "sections": sections,
        "anomalies": anomalies,
        "trace": {"metric_codes": list(codes), "source_tables": ["dwd_outpatient_visit", "dwd_inpatient_stay", "dwd_charge_detail", "dws_dept_day"], "department_scope": dept_code or "授权范围"},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
    }
