from src.sample_data import generate_sample_programs, generate_child_population_sample
from src.metrics import compute_district_age_metrics, compute_weekly_choice_metrics


def test_sample_pipeline_smoke():
    programs = generate_sample_programs(n=50, seed=1)
    population = generate_child_population_sample(seed=1)
    weekly = compute_weekly_choice_metrics(programs, population)
    metrics = compute_district_age_metrics(programs, population)
    assert not weekly.empty
    assert not metrics.empty
    assert {"choice_index", "planb_index", "barrier_index"}.issubset(metrics.columns)
