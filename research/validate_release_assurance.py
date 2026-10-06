"""Run the complete, fail-closed EH-12 release-assurance gate."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import subprocess
import sys
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import Any

from .validate_eh12_closure import load_matrix, validate_matrix

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "research/configs/release_assurance_manifest.json"
DEFAULT_MATRIX = ROOT / "research/configs/eh12_closure_matrix.json"
DEFAULT_DOCUMENT = ROOT / "docs/EH12_CLOSURE_MATRIX.md"
DEFAULT_PYPROJECT = ROOT / "pyproject.toml"

_HEX_DIGITS = frozenset("0123456789abcdef")
_REPLAY_COMMANDS: Mapping[str, tuple[str, tuple[str, ...], tuple[str, ...]]] = {
    "bounded": (
        "research.enumerate_fragments",
        ("--output", "{directory}/bounded_conformance.json"),
        ("research/results/bounded_conformance.json",),
    ),
    "corruption": (
        "research.generate_corruption_evidence",
        ("--directory", "{directory}"),
        (
            "research/results/corruption_benchmark.jsonl",
            "research/results/corruption_manifest.json",
            "research/results/corruption_summary.json",
        ),
    ),
    "eh10": (
        "research.generate_eh10_evidence",
        ("--directory", "{directory}"),
        (
            "research/results/assurance_ablation_rows.jsonl",
            "research/results/assurance_ablation_summary.json",
            "research/results/external_comparator_summary.json",
        ),
    ),
    "eh12": (
        "research.eh12_assurance_corpus",
        ("--directory", "{directory}"),
        (
            "research/results/eh12_assurance_raw.jsonl",
            "research/results/eh12_assurance_summary.json",
        ),
    ),
}

CommandRunner = Callable[[tuple[str, ...], Path, Mapping[str, str] | None], int]


class ReleaseAssuranceError(RuntimeError):
    """Raised when any release-assurance invariant fails."""


@dataclass(frozen=True, slots=True)
class EvidenceArtifact:
    path: str
    sha256: str
    replay_group: str | None


@dataclass(frozen=True, slots=True)
class ReleaseManifest:
    suite_id: str
    supported_python: tuple[str, ...]
    pinned_dependencies: Mapping[str, str]
    claim_id: str
    claim_statement_sha256: str
    expected_publication_decision: str
    expected_blockers: tuple[str, ...]
    evidence: tuple[EvidenceArtifact, ...]


@dataclass(frozen=True, slots=True)
class ReleaseSummary:
    suite_id: str
    python_version: str
    source_commit: str
    source_tree: str
    evidence_artifacts: int
    replay_groups: int
    publication_decision: str
    blockers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CheckoutAttestation:
    """Machine-verifiable identity of the clean source tree under review."""

    commit: str
    tree: str


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReleaseAssuranceError(f"{location} must be an object")
    return value


def _sequence(value: object, location: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise ReleaseAssuranceError(f"{location} must be an array")
    return value


def _text(value: object, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReleaseAssuranceError(f"{location} must be a non-empty string")
    return value


def _sha(value: object, location: str) -> str:
    digest = _text(value, location)
    if len(digest) != 64 or any(character not in _HEX_DIGITS for character in digest):
        raise ReleaseAssuranceError(f"{location} must be a lowercase SHA-256 digest")
    return digest


def _relative_path(value: object, location: str) -> str:
    path = PurePosixPath(_text(value, location))
    if path.is_absolute() or ".." in path.parts or path.as_posix() != str(value):
        raise ReleaseAssuranceError(f"{location} must be a normalized relative path")
    return path.as_posix()


def load_release_manifest(path: Path = DEFAULT_MANIFEST) -> ReleaseManifest:
    """Load and structurally validate the release-assurance manifest."""

    raw = json.loads(path.read_text(encoding="utf-8"))
    root = _mapping(raw, "manifest")
    if root.get("schema_version") != 1:
        raise ReleaseAssuranceError("manifest.schema_version must be 1")
    suite_id = _text(root.get("suite_id"), "manifest.suite_id")
    if suite_id != "eh12-release-assurance-v1":
        raise ReleaseAssuranceError("unexpected release-assurance suite_id")

    supported_python = tuple(
        _text(item, f"manifest.supported_python[{index}]")
        for index, item in enumerate(
            _sequence(root.get("supported_python"), "manifest.supported_python")
        )
    )
    if supported_python != ("3.11", "3.12", "3.13"):
        raise ReleaseAssuranceError("supported_python must be exactly 3.11, 3.12, and 3.13")

    raw_dependencies = _mapping(
        root.get("pinned_dependencies"), "manifest.pinned_dependencies"
    )
    pinned_dependencies = {
        _text(name, "manifest.pinned_dependencies key"): _text(
            version, f"manifest.pinned_dependencies.{name}"
        )
        for name, version in raw_dependencies.items()
    }
    if set(pinned_dependencies) != {"music21", "ortools"}:
        raise ReleaseAssuranceError("pinned_dependencies must contain music21 and ortools")

    closure = _mapping(root.get("closure"), "manifest.closure")
    expected_blockers = tuple(
        _text(item, f"manifest.closure.expected_blockers[{index}]")
        for index, item in enumerate(
            _sequence(
                closure.get("expected_blockers"),
                "manifest.closure.expected_blockers",
            )
        )
    )

    artifacts: list[EvidenceArtifact] = []
    seen_paths: set[str] = set()
    for index, raw_artifact in enumerate(
        _sequence(root.get("evidence"), "manifest.evidence")
    ):
        location = f"manifest.evidence[{index}]"
        artifact = _mapping(raw_artifact, location)
        artifact_path = _relative_path(artifact.get("path"), f"{location}.path")
        if artifact_path in seen_paths:
            raise ReleaseAssuranceError(f"duplicate evidence path: {artifact_path}")
        seen_paths.add(artifact_path)
        replay_value = artifact.get("replay_group")
        if replay_value is not None and replay_value not in _REPLAY_COMMANDS:
            raise ReleaseAssuranceError(f"{location}.replay_group is unknown")
        artifacts.append(
            EvidenceArtifact(
                path=artifact_path,
                sha256=_sha(artifact.get("sha256"), f"{location}.sha256"),
                replay_group=replay_value,
            )
        )

    expected_paths = {
        path for _module, _arguments, outputs in _REPLAY_COMMANDS.values() for path in outputs
    }
    replayed_paths = {artifact.path for artifact in artifacts if artifact.replay_group}
    if replayed_paths != expected_paths:
        raise ReleaseAssuranceError(
            "replayed evidence must exactly cover the configured deterministic outputs"
        )
    for artifact in artifacts:
        if artifact.replay_group is None and not artifact.path.startswith(
            "research/results/eh11_"
        ):
            raise ReleaseAssuranceError(
                f"only recorded EH-11 measurements may be hash-only: {artifact.path}"
            )
    if len(artifacts) != 12:
        raise ReleaseAssuranceError("manifest must pin all 12 checked-in evidence artifacts")

    return ReleaseManifest(
        suite_id=suite_id,
        supported_python=supported_python,
        pinned_dependencies=pinned_dependencies,
        claim_id=_text(closure.get("claim_id"), "manifest.closure.claim_id"),
        claim_statement_sha256=_sha(
            closure.get("claim_statement_sha256"),
            "manifest.closure.claim_statement_sha256",
        ),
        expected_publication_decision=_text(
            closure.get("expected_publication_decision"),
            "manifest.closure.expected_publication_decision",
        ),
        expected_blockers=expected_blockers,
        evidence=tuple(artifacts),
    )


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_output(arguments: Sequence[str], *, root: Path) -> str:
    command = ("git", *arguments)
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise ReleaseAssuranceError(
            f"clean-checkout attestation could not execute git: {error}"
        ) from error
    if completed.returncode != 0:
        diagnostic = completed.stderr.strip() or completed.stdout.strip()
        suffix = f": {diagnostic}" if diagnostic else ""
        raise ReleaseAssuranceError(
            "clean-checkout attestation failed while running "
            f"{' '.join(command)}{suffix}"
        )
    return completed.stdout.strip()


def _git_object_id(value: str, location: str) -> str:
    if len(value) not in {40, 64} or any(
        character not in _HEX_DIGITS for character in value
    ):
        raise ReleaseAssuranceError(
            f"clean-checkout {location} must be a lowercase Git object ID"
        )
    return value


def validate_clean_checkout(
    *,
    root: Path = ROOT,
    environment: Mapping[str, str] | None = None,
) -> CheckoutAttestation:
    """Fail unless ``root`` is the exact, clean Git checkout being validated."""

    active_environment = os.environ if environment is None else environment
    repository_root = Path(
        _git_output(("rev-parse", "--show-toplevel"), root=root)
    ).resolve()
    expected_root = root.resolve()
    if repository_root != expected_root:
        raise ReleaseAssuranceError(
            "clean-checkout repository root mismatch: "
            f"expected {expected_root}, got {repository_root}"
        )

    dirty = _git_output(
        ("status", "--porcelain=v1", "--untracked-files=all"),
        root=root,
    )
    if dirty:
        entries = tuple(line for line in dirty.splitlines() if line)
        preview = "; ".join(entries[:5])
        if len(entries) > 5:
            preview += f"; ... ({len(entries)} entries total)"
        raise ReleaseAssuranceError(
            f"clean-checkout worktree contains changes: {preview}"
        )

    commit = _git_object_id(
        _git_output(("rev-parse", "--verify", "HEAD^{commit}"), root=root),
        "commit",
    )
    tree = _git_object_id(
        _git_output(("rev-parse", "--verify", "HEAD^{tree}"), root=root),
        "tree",
    )

    if active_environment.get("GITHUB_ACTIONS") == "true":
        github_sha = active_environment.get("GITHUB_SHA")
        if not github_sha:
            raise ReleaseAssuranceError(
                "clean-checkout GitHub Actions attestation requires GITHUB_SHA"
            )
        if github_sha != commit:
            raise ReleaseAssuranceError(
                "clean-checkout GITHUB_SHA mismatch: "
                f"expected {github_sha}, got {commit}"
            )
        github_workspace = active_environment.get("GITHUB_WORKSPACE")
        if not github_workspace:
            raise ReleaseAssuranceError(
                "clean-checkout GitHub Actions attestation requires GITHUB_WORKSPACE"
            )
        if Path(github_workspace).resolve() != expected_root:
            raise ReleaseAssuranceError(
                "clean-checkout GITHUB_WORKSPACE mismatch: "
                f"expected {expected_root}, got {Path(github_workspace).resolve()}"
            )

    return CheckoutAttestation(commit=commit, tree=tree)


def validate_evidence_hashes(
    manifest: ReleaseManifest,
    *,
    root: Path = ROOT,
) -> None:
    """Require every checked-in evidence file to match its pinned byte digest."""

    result_directory = root / "research/results"
    checked_in = {
        path.relative_to(root).as_posix()
        for path in result_directory.iterdir()
        if path.is_file()
    }
    declared = {artifact.path for artifact in manifest.evidence}
    if checked_in != declared:
        raise ReleaseAssuranceError(
            "evidence inventory drift: "
            f"undeclared={sorted(checked_in - declared)}, "
            f"missing={sorted(declared - checked_in)}"
        )
    for artifact in manifest.evidence:
        path = root / artifact.path
        if not path.is_file():
            raise ReleaseAssuranceError(f"evidence file is missing: {artifact.path}")
        actual = _file_sha256(path)
        if actual != artifact.sha256:
            raise ReleaseAssuranceError(
                f"evidence SHA-256 drift for {artifact.path}: "
                f"expected {artifact.sha256}, got {actual}"
            )


def validate_environment(
    manifest: ReleaseManifest,
    *,
    pyproject: Path = DEFAULT_PYPROJECT,
    python_version: str | None = None,
    distribution_version: Callable[[str], str] = importlib.metadata.version,
) -> str:
    """Validate supported Python and the exact research dependency pins."""

    active_python = python_version or f"{sys.version_info.major}.{sys.version_info.minor}"
    if active_python not in manifest.supported_python:
        raise ReleaseAssuranceError(
            f"Python {active_python} is unsupported; expected one of "
            f"{', '.join(manifest.supported_python)}"
        )

    project = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    dev_dependencies = project.get("project", {}).get("optional-dependencies", {}).get(
        "dev", []
    )
    if not isinstance(dev_dependencies, list):
        raise ReleaseAssuranceError("pyproject project.optional-dependencies.dev is invalid")
    for name, expected in manifest.pinned_dependencies.items():
        declaration = f"{name}=={expected}"
        if declaration not in dev_dependencies:
            raise ReleaseAssuranceError(
                f"pyproject dev dependency must retain exact pin {declaration}"
            )
        try:
            actual = distribution_version(name)
        except importlib.metadata.PackageNotFoundError as error:
            raise ReleaseAssuranceError(f"required dependency is not installed: {name}") from error
        if actual != expected:
            raise ReleaseAssuranceError(
                f"installed {name} version must be {expected}, got {actual}"
            )
    return active_python


def validate_claim_boundary(
    manifest: ReleaseManifest,
    *,
    matrix_path: Path = DEFAULT_MATRIX,
    document: Path = DEFAULT_DOCUMENT,
    root: Path = ROOT,
) -> tuple[str, tuple[str, ...]]:
    """Validate closure structure plus the exact frozen claim and release state."""

    matrix = load_matrix(matrix_path)
    closure = validate_matrix(matrix, root=root, document=document)
    claim = _mapping(matrix.get("claim"), "claim")
    claim_id = _text(claim.get("id"), "claim.id")
    statement = _text(claim.get("statement"), "claim.statement")
    statement_digest = sha256(statement.encode()).hexdigest()
    if claim_id != manifest.claim_id:
        raise ReleaseAssuranceError(
            f"frozen claim ID drift: expected {manifest.claim_id}, got {claim_id}"
        )
    if statement_digest != manifest.claim_statement_sha256:
        raise ReleaseAssuranceError("frozen claim statement SHA-256 drift")
    if closure.publication_decision != manifest.expected_publication_decision:
        raise ReleaseAssuranceError(
            "publication decision drift: "
            f"expected {manifest.expected_publication_decision}, "
            f"got {closure.publication_decision}"
        )
    if closure.blockers != manifest.expected_blockers:
        raise ReleaseAssuranceError(
            f"closure blocker drift: expected {manifest.expected_blockers}, "
            f"got {closure.blockers}"
        )
    return closure.publication_decision, closure.blockers


def _default_runner(
    command: tuple[str, ...], cwd: Path, environment: Mapping[str, str] | None
) -> int:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=None if environment is None else dict(environment),
        check=False,
    )
    return completed.returncode


def _run_checked(
    label: str,
    command: Sequence[str],
    *,
    root: Path,
    runner: CommandRunner,
    environment: Mapping[str, str] | None = None,
) -> None:
    rendered = tuple(str(part) for part in command)
    print(f"[release-assurance] {label}: {' '.join(rendered)}", flush=True)
    return_code = runner(rendered, root, environment)
    if return_code != 0:
        raise ReleaseAssuranceError(
            f"{label} failed with exit code {return_code}: {' '.join(rendered)}"
        )


def _quality_commands(python: str, active_python: str) -> tuple[tuple[str, ...], ...]:
    return (
        (python, "-m", "ruff", "check", "src", "tests", "research"),
        (python, "-m", "mypy", "--python-version", active_python, "src"),
        (
            python,
            "-m",
            "pytest",
            "--cov=constraint_music",
            "--cov-report=term-missing",
        ),
    )


def _replay_evidence(
    manifest: ReleaseManifest,
    *,
    output_root: Path,
    root: Path,
    runner: CommandRunner,
) -> None:
    expected = {artifact.path: artifact for artifact in manifest.evidence}
    for group, (module, arguments, outputs) in _REPLAY_COMMANDS.items():
        directory = output_root / group
        directory.mkdir(parents=True, exist_ok=True)
        expanded = tuple(
            argument.replace("{directory}", str(directory)) for argument in arguments
        )
        _run_checked(
            f"replay {group}",
            (sys.executable, "-m", module, *expanded),
            root=root,
            runner=runner,
        )
        for repository_path in outputs:
            generated = directory / Path(repository_path).name
            if not generated.is_file():
                raise ReleaseAssuranceError(
                    f"{group} replay did not create {generated.name}"
                )
            actual = _file_sha256(generated)
            if actual != expected[repository_path].sha256:
                raise ReleaseAssuranceError(
                    f"replayed evidence drift for {repository_path}: "
                    f"expected {expected[repository_path].sha256}, got {actual}"
                )


_CHECKER_SCRIPT = r"""
import importlib.util
import sys

