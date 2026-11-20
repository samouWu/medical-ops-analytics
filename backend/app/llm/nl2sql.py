import re
import sqlite3

import httpx

from app.core import config
from app.core.config import DB_PATH as DB_FILE

ALLOWED_TABLES = {
    "dwd_outpatient_visit", "dwd_inpatient_stay", "dwd_charge_detail",
    "dwd_emr_record", "dwd_lis_report", "dwd_finance_day",
    "dws_dept_day", "dws_disease", "dws_outpatient_day", "dws_inpatient_day",
    "dws_revenue_day", "dws_drug_day", "dws_consumable_day", "dws_disease_day",
    "dws_resource_day", "dws_service_day", "dim_department", "dim_disease",
    "dim_fee_type", "dim_date", "ads_metric_result", "metric_definition",
}
BANNED = re.compile(r"\b(insert|update|delete|drop|alter|truncate|create|replace|attach|detach|pragma|vacuum|reindex|load_extension)\b", re.I)
COMMENT = re.compile(r"(--|/\*|\*/)")
TABLE_REF = re.compile(r"\b(?:from|join)\s+([a-zA-Z_][\w]*)", re.I)
SENSITIVE_COLUMN = re.compile(r"\b(patient_key|patient_id|id_card|phone|patient_name|payload_json)\b", re.I)
AGGREGATE = re.compile(r"\b(count|sum|avg|min|max|round)\s*\(", re.I)


class NL2SQLError(ValueError):
    pass


def clean_sql(raw):
    text = (raw or "").strip()
    text = re.sub(r"^```(?:sql)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def validate_sql(raw):
    sql = clean_sql(raw)
    if not sql:
        raise NL2SQLError("模型未返回SQL")
    if COMMENT.search(sql):
        raise NL2SQLError("SQL不允许注释")
    stripped = sql.rstrip().rstrip(";")
    if ";" in stripped:
        raise NL2SQLError("只允许单条SQL")
    if not re.match(r"^(select|with)\b", stripped, re.I):
        raise NL2SQLError("只允许SELECT或WITH查询")
    if BANNED.search(stripped):
        raise NL2SQLError("SQL包含禁止的写操作或管理命令")
    if SENSITIVE_COLUMN.search(stripped):
        raise NL2SQLError("SQL不允许访问患者标识或ODS原文")
    tables = {name.lower() for name in TABLE_REF.findall(stripped)}
    if not tables:
        raise NL2SQLError("SQL必须引用允许的数仓表")
    denied = tables-ALLOWED_TABLES
    if denied:
        raise NL2SQLError("SQL访问了未授权表："+", ".join(sorted(denied)))
    if not AGGREGATE.search(stripped) and "group by" not in stripped.lower():
        raise NL2SQLError("只允许聚合查询，不返回明细个人记录")
    if "limit" not in stripped.lower():
        stripped += " LIMIT 200"
    return stripped


def execute_readonly(sql):
    safe_sql = validate_sql(sql)
    uri = f"file:{DB_FILE.as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        cursor = connection.execute(safe_sql)
        rows = [dict(row) for row in cursor.fetchmany(200)]
        columns = [item[0] for item in cursor.description or []]
        return {"sql": safe_sql, "columns": columns, "rows": rows, "row_count": len(rows)}
    except sqlite3.Error as exc:
        raise NL2SQLError(f"只读SQL执行失败：{exc}") from None
    finally:
        connection.close()


def generate_sql(question):
    provider = config.LLM_PROVIDER
    if provider == "kimi":
        key, base_url, model = config.KIMI_API_KEY, config.KIMI_BASE_URL, config.KIMI_MODEL
    else:
        provider = "deepseek"
        key, base_url, model = config.DEEPSEEK_API_KEY, config.DEEPSEEK_BASE_URL, config.DEEPSEEK_MODEL
    if not key:
        raise NL2SQLError("未配置DeepSeek/Kimi Key，无法调用模型生成SQL；受控指标问数仍可使用")
    schema = """可用表：dwd_outpatient_visit,dwd_inpatient_stay,dwd_charge_detail,dwd_emr_record,dwd_lis_report,dwd_finance_day,dws_dept_day,dws_disease,八张dws_*主题表,dim_department,dim_disease,dim_fee_type,dim_date,ads_metric_result,metric_definition。
禁止访问patient_key、patient_id、id_name、phone、patient_name、payload_json。只允许单条SELECT聚合查询，必须带LIMIT。"""
    prompt = (
        "你是医院运营SQL生成器。根据问题生成SQLite单条只读聚合SELECT，不得解释，不得使用写操作或注释。"
        "时间字段：门诊visit_date、住院discharge_date、收费fee_date、DWS stat_date。只输出SQL。\n"
        + schema + "\n问题：" + question
    )
    try:
        response = httpx.post(
            base_url.rstrip("/")+"/chat/completions",
            headers={"Authorization": "Bearer "+key},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 500},
            timeout=25,
        )
        response.raise_for_status()
        sql = response.json()["choices"][0]["message"]["content"]
        return validate_sql(sql), provider
    except (httpx.HTTPError, KeyError, IndexError, TypeError) as exc:
        raise NL2SQLError(f"模型SQL生成失败：{exc}") from None


def ask_sql(question):
    sql, provider = generate_sql(question)
    result = execute_readonly(sql)
    result["provider"] = provider
    result["intent"] = "nl2sql"
    result["query_mode"] = "model-generated-readonly-sql"
    return result
