import re
from datetime import date, timedelta

import httpx

from app.core import config
from app.core.database import db_session
from app.services.analytics import metric_summary, metric_values, normalize_period
from app.services.metrics import METRIC_MAP

BASE_ALIASES = [
    ("K20", ("出院次均费用", "住院次均费用")), ("K19", ("门诊次均费用", "次均费用")),
    ("K27", ("CMI", "病例组合指数")), ("K26", ("DRG入组率", "入组率")),
    ("K12", ("床位使用率", "床位利用")), ("K13", ("平均住院日",)),
    ("K14", ("床位周转",)), ("K22", ("药占比", "药品占比")), ("K24", ("耗占比", "耗材占比")),
    ("K08", ("出院人次", "出院人数")), ("K07", ("入院人次", "入院人数")),
    ("K17", ("门诊收入",)), ("K18", ("住院收入",)), ("K16", ("医疗总收入", "总收入", "收入")),
    ("K21", ("药品收入",)), ("K23", ("耗材收入",)), ("K02", ("门诊就诊人数", "门诊人数")),
    ("K01", ("门诊就诊人次", "门诊人次", "门诊量")), ("K06", ("复诊率",)),
    ("K31", ("人均门诊服务量",)), ("K32", ("人均业务收入",)),
]
_alias_pairs = []
for _code, _aliases in BASE_ALIASES:
    _alias_pairs.extend((_code, _alias) for _alias in _aliases)
for _code, _metric in METRIC_MAP.items():
    if _metric["supported"]:
        _alias_pairs.append((_code, _metric["name"]))
# 长别名优先，避免“药品收入”被“收入”错误识别成K16。
ALIASES = [(code, (alias,)) for code, alias in sorted(_alias_pairs, key=lambda item: len(item[1]), reverse=True)]
DANGEROUS = re.compile(r"drop|delete|update|insert|alter|truncate|身份证|手机号|患者姓名|病历明细|\d{17}[\dXx]|(?<!\d)1[3-9]\d{9}(?!\d)", re.I)


def resolve_period(question, available):
    max_date = date.fromisoformat(available["max"])
    min_date = date.fromisoformat(available["min"])
    match = re.search(r"(20\d{2})[年/-](\d{1,2})月?", question)
    if match:
        year, month = int(match.group(1)), int(match.group(2))
        if not 1 <= month <= 12:
            raise ValueError("月份应为1到12")
        start = date(year, month, 1)
    else:
        match = re.search(r"(?<!\d)(\d{1,2})月", question)
        if match:
            month = int(match.group(1))
            if not 1 <= month <= 12:
                raise ValueError("月份应为1到12")
            start = date(max_date.year, month, 1)
        elif "上月" in question:
            start = (max_date.replace(day=1)-timedelta(days=1)).replace(day=1)
        elif "本月" in question:
            start = max_date.replace(day=1)
        elif "上周" in question:
            this_monday = max_date-timedelta(days=max_date.weekday())
            return (this_monday-timedelta(days=7)).isoformat(), (this_monday-timedelta(days=1)).isoformat()
        elif re.search(r"(?:近|最近)\d+天", question):
            days = int(re.search(r"(?:近|最近)(\d+)天", question).group(1))
            if days < 1 or days > 366:
                raise ValueError("近N天范围应为1到366")
            return (max_date-timedelta(days=days-1)).isoformat(), max_date.isoformat()
        elif "本周" in question:
            return (max_date-timedelta(days=max_date.weekday())).isoformat(), max_date.isoformat()
        else:
            return min_date.isoformat(), max_date.isoformat()
    end = (start.replace(day=28)+timedelta(days=5)).replace(day=1)-timedelta(days=1)
    return max(start, min_date).isoformat(), min(end, max_date).isoformat()


