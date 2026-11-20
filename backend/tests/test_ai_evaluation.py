from etl.evaluation.run_eval import run_evaluation


def test_controlled_nl_query_benchmark_reaches_85_percent(tmp_path):
    report = run_evaluation(tmp_path / "nl_query_eval.json")
    assert report["question_count"] == 50
    assert report["accuracy"] >= 85
    assert report["passed_threshold"] is True
    assert report["failed"] == 0
