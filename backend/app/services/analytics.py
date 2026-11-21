from datetime import date, timedelta

from app.core.database import db_session
from app.services.metrics import ACTUAL_OPEN_BEDS, METRIC_MAP, safe_ratio


def date_range(conn):
    row = conn.execute("SELECT MIN(stat_date),MAX(stat_date) FROM dws_dept_day").fetchone()
    return {"min": row[0], "max": row[1]}


def normalize_period(conn, start=None, end=None):
    available = date_range(conn)
    if not available["min"]:
        today = date.today().isoformat()
        return today, today
    start = start or available["min"]
    end = end or available["max"]
    date.fromisoformat(start)
    date.fromisoformat(end)
    if start > end:
        raise ValueError("开始日期不能晚于结束日期")
    return start, end


def scope(user, dept_code, column="dept_code"):
    allowed = user.get("dept_codes") or []
    if dept_code:
        if allowed and dept_code not in allowed:
            raise PermissionError("无权访问该科室数据")
        return f"{column}=?", [dept_code]
    if allowed:
        return f"{column} IN ({','.join('?' for _ in allowed)})", list(allowed)
    return "1=1", []


def card(key, value, unit="", fmt="number"):
    return {"key": key, "label": METRIC_MAP.get(key, {}).get("name", key), "value": value, "unit": unit or METRIC_MAP.get(key, {}).get("unit", ""), "format": fmt}


def hospital_open_bed_days(user, dept_code, start, end, raw_value):
    """全院口径开放床日按实际开放床位 345 张复算；科室与数据受限角色仍用 DWS 编制床位。"""
    if dept_code or user.get("dept_codes"):
        return raw_value
    days = (date.fromisoformat(end)-date.fromisoformat(start)).days+1
    return ACTUAL_OPEN_BEDS*days