def parse_question(question, user, conn):
    if not question or len(question) > 300:
        raise ValueError("问题长度应为1到300字")
    if DANGEROUS.search(question):
        raise PermissionError("仅支持聚合运营指标查询，已拒绝危险或敏感请求")
    metric_code = next((code for code, aliases in ALIASES if any(alias.lower() in question.lower() for alias in aliases)), None)
    if not metric_code:
        raise ValueError("暂未识别指标，可尝试询问门诊量、出院人次、床位使用率、平均住院日或药占比")
    if not METRIC_MAP[metric_code]["supported"]:
        raise ValueError("该指标缺少源数据，暂不可计算")
    dept = None
    for row in conn.execute("SELECT dept_code,dept_name FROM dim_department"):
        short_name = row[1].replace("内科", "").replace("外科", "")
        if row[1] in question or (len(short_name) >= 2 and short_name in question):
            dept = row[0]
            break
    if user.get("dept_codes"):
        if dept and dept not in user["dept_codes"]:
            raise PermissionError("无权查询该科室")
        dept = dept or user["dept_codes"][0]
    start, end = resolve_period(question, date_range(conn))
    return metric_code, dept, start, end


def date_range(conn):
    row = conn.execute("SELECT MIN(stat_date),MAX(stat_date) FROM dws_dept_day").fetchone()
    if not row[0]:
        raise ValueError("数仓暂无数据，请先执行ETL")
    return {"min": row[0], "max": row[1]}


def format_value(code, value):
    if value is None:
        return "暂无可用数据"
    unit = METRIC_MAP[code]["unit"]
    if unit == "%":
        return f"{value:.2f}%"
    if unit.startswith("元"):
        # 大额金额统一折合万元，小额的次均费用等仍按元展示。
        if abs(value) >= 100000:
            return f"{value/10000:,.2f}{unit.replace('元', '万元')}"
        return f"{value:,.2f}{unit}"
    return f"{value:,.2f}{unit}"


def llm_interpretation(question, facts):
    provider = config.LLM_PROVIDER
    if provider == "kimi":
        key, base_url, model = config.KIMI_API_KEY, config.KIMI_BASE_URL, config.KIMI_MODEL
    else:
        provider = "deepseek"
        key, base_url, model = config.DEEPSEEK_API_KEY, config.DEEPSEEK_BASE_URL, config.DEEPSEEK_MODEL
    if not key:
        return None, "local-rules"
    prompt = "你是医院运营分析助手。仅根据给定聚合数据生成80字以内中文解读，不补充不存在的原因，不输出SQL或患者信息。\n" + facts
    try:
        response = httpx.post(base_url.rstrip("/")+"/chat/completions", headers={"Authorization": "Bearer "+key}, json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "max_tokens": 180}, timeout=25)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip(), provider
    except (httpx.HTTPError, KeyError, IndexError):
        return None, "local-rules-fallback"


def ask(question, user, start_override=None, end_override=None, dept_override=None):
    with db_session() as conn:
        metric_code, dept, start, end = parse_question(question, user, conn)
        dept = dept or dept_override
        explicit_period = bool(re.search(r"20\d{2}[年/-]\d{1,2}月?|\d{1,2}月|上月|本月|上周|本周|近\d+天|最近\d+天", question))
        if not explicit_period:
            start = start_override or start
            end = end_override or end
        start, end = normalize_period(conn, start, end)
        value = metric_summary(metric_code, start, end, user, dept, conn)
        points = metric_values(metric_code, start, end, user, dept, "day" if start[:7] == end[:7] else "day")
        dept_name = "全院"
        if dept:
            dept_name = conn.execute("SELECT dept_name FROM dim_department WHERE dept_code=?", (dept,)).fetchone()[0]
    metric = METRIC_MAP[metric_code]
    facts = f"问题：{question}\n统计期：{start}至{end}；范围：{dept_name}；指标：{metric['name']}；结果：{format_value(metric_code, value)}；口径：{metric['description']}"
    generated, provider = llm_interpretation(question, facts)
    answer = generated or f"{start}至{end}，{dept_name}{metric['name']}为{format_value(metric_code, value)}。结果来自统一指标口径与ADS/DWD数据，未使用患者明细展示。"
    return {"answer": answer, "provider": provider, "intent": "metric_query", "query_mode": "controlled-metric-query", "metric_code": metric_code, "value": value, "period": {"start": start, "end": end}, "department": dept_name, "points": points, "chart": {"type": "line", "title": metric["name"]+"趋势"}}
