from pathlib import Path

from fastapi import UploadFile

from app.core.config import DATA_DIR
from app.core.database import db_session
from etl.jobs.pipeline import import_file, run_all


def test_reimport_is_idempotent():
    before = None
    with db_session() as conn:
        before = conn.execute("SELECT COUNT(*) FROM dwd_outpatient_visit").fetchone()[0]
    result = import_file("his_outpatient", DATA_DIR / "mock_his" / "his_outpatient.csv")
    with db_session() as conn:
        after = conn.execute("SELECT COUNT(*) FROM dwd_outpatient_visit").fetchone()[0]
    assert before == after == 9000
    assert result["row_count"] == 9000


def test_dwd_contains_no_direct_patient_identity():
    with db_session() as conn:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(dwd_outpatient_visit)")]
    assert "patient_name" not in columns
    assert "id_card" not in columns
    assert "phone" not in columns
    assert "patient_key" in columns


def test_incremental_run_skips_already_loaded_dates():
    result = run_all(incremental=True)
    assert all(item["row_count"] == 0 for item in result["sources"])
    assert sum(item["skipped_rows"] for item in result["sources"]) == 59922
    with db_session() as conn:
        assert conn.execute("SELECT COUNT(*) FROM dwd_outpatient_visit").fetchone()[0] == 9000
        assert conn.execute("SELECT COUNT(*) FROM dwd_charge_detail").fetchone()[0] == 44078


def test_dwd_wide_combines_outpatient_and_inpatient():
    with db_session() as conn:
        wide_count = conn.execute("SELECT COUNT(*) FROM dwd_encounter_wide").fetchone()[0]
        outpatient = conn.execute("SELECT COUNT(*) FROM dwd_outpatient_visit").fetchone()[0]
        inpatient = conn.execute("SELECT COUNT(*) FROM dwd_inpatient_stay").fetchone()[0]
        assert wide_count == outpatient + inpatient == 10500
        assert conn.execute("SELECT COUNT(*) FROM dwd_encounter_wide WHERE source_type='outpatient'").fetchone()[0] == 9000
        assert conn.execute("SELECT COUNT(*) FROM dwd_encounter_wide WHERE source_type='inpatient'").fetchone()[0] == 1500


def test_theme_marts_dim_date_and_ads_grains():
    theme_tables = (
        "dws_outpatient_day", "dws_inpatient_day", "dws_revenue_day", "dws_drug_day",
        "dws_consumable_day", "dws_disease_day", "dws_resource_day", "dws_service_day",
    )
    with db_session() as conn:
        for table in theme_tables:
            assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] > 0, table
        assert conn.execute("SELECT COUNT(*) FROM dim_date").fetchone()[0] == 91
        grains = {row[0] for row in conn.execute("SELECT DISTINCT grain FROM ads_metric_result")}
        assert grains == {"day", "week", "month"}
        assert conn.execute("SELECT COUNT(*) FROM ads_metric_result WHERE grain='month'").fetchone()[0] == 990
        assert conn.execute("SELECT COUNT(DISTINCT metric_code) FROM ads_metric_result").fetchone()[0] == 30
        assert conn.execute("SELECT COUNT(*) FROM ads_metric_result").fetchone()[0] == 35640
        assert conn.execute("SELECT COUNT(value_num) FROM ads_metric_result WHERE metric_code='K25'").fetchone()[0] == 0
        sum_checks = {
            "dws_outpatient_day": ("visits", "outpatient_visits"),
            "dws_inpatient_day": ("discharges", "discharges"),
            "dws_revenue_day": ("total_revenue", "total_revenue"),
            "dws_drug_day": ("drug_revenue", "drug_revenue"),
            "dws_consumable_day": ("consumable_revenue", "consumable_revenue"),
            "dws_service_day": ("lis_reports", "lis_reports"),
        }
        for table, (theme_column, source_column) in sum_checks.items():
            expected = conn.execute(f"SELECT SUM({source_column}) FROM dws_dept_day").fetchone()[0]
            actual = conn.execute(f"SELECT SUM({theme_column}) FROM {table}").fetchone()[0]
            assert round(actual, 4) == round(expected, 4), table
        for table in theme_tables:
            total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            unique = conn.execute(f"SELECT COUNT(*) FROM (SELECT DISTINCT * FROM {table})").fetchone()[0]
            assert total == unique, table
        ads_revenue = conn.execute("SELECT SUM(value_num) FROM ads_metric_result WHERE metric_code='K16' AND grain='month' AND dept_code='ALL'").fetchone()[0]
        source_revenue = conn.execute("SELECT SUM(total_revenue) FROM dws_dept_day").fetchone()[0]
        assert round(ads_revenue, 4) == round(source_revenue, 4)
        ads_visits = conn.execute("SELECT SUM(value_num) FROM ads_metric_result WHERE metric_code='K01' AND grain='month' AND dept_code='ALL'").fetchone()[0]
        source_visits = conn.execute("SELECT SUM(outpatient_visits) FROM dws_dept_day").fetchone()[0]
        assert ads_visits == source_visits