def metric_summary(code, start, end, user, dept_code=None, conn=None):
    if conn is None:
        # 复用统一会话入口，避免临时上下文管理器被回收导致连接提前关闭。
        with db_session() as session:
            return metric_summary(code, start, end, user, dept_code, session)
    start, end = normalize_period(conn, start, end)
    where, params = scope(user, dept_code)
    aggregate = "SELECT SUM(outpatient_visits),SUM(outpatient_patients),SUM(outpatient_revenue),SUM(admissions),SUM(discharges),SUM(inpatient_revenue),SUM(drug_revenue),SUM(consumable_revenue),SUM(total_revenue),SUM(stay_days),SUM(occupied_bed_days),SUM(open_bed_days),SUM(lis_reports),SUM(abnormal_lis_reports) FROM dws_dept_day WHERE stat_date BETWEEN ? AND ? AND " + where
    a = conn.execute(aggregate, [start, end, *params]).fetchone()
    a = [x or 0 for x in a]
    days = (date.fromisoformat(end)-date.fromisoformat(start)).days+1
    open_days = hospital_open_bed_days(user, dept_code, start, end, a[11])
    values = {
        "K01": a[0], "K07": a[3], "K08": a[4], "K10": a[10], "K11": open_days,
        "K16": a[8], "K17": a[2], "K18": a[5], "K21": a[6], "K23": a[7],
        "K12": safe_ratio(a[10], open_days, 100), "K13": safe_ratio(a[9], a[4]),
        "K14": safe_ratio(a[4]*days, open_days), "K19": safe_ratio(a[2], a[0]),
        "K20": safe_ratio(a[5], a[4]), "K22": safe_ratio(a[6], a[8], 100),
        "K24": safe_ratio(a[7], a[8], 100), "K39": safe_ratio(a[13], a[12], 100),
        "K45": safe_ratio(a[10], days),
    }
    if code in ("K02", "K06", "K37"):
        sql = "SELECT COUNT(*),COUNT(DISTINCT patient_key) FROM dwd_outpatient_visit WHERE visit_date BETWEEN ? AND ? AND " + where
        total, patients = conn.execute(sql, [start, end, *params]).fetchone()
        values["K02"] = patients
        values["K06"] = safe_ratio((total or 0)-(patients or 0), total, 100)
        values["K37"] = safe_ratio(total, patients)
    elif code == "K38":
        sql = "SELECT COUNT(*),COUNT(DISTINCT patient_key) FROM dwd_inpatient_stay WHERE discharge_date BETWEEN ? AND ? AND " + where
        total, patients = conn.execute(sql, [start, end, *params]).fetchone()
        values[code] = safe_ratio(total, patients)
    elif code in ("K40", "K41"):
        sql = "SELECT COUNT(*),SUM(visit_type='专家'),SUM(visit_type='急诊') FROM dwd_outpatient_visit WHERE visit_date BETWEEN ? AND ? AND " + where
        total, expert, emergency = conn.execute(sql, [start, end, *params]).fetchone()
        values["K40"] = safe_ratio(expert or 0, total, 100)
        values["K41"] = safe_ratio(emergency or 0, total, 100)
    elif code in ("K42", "K43", "K44", "K46"):
        sql = "SELECT SUM(total_fee),SUM(drug_fee),SUM(consumable_fee),COUNT(*),SUM(stay_days=0),SUM(stay_days) FROM dwd_inpatient_stay WHERE discharge_date BETWEEN ? AND ? AND " + where
        total_fee, drug_fee, consumable_fee, discharges, same_day, stay_days = conn.execute(sql, [start, end, *params]).fetchone()
        values["K42"] = safe_ratio(drug_fee or 0, total_fee, 100)
        values["K43"] = safe_ratio(consumable_fee or 0, total_fee, 100)
        values["K44"] = safe_ratio(total_fee or 0, stay_days)
        values["K46"] = safe_ratio(same_day or 0, discharges, 100)
    elif code == "K47":
        # 只统计具有完整30天观察窗的出院，末30天出院不进入分母，避免右删失低估。
        obs_end = conn.execute("SELECT date(MAX(discharge_date),'-30 day') FROM dwd_inpatient_stay").fetchone()[0]
        stay_where, stay_params = scope(user, dept_code, "a.dept_code")
        sql = """SELECT COUNT(*),SUM(EXISTS(
            SELECT 1 FROM dwd_inpatient_stay b
            WHERE b.patient_key=a.patient_key AND b.admit_date>a.discharge_date
              AND b.admit_date<=date(a.discharge_date,'+30 day')
        )) FROM dwd_inpatient_stay a
        WHERE a.discharge_date BETWEEN ? AND ? AND a.discharge_date<=? AND """ + stay_where
        observed, readmitted = conn.execute(sql, [start, end, obs_end, *stay_params]).fetchone()
        values["K47"] = safe_ratio(readmitted or 0, observed, 100)
    elif code in ("K48", "K49"):
        stay_where, stay_params = scope(user, dept_code, "i.dept_code")
        sql = """SELECT COUNT(*),
            SUM(EXISTS(SELECT 1 FROM dwd_emr_record e WHERE e.visit_id=i.visit_id)),
            SUM(EXISTS(SELECT 1 FROM dwd_lis_report l WHERE l.visit_id=i.visit_id))
            FROM dwd_inpatient_stay i WHERE i.discharge_date BETWEEN ? AND ? AND """ + stay_where
        discharges, with_emr, with_lis = conn.execute(sql, [start, end, *stay_params]).fetchone()
        values["K48"] = safe_ratio(with_emr or 0, discharges, 100)
        values["K49"] = safe_ratio(with_lis or 0, discharges, 100)
    elif code == "K09":
        sql = "SELECT COUNT(DISTINCT patient_key) FROM dwd_inpatient_stay WHERE admit_date<=? AND discharge_date>? AND " + where
        values[code] = conn.execute(sql, [end, end, *params]).fetchone()[0]
    elif code in ("K26", "K27"):
        sql = "SELECT COUNT(*),SUM(disease_code IS NOT NULL AND disease_code!=''),SUM(total_fee) FROM dwd_inpatient_stay WHERE discharge_date BETWEEN ? AND ? AND " + where
        count, grouped, fees = conn.execute(sql, [start, end, *params]).fetchone()
        values["K26"] = safe_ratio(grouped or 0, count, 100)
        if code == "K27" and count:
            selected = conn.execute("SELECT disease_code,COUNT(*) FROM dwd_inpatient_stay WHERE discharge_date BETWEEN ? AND ? AND disease_code IS NOT NULL AND " + where + " GROUP BY disease_code", [start, end, *params]).fetchall()
            overall = conn.execute("SELECT AVG(total_fee) FROM dwd_inpatient_stay WHERE discharge_date BETWEEN ? AND ?", [start, end]).fetchone()[0]
            weighted = total_cases = 0
            for disease_code, n in selected:
                benchmark = conn.execute("SELECT AVG(total_fee) FROM dwd_inpatient_stay WHERE discharge_date BETWEEN ? AND ? AND disease_code=?", [start, end, disease_code]).fetchone()[0]
                weighted += (benchmark or 0) / overall * n if overall else 0
                total_cases += n
            values[code] = safe_ratio(weighted, total_cases)
    elif code in ("K28", "K29"):
        selected_where, selected_params = scope(user, dept_code)
        selected = conn.execute("SELECT disease_code,COUNT(*),SUM(total_fee),SUM(stay_days) FROM dwd_inpatient_stay WHERE discharge_date BETWEEN ? AND ? AND disease_code IS NOT NULL AND " + selected_where + " GROUP BY disease_code", [start, end, *selected_params]).fetchall()
        actual_fee = expected_fee = actual_days = expected_days = 0
        for disease_code, n, fees, days in selected:
            benchmark = conn.execute("SELECT AVG(total_fee),AVG(stay_days) FROM dwd_inpatient_stay WHERE discharge_date BETWEEN ? AND ? AND disease_code=?", [start, end, disease_code]).fetchone()
            actual_fee += fees or 0
            expected_fee += (benchmark[0] or 0)*n
            actual_days += days or 0
            expected_days += (benchmark[1] or 0)*n
        values["K28"] = safe_ratio(actual_fee, expected_fee)
        values["K29"] = safe_ratio(actual_days, expected_days)
    elif code in ("K31", "K32"):
        if dept_code:
            staff = conn.execute("SELECT staff_count FROM dim_department WHERE dept_code=?", (dept_code,)).fetchone()[0]
        elif user.get("dept_codes"):
            staff = conn.execute(f"SELECT SUM(staff_count) FROM dim_department WHERE dept_code IN ({','.join('?' for _ in user['dept_codes'])})", user["dept_codes"]).fetchone()[0]
        else:
            staff = conn.execute("SELECT SUM(staff_count) FROM dim_department").fetchone()[0]
        values["K31"] = safe_ratio(a[0], staff)
        values["K32"] = safe_ratio(a[8], staff)
    elif code == "K25":
        previous_start = date.fromisoformat(start).replace(year=date.fromisoformat(start).year-1).isoformat()
        previous_end = date.fromisoformat(end).replace(year=date.fromisoformat(end).year-1).isoformat()
        previous = metric_summary("K16", previous_start, previous_end, user, dept_code, conn)
        values[code] = safe_ratio(a[8]-(previous or 0), previous, 100) if previous is not None else None
    return values.get(code)


