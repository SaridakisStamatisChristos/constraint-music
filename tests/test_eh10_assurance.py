from __future__ import annotations

import json
from pathlib import Path

import pytest
from research.generate_eh10_evidence import generate

_RESULTS = Path(__file__).resolve().parents[1] / "research" / "results"


@pytest.fixture(scope="module")
def evidence() -> tuple[list[dict[str, object]], dict[str, object], dict[str, object]]:
    return generate()


def test_internal_ablation_has_exact_complete_accounting(
    evidence: tuple[list[dict[str, object]], dict[str, object], dict[str, object]],
) -> None:
    rows, summary, _ = evidence
    assert len(rows) == 32
    assert summary["attack_denominator"] == 30
    assert summary["control_denominator"] == 2
    assert summary["full_detected"] == 30
    assert summary["false_positive_controls"] == []
    leave_one_out = summary["leave_one_channel_out"]
    assert isinstance(leave_one_out, dict)
    assert {
        channel: metrics["unique_catch_count"]
        for channel, metrics in leave_one_out.items()
    } == {
        "wire_shape": 6,
        "semantic_rules": 5,
        "integrity_request": 7,
        "delivery_parseback": 6,
    }


def test_pinned_scope_normalized_adapters_have_exact_denominators(
    evidence: tuple[list[dict[str, object]], dict[str, object], dict[str, object]],
) -> None:
    _, _, comparators = evidence
    assert comparators["comparator"] == {
        "package": "music21",
        "required_version": "9.9.2",
        "observed_version": "9.9.2",
        "source_tag": "v9.9.2",
        "release_commit": "aa9780a",
        "license": "BSD-3-Clause",
    }
    adapters = comparators["adapters"]
    assert isinstance(adapters, list)
    assert [
        (adapter["adapter_id"], adapter["case_denominator"], adapter["disagreements"])
        for adapter in adapters
    ] == [
        ("music21-voice-leading-v1", 9840, 0),
        ("music21-c-major-triad-v1", 126, 0),
    ]


def test_checked_in_eh10_evidence_replays_exactly(
    evidence: tuple[list[dict[str, object]], dict[str, object], dict[str, object]],
) -> None:
    rows, summary, comparators = evidence
    checked_rows = [
        json.loads(line)
        for line in (_RESULTS / "assurance_ablation_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    checked_summary = json.loads(
        (_RESULTS / "assurance_ablation_summary.json").read_text(encoding="utf-8")
    )
    checked_comparators = json.loads(
        (_RESULTS / "external_comparator_summary.json").read_text(encoding="utf-8")
    )
    assert rows == checked_rows
    assert summary == checked_summary
    assert comparators == checked_comparators
