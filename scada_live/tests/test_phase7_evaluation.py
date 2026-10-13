import pytest
import os
import pandas as pd
from scada_live.common.config_loader import load_config
from experiments.run_full_evaluation import (
    run_single_simulation,
    execute_full_benchmark,
    generate_markdown_report,
    SCENARIO_METADATA
)


@pytest.fixture
def test_cfg():
    cfg = load_config('scada_live/config.yaml')
    cfg.simulation.clamp_flow_noise = False
    return cfg


def test_scenario_metadata_integrity():
    assert len(SCENARIO_METADATA) == 12
    for sc_id, meta in SCENARIO_METADATA.items():
        assert "name" in meta
        assert "category" in meta
        assert "vector" in meta
        assert "ticks" in meta
        assert "init_h" in meta


def test_run_single_simulation_norm(test_cfg):
    res = run_single_simulation("NORM", seed=201, mode="prevention", cfg=test_cfg)
    assert res["scenario"] == "NORM"
    assert res["seed"] == 201
    assert res["mode"] == "prevention"
    assert res["overflow_ticks"] == 0
    assert res["dry_run_ticks"] == 0
    assert res["false_alarms"] == 0


def test_run_single_simulation_am1_prevention(test_cfg):
    res = run_single_simulation("AM-1", seed=201, mode="prevention", cfg=test_cfg)
    assert res["scenario"] == "AM-1"
    assert res["ingress_blocked"] is True
    assert res["overflow_ticks"] == 0


def test_execute_benchmark_fast_smoke(test_cfg, tmp_path):
    # Run smoke benchmark on 1 seed for 2 scenarios
    test_seeds = [201]
    df_raw, df_detection, df_harm = execute_full_benchmark(test_cfg, seeds=test_seeds)

    assert isinstance(df_raw, pd.DataFrame)
    assert len(df_raw) == 12 * 1 * 2  # 12 scenarios x 1 seed x 2 modes = 24 runs
    assert "scenario" in df_raw.columns
    assert "overflow_ticks" in df_raw.columns
    assert "dry_run_ticks" in df_raw.columns

    assert len(df_detection) == 12
    assert "Event Recall (TPR)" in df_detection.columns

    assert len(df_harm) == 12
    assert "Harm Reduction" in df_harm.columns

    # Test report generation
    report_file = tmp_path / "test_report.md"
    generate_markdown_report(df_detection, df_harm, str(report_file))
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "SCADA Hybrid IDS — Consolidated Benchmark Evaluation Report" in content
    assert "Detection Performance Matrix" in content