def metric_values(code, start, end, user, dept_code=None, grain="day"):
    if code not in METRIC_MAP or not METRIC_MAP[code]["supported"]:
        raise ValueError("该指标缺少源数据，暂不可计算")
    if grain not in ("day", "week", "month"):
        raise ValueError("粒度仅支持day、week或month")
    with db_session() as conn:
        start, end = normalize_period(conn, start, end)
        if grain in ("week", "month") or code in ("K09", "K25", "K26", "K27", "K28", "K29", "K31", "K32", "K40", "K41", "K42", "K43", "K44", "K45", "K46", "K47", "K48", "K49"):
            days = [date.fromisoformat(row[0]) for row in conn.execute("SELECT DISTINCT stat_date FROM dws_dept_day WHERE stat_date BETWEEN ? AND ? ORDER BY 1", (start, end))]
            if not days:
                return []
            starts = set()
            for day in days:
                if grain == "week":
                    starts.add(day-timedelta(days=day.weekday()))
                elif grain == "month":
                    starts.add(day.replace(day=1))
                else:
                    starts.add(day)
            points = []
            for period_start in sorted(starts):
                if grain == "week":
                    p_end = min(end, (period_start+timedelta(days=6)).isoformat())
                    label = period_start.isoformat()
                elif grain == "month":
                    p_end = min(end, ((period_start+timedelta(days=32)).replace(day=1)-timedelta(days=1)).isoformat())
                    label = period_start.strftime("%Y-%m")
                else:
                    p_end = min(end, period_start.isoformat())
                    label = period_start.isoformat()
                p_start = max(start, period_start.isoformat())
                points.append({"date": label, "value": metric_summary(code, p_start, p_end, user, dept_code, conn)})
            return points
        expressions = {
            "K01": "SUM(outpatient_visits)", "K02": "SUM(outpatient_patients)", "K07": "SUM(admissions)",
            "K08": "SUM(discharges)", "K10": "SUM(occupied_bed_days)", "K11": "SUM(open_bed_days)",
            "K16": "SUM(total_revenue)", "K17": "SUM(outpatient_revenue)", "K18": "SUM(inpatient_revenue)",
            "K21": "SUM(drug_revenue)", "K23": "SUM(consumable_revenue)",
            "K12": "SUM(occupied_bed_days)*100.0/NULLIF(SUM(open_bed_days),0)",
            "K13": "SUM(stay_days)/NULLIF(SUM(discharges),0)", "K14": "SUM(discharges)/NULLIF(SUM(open_bed_days),0)",
            "K19": "SUM(outpatient_revenue)/NULLIF(SUM(outpatient_visits),0)",
            "K20": "SUM(inpatient_revenue)/NULLIF(SUM(discharges),0)",
            "K22": "SUM(drug_revenue)*100.0/NULLIF(SUM(total_revenue),0)",
            "K24": "SUM(consumable_revenue)*100.0/NULLIF(SUM(total_revenue),0)",
            "K39": "SUM(abnormal_lis_reports)*100.0/NULLIF(SUM(lis_reports),0)",
        }
        if not dept_code and not user.get("dept_codes"):
            # 全院日粒度同样按实际开放床位复算，避免与区间汇总口径不一致。
            expressions["K11"] = str(ACTUAL_OPEN_BEDS)
            expressions["K12"] = f"SUM(occupied_bed_days)*100.0/{ACTUAL_OPEN_BEDS}"
            expressions["K14"] = f"SUM(discharges)*1.0/{ACTUAL_OPEN_BEDS}"
        if code == "K02":
            where, params = scope(user, dept_code)
            rows = conn.execute("SELECT visit_date,COUNT(DISTINCT patient_key) FROM dwd_outpatient_visit WHERE visit_date BETWEEN ? AND ? AND "+where+" GROUP BY visit_date ORDER BY 1", [start, end, *params])
        elif code == "K06":
            where, params = scope(user, dept_code)
            rows = conn.execute("SELECT visit_date,(COUNT(*)-COUNT(DISTINCT patient_key))*100.0/COUNT(*) FROM dwd_outpatient_visit WHERE visit_date BETWEEN ? AND ? AND "+where+" GROUP BY visit_date ORDER BY 1", [start, end, *params])
        elif code == "K37":
            where, params = scope(user, dept_code)
            rows = conn.execute("SELECT visit_date,COUNT(*)*1.0/NULLIF(COUNT(DISTINCT patient_key),0) FROM dwd_outpatient_visit WHERE visit_date BETWEEN ? AND ? AND "+where+" GROUP BY visit_date ORDER BY 1", [start, end, *params])
        elif code == "K38":
            where, params = scope(user, dept_code)
            rows = conn.execute("SELECT discharge_date,COUNT(*)*1.0/NULLIF(COUNT(DISTINCT patient_key),0) FROM dwd_inpatient_stay WHERE discharge_date BETWEEN ? AND ? AND "+where+" GROUP BY discharge_date ORDER BY 1", [start, end, *params])
        else:
            expression = expressions.get(code)
            if not expression:
                return [{"date": end, "value": metric_summary(code, start, end, user, dept_code, conn)}]
            where, params = scope(user, dept_code)
            rows = conn.execute(f"SELECT stat_date,{expression} FROM dws_dept_day WHERE stat_date BETWEEN ? AND ? AND {where} GROUP BY stat_date ORDER BY 1", [start, end, *params])
        return [{"date": row[0], "value": round(row[1], 4) if row[1] is not None else None} for row in rows]


