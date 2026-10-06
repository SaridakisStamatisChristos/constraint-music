from __future__ import annotations

import importlib.metadata
import json
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

import pytest
from research.validate_release_assurance import (
    DEFAULT_MANIFEST,
    ROOT,
    EvidenceArtifact,
    ReleaseAssuranceError,
    _run_checked,
    load_release_manifest,
    validate_claim_boundary,
    validate_environment,
    validate_evidence_hashes,
)


def test_release_manifest_covers_every_evidence_artifact() -> None:
    manifest = load_release_manifest()

    assert manifest.suite_id == "eh12-release-assurance-v1"
    assert len(manifest.evidence) == 12
    assert {artifact.replay_group for artifact in manifest.evidence} == {
        None,
        "bounded",
        "corruption",
        "eh10",
        "eh12",
    }
    validate_evidence_hashes(manifest)


def test_release_manifest_rejects_path_traversal(tmp_path: Path) -> None:
    raw = json.loads(DEFAULT_MANIFEST.read_text(encoding="utf-8"))
    raw["evidence"][0]["path"] = "../outside.json"
    path = tmp_path / "release.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ReleaseAssuranceError, match="normalized relative path"):
        load_release_manifest(path)


def test_evidence_hash_drift_fails_closed(tmp_path: Path) -> None:
    results = tmp_path / "research/results"
    results.mkdir(parents=True)
    evidence = results / "one.json"
    evidence.write_text("changed\n", encoding="utf-8")
    manifest = load_release_manifest()
    reduced = replace(
        manifest,
        evidence=(EvidenceArtifact("research/results/one.json", "0" * 64, None),),
    )

    with pytest.raises(ReleaseAssuranceError, match="SHA-256 drift"):
        validate_evidence_hashes(reduced, root=tmp_path)


def test_environment_requires_exact_installed_pins() -> None:
    manifest = load_release_manifest()

    def wrong_version(name: str) -> str:
        if name == "ortools":
            return "9.14.0"
        return manifest.pinned_dependencies[name]

    with pytest.raises(ReleaseAssuranceError, match="installed ortools version"):
        validate_environment(manifest, distribution_version=wrong_version)


def test_environment_rejects_missing_dependency() -> None:
    manifest = load_release_manifest()

    def missing(_name: str) -> str:
        raise importlib.metadata.PackageNotFoundError

    with pytest.raises(ReleaseAssuranceError, match="required dependency is not installed"):
        validate_environment(manifest, distribution_version=missing)


def test_claim_boundary_matches_the_only_remaining_review_blocker() -> None:
    decision, blockers = validate_claim_boundary(load_release_manifest())

    assert decision == "HOLD"
    assert blockers == ("EH12-G04",)


def test_claim_statement_drift_fails_closed() -> None:
    manifest = replace(
        load_release_manifest(),
        claim_statement_sha256="0" * 64,
    )

    with pytest.raises(ReleaseAssuranceError, match="frozen claim statement SHA-256 drift"):
        validate_claim_boundary(manifest)


def test_failed_subcommand_fails_closed() -> None:
    def failing_runner(
        _command: tuple[str, ...],
        _cwd: Path,
        _environment: Mapping[str, str] | None,
    ) -> int:
        return 23

    with pytest.raises(ReleaseAssuranceError, match="exit code 23"):
        _run_checked(
            "deliberate failure",
            ("python", "-m", "example"),
            root=ROOT,
            runner=failing_runner,
        )