assert importlib.util.find_spec("ortools") is None, "OR-Tools leaked into checker-only environment"
from constraint_music.certification import verify_artifact
from constraint_music.delivery import verify_delivery
from constraint_music.provenance import load_result_json
assert callable(verify_artifact)
assert callable(verify_delivery)
assert callable(load_result_json)
assert "constraint_music.solver" not in sys.modules
print("checker-only wheel import: PASS")
"""


def _build_and_validate_checker(
    *,
    temporary_root: Path,
    root: Path,
    runner: CommandRunner,
) -> None:
    distribution_directory = temporary_root / "dist"
    _run_checked(
        "package build",
        (
            sys.executable,
            "-m",
            "build",
            "--outdir",
            str(distribution_directory),
        ),
        root=root,
        runner=runner,
    )
    wheels = tuple(distribution_directory.glob("*.whl"))
    source_distributions = tuple(distribution_directory.glob("*.tar.gz"))
    if len(wheels) != 1 or len(source_distributions) != 1:
        raise ReleaseAssuranceError(
            "package build must produce exactly one wheel and one source distribution"
        )

    checker_environment = temporary_root / "checker-only"
    _run_checked(
        "checker environment",
        (sys.executable, "-m", "venv", str(checker_environment)),
        root=root,
        runner=runner,
    )
    executable_directory = "Scripts" if os.name == "nt" else "bin"
    checker_python = checker_environment / executable_directory / (
        "python.exe" if os.name == "nt" else "python"
    )
    _run_checked(
        "checker-only install",
        (
            str(checker_python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            str(wheels[0]),
        ),
        root=root,
        runner=runner,
    )
    clean_environment = dict(os.environ)
    clean_environment.pop("PYTHONPATH", None)
    _run_checked(
        "checker-only isolation",
        (str(checker_python), "-c", _CHECKER_SCRIPT),
        root=temporary_root,
        runner=runner,
        environment=clean_environment,
    )


def run_release_assurance(
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    root: Path = ROOT,
    runner: CommandRunner = _default_runner,
) -> ReleaseSummary:
    """Run every release gate, stopping at the first failed invariant."""

    checkout = validate_clean_checkout(root=root)
    manifest = load_release_manifest(manifest_path)
    active_python = validate_environment(
        manifest,
        pyproject=root / "pyproject.toml",
    )
    publication_decision, blockers = validate_claim_boundary(
        manifest,
        matrix_path=root / "research/configs/eh12_closure_matrix.json",
        document=root / "docs/EH12_CLOSURE_MATRIX.md",
        root=root,
    )
    validate_evidence_hashes(manifest, root=root)

    for label, command in zip(
        ("lint", "static typing", "test and coverage"),
        _quality_commands(sys.executable, active_python),
        strict=True,
    ):
        _run_checked(label, command, root=root, runner=runner)

    with TemporaryDirectory(prefix="constraint-music-release-") as temporary:
        temporary_root = Path(temporary)
        _replay_evidence(
            manifest,
            output_root=temporary_root / "evidence",
            root=root,
            runner=runner,
        )
        _build_and_validate_checker(
            temporary_root=temporary_root,
            root=root,
            runner=runner,
        )

    validate_evidence_hashes(manifest, root=root)
    return ReleaseSummary(
        suite_id=manifest.suite_id,
        python_version=active_python,
        source_commit=checkout.commit,
        source_tree=checkout.tree,
        evidence_artifacts=len(manifest.evidence),
        replay_groups=len(_REPLAY_COMMANDS),
        publication_decision=publication_decision,
        blockers=blockers,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    try:
        summary = run_release_assurance(manifest_path=args.manifest)
    except (OSError, ValueError, ReleaseAssuranceError) as error:
        print(f"release assurance: FAIL: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": "PASS",
                "suite_id": summary.suite_id,
                "python_version": summary.python_version,
                "source_commit": summary.source_commit,
                "source_tree": summary.source_tree,
                "evidence_artifacts": summary.evidence_artifacts,
                "replay_groups": summary.replay_groups,
                "publication_decision": summary.publication_decision,
                "blockers": list(summary.blockers),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