def management(start, end, user, dept_code=None):
    with db_session() as conn:
        start, end = normalize_period(conn, start, end)
        cards = [card(code, metric_summary(code, start, end, user, dept_code, conn), fmt="currency" if code == "K16" else "percent" if code in ("K12", "K22") else "number") for code in ("K01", "K08", "K16", "K12", "K22")]
        where, params = scope(user, dept_code)
        trends = [dict(date=r[0], outpatient_visits=r[1], revenue=r[2]) for r in conn.execute("SELECT stat_date,SUM(outpatient_visits),SUM(total_revenue) FROM dws_dept_day WHERE stat_date BETWEEN ? AND ? AND "+where+" GROUP BY 1 ORDER BY 1", [start, end, *params])]
        top = [dict(dept_name=r[1], revenue=r[2]) for r in conn.execute("SELECT d.dept_code,d.dept_name,SUM(s.total_revenue) FROM dws_dept_day s JOIN dim_department d USING(dept_code) WHERE s.stat_date BETWEEN ? AND ? AND "+where.replace("dept_code", "s.dept_code")+" GROUP BY 1,2 ORDER BY 3 DESC LIMIT 5", [start, end, *params])]
        return {"cards": cards, "trends": trends, "top_departments": top, "period": {"start": start, "end": end}}


