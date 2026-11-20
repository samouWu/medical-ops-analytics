import pytest

from app.llm.nl2sql import NL2SQLError, execute_readonly, validate_sql


def test_readonly_sql_executes_aggregate_query():
    result = execute_readonly("SELECT dept_code,SUM(amount) AS revenue FROM dwd_charge_detail GROUP BY dept_code")
    assert result["sql"].lower().endswith("limit 200")
    assert result["row_count"] == 10
    assert {"dept_code", "revenue"} <= set(result["columns"])


def test_readonly_sql_rejects_write_and_multiple_statements():
    with pytest.raises(NL2SQLError):
        validate_sql("DELETE FROM dwd_charge_detail")
    with pytest.raises(NL2SQLError):
        validate_sql("SELECT COUNT(*) FROM dwd_charge_detail; DROP TABLE app_user")


def test_readonly_sql_rejects_sensitive_columns_and_unapproved_tables():
    with pytest.raises(NL2SQLError):
        validate_sql("SELECT COUNT(patient_key) FROM dwd_outpatient_visit")
    with pytest.raises(NL2SQLError):
        validate_sql("SELECT COUNT(*) FROM app_user")
    with pytest.raises(NL2SQLError):
        validate_sql("SELECT * FROM dwd_charge_detail")


def test_readonly_sql_requires_aggregation():
    with pytest.raises(NL2SQLError):
        validate_sql("SELECT charge_id FROM dwd_charge_detail LIMIT 10")
