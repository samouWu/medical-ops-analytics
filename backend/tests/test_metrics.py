from app.services.metrics import METRICS, safe_ratio
from etl.jobs.pipeline import patient_key


def test_ratio_formula_examples():
    assert safe_ratio(850, 1000, 100) == 85
    assert safe_ratio(160, 20) == 8
    assert safe_ratio(20, 100, 100) == 20
    assert safe_ratio(90, 100, 100) == 90
    assert safe_ratio(1, 0, 100) is None


def test_metric_catalog_has_40_unique_entries():
    assert len(METRICS) == 40
    assert len({row[0] for row in METRICS}) == 40
    assert sum(bool(row[4]) for row in METRICS) == 31


def test_patient_identifier_is_one_way_and_stable():
    assert patient_key("P001") == patient_key("P001")
    assert patient_key("P001") != patient_key("P002")
    assert "P001" not in patient_key("P001")