def analytics(topic, start, end, user, dept_code=None):
    topics = {"outpatient", "inpatient", "revenue", "drugs", "consumables", "disease", "resources", "service"}
    if topic not in topics:
        raise ValueError("未知分析主题")
    with db_session() as conn:
        start, end = normalize_period(conn, start, end)
        where, params = scope(user, dept_code)
        card_note = ""
        if topic in ("outpatient", "inpatient", "revenue"):
            codes = {"outpatient": ("K01", "K02", "K40", "K41", "K37", "K19", "K06"), "inpatient": ("K08", "K38", "K13", "K12", "K20", "K45", "K46", "K47"), "revenue": ("K16", "K17", "K18", "K22", "K24", "K42", "K43")}[topic]
        elif topic == "drugs": codes = ("K21", "K22", "K16")
        elif topic == "consumables": codes = ("K23", "K24", "K16")
        elif topic == "disease": codes = ("K26", "K27", "K28", "K29")
        else: codes = ("K12", "K14", "K31", "K32")
        cards = [card(code, metric_summary(code, start, end, user, dept_code, conn), fmt="currency" if code in ("K16", "K17", "K18", "K19", "K20", "K21", "K23", "K32") else "percent" if code in ("K06", "K12", "K22", "K24", "K26", "K40", "K41", "K42", "K43", "K46", "K47", "K48", "K49") else "decimal" if code in ("K13", "K14", "K27", "K28", "K29", "K31", "K45") else "number") for code in codes]
        if topic == "outpatient":
            cards.insert(1, {"key": "daily_avg", "label": "日均门诊", "value": round((cards[0]["value"] or 0)/max((date.fromisoformat(end)-date.fromisoformat(start)).days+1, 1), 2), "unit": "人次", "format": "decimal"})
            trend_code, dist_code = "K01", "outpatient_visits"
        elif topic == "inpatient":
            trend_code, dist_code = "K08", "discharges"
            card_note = "30天再入院率仅统计具有完整30天观察窗的出院；数据截止日前30天的出院不进入分母，因此 2025 年 6 月月粒度显示“—”，不是漏算。"
        elif topic == "revenue": trend_code, dist_code = "K16", "total_revenue"
        elif topic == "drugs": trend_code, dist_code = "K21", "drug_revenue"
        elif topic == "consumables": trend_code, dist_code = "K23", "consumable_revenue"
        else: trend_code, dist_code = "K08", "discharges"
        trends = [dict(point, label=METRIC_MAP[trend_code]["name"]) for point in metric_values(trend_code, start, end, user, dept_code)]
        distribution = []
        table = {"columns": [], "rows": []}
        chart_type = "line"
        trend_available = True
        stacked = waterfall = radar = heatmap = None
        if topic == "revenue":
            distribution = [{"name": "门诊收入", "value": cards[1]["value"]}, {"name": "住院收入", "value": cards[2]["value"]}]
            fee_rows = conn.execute("SELECT fee_type_name,SUM(amount) FROM dwd_charge_detail WHERE fee_date BETWEEN ? AND ? AND "+where+" GROUP BY 1 ORDER BY 2 DESC", [start, end, *params])
            table = {"columns": [{"key": "name", "label": "费用类别"}, {"key": "value", "label": "金额（元）", "format": "money"}], "rows": [{"name": r[0], "value": round(r[1], 2)} for r in fee_rows]}
            # 科室收入构成（门诊/住院堆叠）与累计贡献瀑布，单位万元
            dept_rows = conn.execute("SELECT d.dept_name,SUM(s.outpatient_revenue),SUM(s.inpatient_revenue) FROM dws_dept_day s JOIN dim_department d USING(dept_code) WHERE s.stat_date BETWEEN ? AND ? AND "+where.replace("dept_code", "s.dept_code")+" GROUP BY 1 ORDER BY (SUM(s.outpatient_revenue)+SUM(s.inpatient_revenue)) DESC", [start, end, *params]).fetchall()
            stacked = {"categories": [r[0] for r in dept_rows],
                       "series": [{"name": "门诊收入", "data": [round((r[1] or 0)/10000, 2) for r in dept_rows]},
                                  {"name": "住院收入", "data": [round((r[2] or 0)/10000, 2) for r in dept_rows]}]}
            total_wan = round(sum((r[1] or 0)+(r[2] or 0) for r in dept_rows)/10000, 2)
            waterfall = []
            running = 0.0
            head = dept_rows[:5]
            for r in head:
                amount = round(((r[1] or 0)+(r[2] or 0))/10000, 2)
                waterfall.append({"name": r[0], "value": amount, "base": round(running, 2), "display": f"{amount:,.0f}"})
                running += amount
            rest = [r for r in dept_rows[5:]]
            if rest:
                others = round(total_wan - running, 2)
                waterfall.append({"name": "其他科室", "value": others, "base": round(running, 2), "display": f"{others:,.0f}"})
                running += others
            waterfall.append({"name": "合计", "value": total_wan, "base": 0, "display": f"{total_wan:,.0f}", "color": "#18a477"})
        elif topic in ("drugs", "consumables"):
            codes_filter = ("XY", "ZC") if topic == "drugs" else ("CL",)
            rows = conn.execute(f"SELECT fee_type_name,SUM(amount) FROM dwd_charge_detail WHERE fee_date BETWEEN ? AND ? AND fee_type_code IN ({','.join('?' for _ in codes_filter)}) AND "+where+" GROUP BY 1 ORDER BY 2 DESC", [start, end, *codes_filter, *params]).fetchall()
            distribution = [{"name": r[0], "value": r[1]} for r in rows]
            total_fee = sum(r[1] or 0 for r in rows)
            table = {"columns": [{"key": "name", "label": "费别"}, {"key": "value", "label": "金额（元）", "format": "money"}, {"key": "share", "label": "占比", "format": "percent"}],
                     "rows": [{"name": r[0], "value": round(r[1], 2), "share": safe_ratio(r[1], total_fee, 100)} for r in rows]}
        elif topic == "disease":
            disease_where = where
            rows = conn.execute("SELECT i.disease_code,d.disease_name,COUNT(*) n,AVG(i.total_fee),AVG(i.stay_days) FROM dwd_inpatient_stay i JOIN dim_disease d USING(disease_code) WHERE i.discharge_date BETWEEN ? AND ? AND "+disease_where.replace("dept_code", "i.dept_code")+" GROUP BY 1,2 ORDER BY n DESC", [start, end, *params]).fetchall()
            distribution = [{"name": r[1], "value": r[2], "avg_fee": round(r[3], 2), "avg_days": round(r[4], 2)} for r in rows]
            table = {"columns": [{"key": "name", "label": "病种"}, {"key": "value", "label": "出院人次"}, {"key": "avg_fee", "label": "次均费用（元）", "format": "money"}, {"key": "avg_days", "label": "平均住院日"}], "rows": distribution}
            # 病种数按有编码的出院病例去重统计；卡片顺序对齐示范页：病种数、平均CMI、DRG入组率。
            disease_card = {"key": "disease_count", "label": "病种数", "value": len({r[0] for r in rows}), "unit": "种", "format": "number"}
            by_key = {item["key"]: item for item in cards}
            cards = [disease_card] + [by_key[code] for code in ("K27", "K26", "K28", "K29") if code in by_key]
            card_note = "病种数按有疾病编码的出院病例去重；CMI 与费用/时间消耗指数均以本院同病种均值归一，全院全期口径下恒为 1.00，下钻科室或切换单月才有区分度。"
            trends = []
            trend_available = False
            chart_type = "bar"
        elif topic == "resources":
            rows = conn.execute("SELECT d.dept_code,d.dept_name,d.bed_count,d.staff_count,SUM(s.outpatient_visits),SUM(s.discharges),SUM(s.occupied_bed_days),SUM(s.open_bed_days),SUM(s.total_revenue) FROM dws_dept_day s JOIN dim_department d USING(dept_code) WHERE s.stat_date BETWEEN ? AND ? AND "+where.replace("dept_code", "s.dept_code")+" GROUP BY 1,2,3,4 ORDER BY 8 DESC", [start, end, *params]).fetchall()
            table_rows = [{"name": r[1], "beds": r[2], "staff": r[3], "usage": safe_ratio(r[6], r[7], 100), "turnover": safe_ratio(r[5]*((date.fromisoformat(end)-date.fromisoformat(start)).days+1), r[7]), "revenue": r[8]} for r in rows]
            # 与示范页一致：按床位使用率倒序，空缺值排在最后。
            table_rows.sort(key=lambda row: (row["usage"] is None, -(row["usage"] or 0)))
            distribution = [{"name": row["name"], "value": row["usage"]} for row in table_rows]
            secondary_distribution = [{"name": row["name"], "value": row["turnover"]} for row in table_rows]
            table = {"columns": [{"key": "name", "label": "科室"}, {"key": "beds", "label": "教学配置床位"}, {"key": "usage", "label": "床位使用率"}, {"key": "turnover", "label": "床位周转次数"}, {"key": "staff", "label": "教学配置人力"}, {"key": "revenue", "label": "医疗收入（元）", "format": "money"}], "rows": table_rows}
            trends = metric_values("K08", start, end, user, dept_code)
            chart_type = "bar"
            # 科室能力雷达：取使用率前 5 的科室，四个指标各自 0-100 归一，悬停显示原值。
            def score(value, values):
                top = max(values) if values else 0
                return round((value or 0)/top*100, 1) if top else 0

            by_name = {row[1]: row for row in rows}
            # 取使用率最高、中位、最低三个科室，避免五条折线互相压盖。
            picks = {0, len(table_rows)//2, len(table_rows)-1} if table_rows else set()
            top_rows = [table_rows[index] for index in sorted(picks)]
            usages = [row["usage"] or 0 for row in top_rows]
            turnovers = [row["turnover"] or 0 for row in top_rows]
            visits = [safe_ratio(by_name[row["name"]][4] or 0, by_name[row["name"]][3] or 1) or 0 for row in top_rows]
            incomes = [safe_ratio(by_name[row["name"]][8] or 0, by_name[row["name"]][3] or 1) or 0 for row in top_rows]
            radar = {
                "indicators": [
                    {"name": "床位使用率", "max": 100},
                    {"name": "床位周转", "max": 100},
                    {"name": "人均门诊", "max": 100},
                    {"name": "人均收入", "max": 100},
                ],
                "series": [
                    {"name": row["name"], "value": [
                        score(row["usage"], usages),
                        score(row["turnover"], turnovers),
                        score(visits[index], visits),
                        score(incomes[index], incomes),
                    ]}
                    for index, row in enumerate(top_rows)
                ],
            }
            # 科室 × 月份 床位使用率热力图
            heat_rows = conn.execute("SELECT d.dept_name,substr(s.stat_date,1,7),SUM(s.occupied_bed_days),SUM(s.open_bed_days) FROM dws_dept_day s JOIN dim_department d USING(dept_code) WHERE s.stat_date BETWEEN ? AND ? AND "+where.replace("dept_code", "s.dept_code")+" GROUP BY 1,2 ORDER BY 1,2", [start, end, *params]).fetchall()
            months = sorted({r[1] for r in heat_rows})
            heat_depts = [row["name"] for row in table_rows]
            cells = [[months.index(r[1]), heat_depts.index(r[0]), round((r[2] or 0)/(r[3] or 1)*100, 2)] for r in heat_rows if r[0] in heat_depts]
            heatmap = {"xLabels": [m[5:7]+"月" for m in months], "yLabels": heat_depts, "cells": cells}
        elif topic == "service":
            service = conn.execute("SELECT SUM(lis_reports),SUM(abnormal_lis_reports) FROM dws_dept_day WHERE stat_date BETWEEN ? AND ? AND "+where, [start, end, *params]).fetchone()
            cards = [{"key": "lis", "label": "检验报告数", "value": service[0] or 0, "unit": "份", "format": "number"}, card("K39", metric_summary("K39", start, end, user, dept_code, conn), fmt="percent"), card("K49", metric_summary("K49", start, end, user, dept_code, conn), fmt="percent")]
            service_where, service_params = scope(user, dept_code, "COALESCE(o.dept_code,i.dept_code)")
            rows = conn.execute("SELECT l.item_name,COUNT(*),SUM(l.result_text IN ('异常','阳性')) FROM dwd_lis_report l LEFT JOIN dwd_outpatient_visit o ON l.visit_id=o.visit_id LEFT JOIN dwd_inpatient_stay i ON l.visit_id=i.visit_id WHERE l.report_date BETWEEN ? AND ? AND "+service_where+" GROUP BY 1 ORDER BY 2 DESC", [start, end, *service_params])
            distribution = [{"name": r[0], "value": r[1], "abnormal": r[2]} for r in rows]
            table = {"columns": [{"key": "name", "label": "检验项目"}, {"key": "value", "label": "报告数"}, {"key": "abnormal", "label": "异常/阳性数"}], "rows": distribution}
            trends = []
            trend_available = False
            chart_type = "bar"
        elif topic == "outpatient":
            rows = conn.execute("SELECT d.dept_name,COUNT(*),COUNT(DISTINCT v.patient_key),SUM(v.fee_amount) FROM dwd_outpatient_visit v JOIN dim_department d USING(dept_code) WHERE v.visit_date BETWEEN ? AND ? AND "+where.replace("dept_code", "v.dept_code")+" GROUP BY 1 ORDER BY 2 DESC", [start, end, *params]).fetchall()
            distribution = [{"name": r[0], "value": r[1]} for r in rows]
            table = {"columns": [{"key": "name", "label": "科室"}, {"key": "value", "label": "门诊人次"}, {"key": "patients", "label": "就诊患者数"}, {"key": "avg_fee", "label": "次均费用（元）", "format": "money"}],
                     "rows": [{"name": r[0], "value": r[1], "patients": r[2], "avg_fee": safe_ratio(r[3], r[1])} for r in rows]}
        elif topic == "inpatient":
            rows = conn.execute("SELECT d.dept_name,SUM(s.discharges),SUM(s.stay_days),SUM(s.inpatient_revenue) FROM dws_dept_day s JOIN dim_department d USING(dept_code) WHERE s.stat_date BETWEEN ? AND ? AND "+where.replace("dept_code", "s.dept_code")+" GROUP BY 1 ORDER BY 2 DESC", [start, end, *params]).fetchall()
            distribution = [{"name": r[0], "value": r[1]} for r in rows]
            table = {"columns": [{"key": "name", "label": "科室"}, {"key": "value", "label": "出院人次"}, {"key": "avg_stay", "label": "平均住院日"}, {"key": "avg_fee", "label": "次均费用（元）", "format": "money"}],
                     "rows": [{"name": r[0], "value": r[1], "avg_stay": safe_ratio(r[2], r[1]), "avg_fee": safe_ratio(r[3], r[1])} for r in rows]}
        else:
            rows = conn.execute("SELECT d.dept_name,SUM(s."+dist_code+") FROM dws_dept_day s JOIN dim_department d USING(dept_code) WHERE s.stat_date BETWEEN ? AND ? AND "+where.replace("dept_code", "s.dept_code")+" GROUP BY 1 ORDER BY 2 DESC", [start, end, *params])
            distribution = [{"name": r[0], "value": r[1]} for r in rows]
            table = {"columns": [{"key": "name", "label": "科室"}, {"key": "value", "label": cards[0]["label"]}], "rows": distribution}
        titles = {"outpatient": "科室门诊人次分布", "inpatient": "科室出院人次分布", "revenue": "收入构成（门诊 vs 住院）",
                  "drugs": "药品费别构成", "consumables": "耗材费别构成", "disease": "病种出院人次分布",
                  "resources": "科室床位使用率", "service": "检验项目分布"}
        source_spec = {"outpatient": ("dwd_outpatient_visit", "visit_date"), "inpatient": ("dwd_inpatient_stay", "discharge_date"),
                       "revenue": ("dwd_charge_detail", "fee_date"), "drugs": ("dwd_charge_detail", "fee_date"),
                       "consumables": ("dwd_charge_detail", "fee_date"), "disease": ("dwd_inpatient_stay", "discharge_date"),
                       "resources": ("dws_dept_day", "stat_date"), "service": ("dwd_lis_report", "report_date")}
        source_table, source_date = source_spec[topic]
        source_rows = conn.execute(f"SELECT COUNT(*) FROM {source_table} WHERE {source_date} BETWEEN ? AND ? AND {where}", [start, end, *params]).fetchone()[0]
        group_by = {"revenue": "按费别聚合", "drugs": "按费别聚合", "consumables": "按费别聚合",
                    "service": "按检验项目聚合", "disease": "按病种聚合"}.get(topic, "按科室聚合")
        source_note = f"来源 {source_table}：统计期 {source_rows:,} 行明细{group_by}，未做人工补数或放大"
        if topic == "outpatient":
            source_note += "；各科室源记录均为 900 条（课程数据集等量抽样），患者数与次均费用各不相同"
        return {"cards": cards, "trends": trends, "trend_available": trend_available, "distribution": distribution,
                "secondary_distribution": secondary_distribution if topic == "resources" else [], "table": table,
                "chart_type": chart_type, "bar_title": titles.get(topic, "结构分布"), "source_note": source_note, "card_note": card_note,
                "stacked": stacked, "waterfall": waterfall, "radar": radar, "heatmap": heatmap,
                "period": {"start": start, "end": end}}
