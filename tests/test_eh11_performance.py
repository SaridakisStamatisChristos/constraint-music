from __future__ import annotations

import json
from pathlib import Path

from research import benchmark_performance as perf


def _case(profile: str, bars: int = 4) -> perf.Case:
    return perf.Case(
        workload="single",
        profile=profile,
        bars=bars,
        seed=7,
        workers=1,
        worker_mode="single",
        time_limit_seconds=0.1,
    )


def test_config_and_matrix_cover_required_sizes_profiles_and_worker_modes(
    monkeypatch,
) -> None:
    monkeypatch.setattr(perf.os, "cpu_count", lambda: 4)
    config = perf.load_config(Path("research/configs/eh11_performance_matrix.json"))
    cases = perf.matrix(config)

    single = [case for case in cases if case.workload == "single"]
    assert {case.bars for case in single} == {1, 2, 4, 8, 16, 32}
    assert {case.profile for case in single} == set(config["profiles"])
    assert {case.worker_mode for case in single} == {"single", "throughput"}
    assert len(single) == 9 * 6 * 5 * 2

    multi = [case for case in cases if case.workload == "multi_output"]
    assert len(multi) == 3 * 3 * 2
    assert {case.multi_output_count for case in multi} == {3}


def test_profile_builder_records_scope_exclusions_and_valid_modulation() -> None:
    spec, reason = perf.build_spec(_case("rhythm_motifs", bars=1))
    assert spec is None
    assert reason is not None

    spec, reason = perf.build_spec(_case("declared_modulation", bars=1))
    assert reason is None
    assert spec is not None
    assert spec.modulation_enabled
    assert spec.modulation_boundary_beat == 2


def test_summary_keeps_unknown_and_internal_error_in_runnable_denominator() -> None:
    rows = [
        {
            "workload": "single",
            "profile": "base_satb",
            "bars": 4,
            "worker_mode": "single",
            "outcome": "success",
            "solver_status": "OPTIMAL",
            "attempted_count": 1,
            "excluded_count": 0,
            "generated_count": 1,
            "accepted_count": 1,
            "released_count": 1,
            "generation_total_seconds": 1.0,
            "peak_rss_bytes": 100.0,
            "certification_total_seconds": 0.1,
            "verification_overhead_ratio": 0.1,
            "compile_seconds": 0.1,
            "solve_seconds": 0.7,
            "semantic_verification_seconds": 0.02,
            "artifact_parse_seconds": 0.01,
            "strict_semantic_recheck_seconds": 0.02,
            "integrity_request_binding_exclusive_seconds": 0.01,
            "export_seconds": 0.01,
            "parseback_and_delivery_seconds": 0.03,
        },
        {
            "workload": "single",
            "profile": "base_satb",
            "bars": 4,
            "worker_mode": "single",
            "outcome": "no_solution",
            "solver_status": "UNKNOWN",
            "attempted_count": 1,
            "excluded_count": 0,
            "generated_count": 0,
            "accepted_count": 0,
            "released_count": 0,
        },
        {
            "workload": "single",
            "profile": "base_satb",
            "bars": 4,
            "worker_mode": "single",
            "outcome": "internal_error",
            "solver_status": "ERROR",
            "attempted_count": 1,
            "excluded_count": 0,
            "generated_count": 0,
            "accepted_count": 0,
            "released_count": 0,
        },
        {
            "workload": "single",
            "profile": "rhythm_motifs",
            "bars": 1,
            "worker_mode": "single",
            "outcome": "excluded",
            "solver_status": "NOT_RUN",
            "attempted_count": 1,
            "excluded_count": 1,
            "generated_count": 0,
            "accepted_count": 0,
            "released_count": 0,
        },
    ]

    summary = perf.summarize(rows)["single_output"]
    assert summary["attempted"] == 4
    assert summary["excluded"] == 1
    assert summary["runnable"] == 3
    assert summary["generated"] == 1
    assert summary["generation_yield"] == 1 / 3
    assert summary["solver_statuses"]["UNKNOWN"] == 1
    assert summary["outcomes"]["internal_error"] == 1

    base_group = next(
        group
        for group in summary["groups"]
        if group["profile"] == "base_satb" and group["bars"] == 4
    )
    assert base_group["successful_generation_seconds"]["n"] == 1
    assert base_group["successful_generation_seconds"]["p90"] is None


def test_result_validation_detects_summary_tampering(tmp_path: Path) -> None:
    rows = [
        {
            "workload": "single",
            "profile": "base_satb",
            "bars": 1,
            "worker_mode": "single",
            "outcome": "excluded",
            "solver_status": "NOT_RUN",
            "attempted_count": 1,
            "excluded_count": 1,
            "generated_count": 0,
            "accepted_count": 0,
            "released_count": 0,
        }
    ]
    summary = perf.summarize(rows)
    env = {"benchmark_version": perf.VERSION}
    perf.write(tmp_path, rows, summary, env)
    perf.validate(tmp_path)

    summary_path = tmp_path / "eh11_performance_summary.json"
    tampered = json.loads(summary_path.read_text(encoding="utf-8"))
    tampered["single_output"]["generated"] = 99
    summary_path.write_text(json.dumps(tampered), encoding="utf-8")

    try:
        perf.validate(tmp_path)
    except ValueError as exc:
        assert "does not reproduce" in str(exc)
    else:
        raise AssertionError("tampered summary must fail validation")
