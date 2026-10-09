"""Generate, replay and analyze preregistered multi-composition assurance evidence."""

from __future__ import annotations

import argparse
import json
import platform
import re
import statistics
import subprocess
import time
from collections import Counter, defaultdict
from dataclasses import replace
from hashlib import sha256
from importlib import metadata
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from constraint_music.artifact_validation import ArtifactShapeError
from constraint_music.certification import certify_delivery, verify_artifact
from constraint_music.contract import CONTRACT_VERSION, contract_digest
from constraint_music.delivery import verify_delivery
from constraint_music.errors import NoSolutionError
from constraint_music.midi import write_midi
from constraint_music.models import GenerationSpec
from constraint_music.provenance import artifact_payload, request_digest
from constraint_music.verifier import verify_result

from .multifixture_mutations import apply_mutation
from .oracle.delivery import adjudicate_delivery, project_context, project_melody, project_satb
from .oracle.rhythm_phrase import RhythmPolicy, adjudicate_rhythm

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "research/configs/multifixture_assurance_v1.json"
RESULTS = ROOT / "research/results/multifixture_assurance_v1"
PROTOCOL_COMMIT = "9823544"
CHANNELS = ("wire_shape", "semantic_rules", "integrity_request", "delivery_parseback")


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: object) -> str:
    return sha256(canonical(value).encode()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def implementation_hashes() -> dict[str, str]:
    paths = [
        *sorted((ROOT / "src").rglob("*.py")),
        *sorted((ROOT / "research/oracle").glob("*.py")),
        ROOT / "research/multifixture_mutations.py",
        ROOT / "research/multifixture_assurance.py",
    ]
    return {
        path.relative_to(ROOT).as_posix(): sha256(path.read_bytes()).hexdigest() for path in paths
    }


def load_manifest(path: Path = MANIFEST) -> dict[str, Any]:
    manifest = json.loads(path.read_text())
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("corpus_id") != "multifixture-assurance-v1":
        raise ValueError("wrong corpus identity")
    if manifest.get("schema_version") != 1 or manifest.get("artifact_schema") != "2.13":
        raise ValueError("wrong protocol/schema version")
    if (
        manifest.get("contract_version") != CONTRACT_VERSION
        or manifest.get("contract_sha256") != contract_digest()
    ):
        raise ValueError("contract pin drift")
    fixtures, mutations = manifest["fixtures"], manifest["mutations"]
    if len(fixtures) != manifest["planned_attempts"]:
        raise ValueError("planned attempt count mismatch")
    fixture_ids = [f["id"] for f in fixtures]
    mutation_ids = [m["id"] for m in mutations]
    if len(set(fixture_ids)) != len(fixtures) or len(set(mutation_ids)) != len(mutations):
        raise ValueError("duplicate fixture or mutation IDs")
    requests, seeds = [], []
    for fixture in fixtures:
        spec = GenerationSpec.from_mapping(fixture["spec"])
        if spec.workers != 1:
            raise ValueError("one worker required")
        if fixture["split"] not in {"development", "evaluation"}:
            raise ValueError("unknown fixture split")
        if fixture["profiles"] != ["certified-satb", "melody-plus-satb"]:
            raise ValueError("both certified profiles required")
        requests.append(request_digest(spec))
        seeds.append(spec.seed)
    if len(set(requests)) != len(fixtures) or len(set(seeds)) != len(fixtures):
        raise ValueError("fixture requests/seeds must be disjoint")
    clusters: dict[str, set[str]] = defaultdict(set)
    for definition in mutations:
        if definition["split"] not in {"development", "evaluation"}:
            raise ValueError("unknown mutation split")
        clusters[definition["split"]].add(definition["cluster"])
        if definition["expected_outcome"] not in {"REJECT", "BLOCKED"}:
            raise ValueError("invalid fault expectation")
    if clusters["development"] & clusters["evaluation"]:
        raise ValueError("mutation clusters cross splits")
    for split, target in manifest["fixture_targets"].items():
        if sum(f["split"] == split for f in fixtures) != target:
            raise ValueError("fixture target mismatch")
    controls = sum(len(f["profiles"]) for f in fixtures)
    attacks = sum(
        len(f["profiles"]) * sum(m["split"] == f["split"] for m in mutations) for f in fixtures
    )
    if controls != manifest["planned_controls"] or attacks != manifest["planned_mutation_slots"]:
        raise ValueError("planned slot count mismatch")


def _frozen_protocol(manifest: dict[str, Any]) -> dict[str, str]:
    path = MANIFEST.relative_to(ROOT).as_posix()
    frozen = json.loads(git("show", f"{PROTOCOL_COMMIT}:{path}"))
    if frozen != manifest:
        raise ValueError("manifest differs from preregistration commit")
    protocol_path = "docs/MULTIFIXTURE_ASSURANCE_PROTOCOL.md"
    if (ROOT / protocol_path).read_text().strip() != git(
        "show", f"{PROTOCOL_COMMIT}:{protocol_path}"
    ):
        raise ValueError("protocol document differs from preregistration commit")
    return {
        "protocol_commit": git("rev-parse", PROTOCOL_COMMIT),
        "manifest_sha256": sha256(MANIFEST.read_bytes()).hexdigest(),
        "protocol_sha256": sha256(
            (ROOT / "docs/MULTIFIXTURE_ASSURANCE_PROTOCOL.md").read_bytes()
        ).hexdigest(),
    }


def _versions() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        **{name: metadata.version(name) for name in ("ortools", "music21", "mido")},
    }


def _measure(function: Any, *args: Any, **kwargs: Any) -> tuple[Any, float]:
    start = time.perf_counter()
    result = function(*args, **kwargs)
    return result, time.perf_counter() - start


def _rss() -> int | None:
    path = Path("/proc/self/status")
    if not path.exists():
        return None
    match = re.search(r"^VmRSS:\s+(\d+)\s+kB", path.read_text(), re.MULTILINE)
    return int(match[1]) if match else None


def generate_candidates(directory: Path, split: str | None = None) -> None:
    """Attempt each fixed request exactly once and archive normalized generator output."""
    from constraint_music.solver import ConstraintMusicSolver

    manifest = load_manifest()
    protocol = _frozen_protocol(manifest)
    versions = _versions()
    for name, version in manifest["pinned_dependencies"].items():
        if versions[name] != version:
            raise ValueError(f"dependency pin mismatch: {name}")
    dirty = bool(git("status", "--porcelain", "--untracked-files=normal"))
    if dirty:
        raise ValueError("generation requires a clean committed checkout")
    directory.mkdir(parents=True, exist_ok=True)
    if (directory / "candidates.json").exists():
        raise ValueError("refusing to overwrite fixed candidate evidence; choose a new directory")
    source_hashes = implementation_hashes()
    attestation = {
        **protocol,
        "corpus_id": manifest["corpus_id"],
        "implementation_sha256": digest(source_hashes),
        "implementation_hashes": source_hashes,
        "git_commit": git("rev-parse", "HEAD"),
        "git_dirty": dirty,
        "runtime_versions": versions,
    }
    candidates, observations = [], []
    for fixture in manifest["fixtures"]:
        if split is not None and fixture["split"] != split:
            continue
        spec = GenerationSpec.from_mapping(fixture["spec"])
        record: dict[str, Any] = {
            "fixture_id": fixture["id"],
            "attempt_id": fixture["id"],
            "split": fixture["split"],
            "stratum": fixture["stratum"],
            "request_sha256": request_digest(spec),
            "seed": spec.seed,
            "outcome": "EXCEPTION",
            "solver_status": None,
            "issues": [],
            "excluded": False,
            "payload": None,
            "midi": {},
        }
        timings: dict[str, float] = {}
        started = time.perf_counter()
        try:
            result = ConstraintMusicSolver().generate(spec)
            timings["generation_seconds"] = time.perf_counter() - started
            timings["solver_seconds"] = result.wall_time_seconds
            record["solver_status"] = result.solver_status
            normalized = replace(result, wall_time_seconds=0.0)
            payload, timings["serialization_seconds"] = _measure(artifact_payload, normalized)
            report, timings["fresh_semantic_seconds"] = _measure(verify_result, normalized)
            strict, timings["artifact_certification_seconds"] = _measure(
                verify_artifact, payload, expected_spec=spec
            )
            record["payload"] = payload
            record["artifact_sha256"] = digest(payload)
            record["composition_sha256"] = payload["provenance"]["composition_sha256"]
            record["outcome"] = (
                "GENERATED" if report.valid and strict.accepted else "CONTROL_REJECTED"
            )
            record["issues"] = [*report.issues, *strict.integrity_issues]
            for profile in fixture["profiles"]:
                path = directory / "candidate.mid"
                _, timings[f"{profile}.export_seconds"] = _measure(
                    write_midi, normalized, path, profile=profile
                )
                record["midi"][profile] = path.read_bytes().hex()
                delivery, timings[f"{profile}.delivery_parseback_seconds"] = _measure(
                    verify_delivery, normalized, path, profile
                )
                full, timings[f"{profile}.full_delivery_certification_seconds"] = _measure(
                    certify_delivery, payload, path, expected_spec=spec, render_profile=profile
                )
                if not delivery.accepted or not full.accepted:
                    record["outcome"] = "CONTROL_REJECTED"
                    record["issues"].extend(delivery.issues)
                path.unlink()
        except NoSolutionError as exc:
            match = re.search(r"found \(([^)]+)\)", str(exc))
            status = match[1] if match else "UNRECOGNIZED"
            record.update(
                outcome=status if status in {"UNKNOWN", "INFEASIBLE"} else "OTHER_FAILURE",
                solver_status=status,
                issues=[str(exc)],
            )
        except Exception as exc:  # Evidence preserves exceptions; never calls them rejections.
            record.update(outcome="EXCEPTION", issues=[f"{type(exc).__name__}: {exc}"])
        timings.setdefault("generation_seconds", time.perf_counter() - started)
        observations.append(
            {
                "fixture_id": fixture["id"],
                "candidate_outcome": record["outcome"],
                "timings": timings,
                "process_local_rss_kib": _rss(),
            }
        )
        candidates.append(record)
        print(
            canonical(
                {
                    "fixture": fixture["id"],
                    "outcome": record["outcome"],
                    "solver": record["solver_status"],
                }
            ),
            flush=True,
        )
        # Reproducible checkpoints survive interruption; a partial corpus cannot pass replay.
        (directory / "candidates.json").write_text(
            json.dumps({"attestation": attestation, "candidates": candidates}, indent=2) + "\n"
        )
        (directory / "observations.json").write_text(
            json.dumps(
                {
                    "environment": {
                        "platform": platform.platform(),
                        "machine": platform.machine(),
                        "processor": platform.processor(),
                        "cpu_count": __import__("os").cpu_count(),
                        "runtime_versions": versions,
                        "source_commit": attestation["git_commit"],
                        "rss_method": "process-local Linux VmRSS samples; not peak RSS",
                    },
                    "fixtures": observations,
                },
                indent=2,
            )
            + "\n"
        )


def _oracle(payload: dict[str, Any], data: bytes, profile: str) -> dict[str, Any]:
    """Only independent rhythm CM017-19 and exact certified MIDI projection predicates."""
    music, spec = payload["music"], GenerationSpec.from_mapping(payload["spec"])
    events = list(
        project_satb(
            tuple(music["soprano_midi"]),
            tuple(music["alto_midi"]),
            tuple(music["tenor_midi"]),
            tuple(music["bass_midi"]),
        )
    )
    if profile == "melody-plus-satb":
        events.extend(
            project_melody(
                tuple(music["melody_midi"]),
                tuple(music["rhythm"]),
                subdivisions_per_beat=spec.subdivisions_per_beat,
                channel=4,
            )
        )

    def key_name(key: Any) -> str:
        display = key.tonic[0] + key.tonic[1:].replace("B", "b")
        return display if key.mode.value == "major" else display + "m"

    contexts = project_context(
        tempo_bpm=spec.tempo_bpm,
        beats_per_bar=spec.beats_per_bar,
        initial_key=key_name(spec.tonal_key),
        destination_key=key_name(spec.modulation_destination) if spec.modulation_enabled else None,
        modulation_boundary_beat=spec.modulation_boundary_beat,
    )
    decision = adjudicate_delivery(
        data,
        allowed_tracks=("Soprano", "Alto", "Tenor", "Bass")
        + (("Melody",) if profile == "melody-plus-satb" else ()),
        expected_events=tuple(sorted(events)),
        expected_context=contexts,
    )
    result: dict[str, Any] = {
        "delivery": {
            "accepted": decision.accepted,
            "issues": list(decision.issues),
            "domain": "certified SMF exact notes/context/tick division",
        }
    }
    if spec.rhythm_enabled:
        fields = RhythmPolicy.__dataclass_fields__
        values = {key: getattr(spec, key) for key in fields if hasattr(spec, key)}
        values.update(enabled=True, require_final_onset=spec.require_authentic_cadence)
        rhythm = adjudicate_rhythm(
            tuple(music["melody_midi"]), tuple(music["rhythm"]), policy=RhythmPolicy(**values)
        )
        result["rhythm"] = {
            "failed_rules": [r for r in rhythm.failed_rules if r in {"CM017", "CM018", "CM019"}],
            "issues": list(rhythm.reasons),
            "domain": "CM017-CM019 only",
        }
    else:
        result["rhythm"] = {"excluded": "rhythm disabled"}
    return result


def observe(
    payload: dict[str, Any], data: bytes, spec: GenerationSpec, profile: str, path: Path
) -> dict[str, Any]:
    signals = {
        channel: {"status": "BLOCKED", "detected": False, "issues": []} for channel in CHANNELS
    }
    try:
        path.write_bytes(data)
        report = certify_delivery(payload, path, expected_spec=spec, render_profile=profile)
        signals["wire_shape"]["status"] = "PASS"
        signals["semantic_rules"] = {
            "status": "PASS" if report.semantic.valid else "FAIL",
            "detected": not report.semantic.valid,
            "issues": list(report.semantic.issues),
        }
        signals["integrity_request"] = {
            "status": "FAIL" if report.integrity_issues else "PASS",
            "detected": bool(report.integrity_issues),
            "issues": list(report.integrity_issues),
        }
        assert report.delivery is not None
        signals["delivery_parseback"] = {
            "status": "PASS" if report.delivery.accepted else "FAIL",
            "detected": not report.delivery.accepted,
            "issues": list(report.delivery.issues),
        }
        outcome = "ACCEPT" if report.accepted else "REJECT"
        issues = [*report.semantic.issues, *report.integrity_issues, *report.delivery.issues]
    except ArtifactShapeError as exc:
        outcome, issues = "BLOCKED", list(exc.issues)
        signals["wire_shape"] = {"status": "FAIL", "detected": True, "issues": issues}
        oracle = {
            "delivery": {"excluded": "wire admission blocked"},
            "rhythm": {"excluded": "wire admission blocked"},
        }
    except Exception as exc:
        outcome, issues = "CRASH", [f"{type(exc).__name__}: {exc}"]
        oracle = {
            "delivery": {"excluded": "exception; requires adjudication"},
            "rhythm": {"excluded": "exception; requires adjudication"},
        }
    production_outcome = outcome
    if outcome in {"ACCEPT", "REJECT"}:
        try:
            oracle = _oracle(payload, data, profile)
            oracle["delivery"]["agreement"] = (
                oracle["delivery"]["accepted"] == report.delivery.accepted
            )
            if "excluded" not in oracle["rhythm"]:
                rules = sorted(set(report.semantic.failed_rules) & {"CM017", "CM018", "CM019"})
                oracle["rhythm"]["agreement"] = rules == sorted(oracle["rhythm"]["failed_rules"])
                oracle["rhythm"]["production_failed_rules"] = rules
        except Exception as exc:
            outcome = "HARNESS_ERROR"
            issues.append(f"oracle {type(exc).__name__}: {exc}")
            oracle = {
                "delivery": {"excluded": "oracle harness exception"},
                "rhythm": {"excluded": "oracle harness exception"},
            }
    detected_by = [channel for channel in CHANNELS if signals[channel]["detected"]]
    return {
        "outcome": outcome,
        "production_outcome": production_outcome,
        "issues": issues,
        "signals": signals,
        "detected_by": detected_by,
        "first_rejecting_boundary": detected_by[0]
        if detected_by and production_outcome != "CRASH"
        else None,
        "crashed": outcome == "CRASH",
        "oracle": oracle,
    }


def evaluate(directory: Path, split: str | None = None) -> list[dict[str, Any]]:
    manifest = load_manifest()
    versions = _versions()
    for name, version in manifest["pinned_dependencies"].items():
        if versions[name] != version:
            raise ValueError(f"replay dependency pin mismatch: {name}")
    archive = json.loads((directory / "candidates.json").read_text())
    attestation = archive["attestation"]
    if attestation["implementation_hashes"] != implementation_hashes():
        raise ValueError("implementation drift: rerun requires a versioned correction")
    if attestation["implementation_sha256"] != digest(implementation_hashes()):
        raise ValueError("invalid implementation digest")
    if any(attestation[key] != value for key, value in _frozen_protocol(manifest).items()):
        raise ValueError("protocol attestation drift")
    records = archive["candidates"]
    candidates = {c["fixture_id"]: c for c in records}
    fixtures = [f for f in manifest["fixtures"] if split is None or f["split"] == split]
    if len(candidates) != len(records) or set(candidates) != {f["id"] for f in fixtures}:
        raise ValueError("candidate accounting drift")
    rows: list[dict[str, Any]] = []
    row_attestation = {
        key: value for key, value in attestation.items() if key != "implementation_hashes"
    }
    with TemporaryDirectory() as temporary:
        path = Path(temporary) / "case.mid"
        for fixture in fixtures:
            candidate = candidates[fixture["id"]]
            spec = GenerationSpec.from_mapping(fixture["spec"])
            if candidate["request_sha256"] != request_digest(spec):
                raise ValueError("candidate does not bind frozen request")
            if (
                candidate["payload"] is not None
                and digest(candidate["payload"]) != candidate["artifact_sha256"]
            ):
                raise ValueError("candidate artifact hash drift")
            base = {
                **row_attestation,
                "fixture_id": fixture["id"],
                "attempt_id": fixture["id"],
                "split": fixture["split"],
                "stratum": fixture["stratum"],
                "request_sha256": request_digest(spec),
                "seed": spec.seed,
                "key": spec.key,
                "mode": spec.mode.value,
                "bars": spec.bars,
                "features": {
                    k: v
                    for k, v in fixture["spec"].items()
                    if k.endswith("_enabled") or k == "harmony_vocabulary"
                },
                "candidate_outcome": candidate["outcome"],
                "solver_status": candidate["solver_status"],
                "excluded": False,
            }
            rows.append(
                {
                    **base,
                    "kind": "attempt",
                    "case_id": f"{fixture['id']}.attempt",
                    "cluster_id": fixture["id"],
                    "outcome": candidate["outcome"],
                    "issues": candidate["issues"],
                    "expected_outcome": "GENERATED",
                    "artifact_sha256": candidate.get("artifact_sha256"),
                    "composition_sha256": candidate.get("composition_sha256"),
                }
            )
            definitions = [m for m in manifest["mutations"] if m["split"] == fixture["split"]]
            for profile in fixture["profiles"]:
                control_base = {
                    **base,
                    "kind": "control",
                    "profile": profile,
                    "case_id": f"{fixture['id']}.{profile}.control",
                    "cluster_id": fixture["id"],
                    "family": "control",
                    "tier": "control",
                    "expected_outcome": "ACCEPT",
                    "expected_class": "valid",
                    "artifact_sha256": candidate.get("artifact_sha256"),
                    "composition_sha256": candidate.get("composition_sha256"),
                }
                usable = candidate["outcome"] == "GENERATED"
                if usable:
                    payload = candidate["payload"]
                    data = bytes.fromhex(candidate["midi"][profile])
                    control = {
                        **control_base,
                        "midi_sha256": sha256(data).hexdigest(),
                        "applicability": "APPLIED",
                        **observe(payload, data, spec, profile, path),
                    }
                else:
                    control = {
                        **control_base,
                        "outcome": "GENERATION_FAILED",
                        "applicability": "GENERATION_FAILED",
                        "reason": f"candidate {candidate['outcome']}",
                        "issues": candidate["issues"],
                    }
                rows.append(control)
                usable = usable and control["outcome"] == "ACCEPT"
                for definition in definitions:
                    row = {
                        **base,
                        "kind": "attack",
                        "profile": profile,
                        "case_id": f"{fixture['id']}.{profile}.{definition['id']}",
                        "cluster_id": f"{fixture['id']}.{definition['cluster']}",
                        "mutation_id": definition["id"],
                        "mutation_cluster": definition["cluster"],
                        "mutation_definition": definition,
                        "family": definition["family"],
                        "tier": definition["tier"],
                        "expected_class": definition["expected_class"],
                        "expected_outcome": definition["expected_outcome"],
                    }
                    if not usable:
                        row.update(
                            outcome="GENERATION_FAILED",
                            applicability="GENERATION_FAILED",
                            reason=(
                                f"candidate {candidate['outcome']}; control {control['outcome']}"
                            ),
                            issues=control["issues"],
                        )
                    else:
                        try:
                            applied = apply_mutation(definition, payload, data, profile)
                        except Exception as exc:
                            row.update(
                                outcome="HARNESS_ERROR",
                                applicability="HARNESS_ERROR",
                                reason=f"{type(exc).__name__}: {exc}",
                                issues=[str(exc)],
                            )
                        else:
                            row.update(
                                applicability=applied.applicability,
                                reason=applied.reason,
                                witness=applied.witness,
                                artifact_sha256=digest(applied.payload),
                                midi_sha256=sha256(applied.midi).hexdigest(),
                                control_artifact_sha256=digest(payload),
                                control_midi_sha256=sha256(data).hexdigest(),
                                superficial_valid=applied.payload.get("validation", {}).get("valid")
                                if isinstance(applied.payload.get("validation"), dict)
                                else None,
                            )
                            if applied.applicability == "APPLIED":
                                row.update(
                                    observe(applied.payload, applied.midi, spec, profile, path)
                                )
                                row["adjudication"] = {
                                    "class": definition["expected_class"],
                                    "basis": definition["obligation"],
                                    "checker_used_for_label": False,
                                }
                            else:
                                row.update(outcome="NOT_APPLICABLE", issues=[])
                    rows.append(row)
    validate_rows(manifest, rows, split)
    return rows


def validate_rows(
    manifest: dict[str, Any], rows: list[dict[str, Any]], split: str | None = None
) -> None:
    fixtures = [f for f in manifest["fixtures"] if split is None or f["split"] == split]
    expected = {f"{f['id']}.attempt" for f in fixtures}
    for f in fixtures:
        for profile in f["profiles"]:
            expected.add(f"{f['id']}.{profile}.control")
            for m in manifest["mutations"]:
                if m["split"] == f["split"]:
                    expected.add(f"{f['id']}.{profile}.{m['id']}")
    if len(rows) != len(expected) or {r["case_id"] for r in rows} != expected:
        raise ValueError("missing, duplicate or unplanned raw rows")
    for row in rows:
        if row["excluded"]:
            raise ValueError("unplanned exclusion")
        if row["kind"] == "attack" and row["applicability"] == "APPLIED":
            if (
                row["artifact_sha256"] == row["control_artifact_sha256"]
                and row["midi_sha256"] == row["control_midi_sha256"]
            ):
                raise ValueError("no-op applicable mutation")
            if (
                row["family"] == "delivery"
                and row["artifact_sha256"] != row["control_artifact_sha256"]
            ):
                raise ValueError("delivery corruption changed artifact")


def wilson(successes: int, total: int) -> list[float] | None:
    if not total:
        return None
    z, p = 1.959963984540054, successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    radius = z * ((p * (1 - p) / total + z * z / (4 * total * total)) ** 0.5) / denominator
    return [round(max(0, center - radius), 6), round(min(1, center + radius), 6)]


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    attempts = [r for r in rows if r["kind"] == "attempt"]
    controls = [r for r in rows if r["kind"] == "control"]
    attacks = [r for r in rows if r["kind"] == "attack"]
    yield_rows, fault_rows, signal_rows, oracle_rows, uncertainty = [], [], [], [], []
    for split, stratum in sorted({(r["split"], r["stratum"]) for r in attempts}):
        subset = [r for r in attempts if (r["split"], r["stratum"]) == (split, stratum)]
        ids = {r["fixture_id"] for r in subset}
        subset_controls = [r for r in controls if r["fixture_id"] in ids]
        yield_rows.append(
            {
                "split": split,
                "stratum": stratum,
                "planned": len(subset),
                "excluded": sum(r["excluded"] for r in subset),
                "UNKNOWN": sum(r["outcome"] == "UNKNOWN" for r in subset),
                "INFEASIBLE": sum(r["outcome"] == "INFEASIBLE" for r in subset),
                "other_failure": sum(
                    r["outcome"] not in {"GENERATED", "UNKNOWN", "INFEASIBLE"} for r in subset
                ),
                "generated": sum(r["artifact_sha256"] is not None for r in subset),
                "strict_control_profiles_accepted": sum(
                    r["outcome"] == "ACCEPT" for r in subset_controls
                ),
                "strict_fixtures_accepted": sum(
                    all(
                        r["outcome"] == "ACCEPT"
                        for r in subset_controls
                        if r["fixture_id"] == fixture_id
                    )
                    for fixture_id in ids
                ),
            }
        )
    for split, family, tier in sorted({(r["split"], r["family"], r["tier"]) for r in attacks}):
        subset = [
            r for r in attacks if (r["split"], r["family"], r["tier"]) == (split, family, tier)
        ]
        counts = Counter(r["outcome"] for r in subset)
        fault_rows.append(
            {
                "split": split,
                "family": family,
                "tier": tier,
                "planned": len(subset),
                "applicable": sum(r["applicability"] == "APPLIED" for r in subset),
                **{
                    status: counts[status]
                    for status in (
                        "REJECT",
                        "BLOCKED",
                        "ACCEPT",
                        "CRASH",
                        "NOT_APPLICABLE",
                        "HARNESS_ERROR",
                        "GENERATION_FAILED",
                    )
                },
            }
        )
    for split in sorted({r["split"] for r in attempts}):
        applied = [r for r in attacks if r["split"] == split and r["applicability"] == "APPLIED"]
        ids = {r["fixture_id"] for r in applied}
        all_detected = sum(
            all(
                r["outcome"] in {"REJECT", "BLOCKED"}
                for r in applied
                if r["fixture_id"] == fixture_id
            )
            and not any(
                r["outcome"] == "HARNESS_ERROR" and r["fixture_id"] == fixture_id for r in attacks
            )
            for fixture_id in ids
        )
        uncertainty.append(
            {
                "split": split,
                "unit": "fixture with applicable attacks",
                "clusters": len(ids),
                "all_detected_clusters": all_detected,
                "fixture_family_clusters": len({r["cluster_id"] for r in applied}),
                "wilson_95": wilson(all_detected, len(ids)),
                "population_inference": False,
            }
        )
        for channel in CHANNELS:
            detected = sum(
                bool(set(r["detected_by"]) - {channel}) and r["outcome"] != "CRASH" for r in applied
            )
            signal_rows.append(
                {
                    "split": split,
                    "omitted": channel,
                    "applicable": len(applied),
                    "detected_without": detected,
                    "lost_or_undetected": len(applied) - detected,
                    "unique_catches": sum(r["detected_by"] == [channel] for r in applied),
                }
            )
        for predicate in ("delivery", "rhythm"):
            entries = [
                r.get("oracle", {}).get(predicate, {})
                for r in rows
                if r["split"] == split and r["kind"] != "attempt"
            ]
            compared = [e for e in entries if "agreement" in e]
            oracle_rows.append(
                {
                    "split": split,
                    "predicate": predicate,
                    "cases": len(compared),
                    "agreements": sum(e["agreement"] for e in compared),
                    "disagreements": sum(not e["agreement"] for e in compared),
                    "exclusions": len(entries) - len(compared),
                    "exclusion_reasons": dict(
                        sorted(
                            Counter(
                                e.get("excluded", "not executed: unavailable/inapplicable slot")
                                for e in entries
                                if "agreement" not in e
                            ).items()
                        )
                    ),
                }
            )
    findings = [
        r["case_id"] for r in controls if r["outcome"] not in {"ACCEPT", "GENERATION_FAILED"}
    ]
    findings += [
        r["case_id"]
        for r in attacks
        if r["outcome"] in {"ACCEPT", "CRASH", "HARNESS_ERROR"}
        or (r["applicability"] == "APPLIED" and r["outcome"] != r["expected_outcome"])
    ]
    findings += [
        r["case_id"]
        for r in rows
        if any(e.get("agreement") is False for e in r.get("oracle", {}).values())
    ]
    examples = {}
    for split in ("evaluation",):
        for name, predicate in (
            (
                "semantic",
                lambda r: (
                    r.get("superficial_valid") is True
                    and "semantic_rules" in r.get("detected_by", [])
                ),
            ),
            (
                "delivery",
                lambda r: (
                    r["family"] == "delivery"
                    and r.get("artifact_sha256") == r.get("control_artifact_sha256")
                    and r.get("detected_by") == ["delivery_parseback"]
                ),
            ),
        ):
            example = next(
                (
                    r
                    for r in attacks
                    if r["split"] == split and r["outcome"] == "REJECT" and predicate(r)
                ),
                None,
            )
            if example:
                examples[name] = {
                    key: example[key]
                    for key in (
                        "case_id",
                        "witness",
                        "issues",
                        "detected_by",
                        "first_rejecting_boundary",
                    )
                }
    return {
        "corpus_id": "multifixture-assurance-v1",
        "raw_sha256": digest(rows),
        "counts": {
            "attempts": len(attempts),
            "controls": len(controls),
            "attacks": len(attacks),
            "rows": len(rows),
        },
        "candidate_yield": yield_rows,
        "fault_results": fault_rows,
        "signals": signal_rows,
        "oracle_agreement": oracle_rows,
        "uncertainty": uncertainty,
        "findings": sorted(set(findings)),
        "examples": examples,
        "shortfalls": {
            split: max(
                0,
                target
                - sum(y["strict_fixtures_accepted"] for y in yield_rows if y["split"] == split),
            )
            for split, target in load_manifest()["fixture_targets"].items()
        },
        "nonclaims": [
            "population robustness",
            "aesthetic quality",
            "universal soundness",
            "global compiler/checker equivalence",
            "authenticated origin",
            "comparative superiority",
            "causal channel contributions",
            "novelty verdict",
        ],
    }


def cost_summary(directory: Path) -> dict[str, Any]:
    observations = json.loads((directory / "observations.json").read_text())
    fixtures = observations["fixtures"]
    stages: dict[str, list[float]] = defaultdict(list)
    for fixture in fixtures:
        if fixture["candidate_outcome"] == "GENERATED":
            for stage, value in fixture["timings"].items():
                stages[stage].append(value)
            generation = fixture["timings"]["generation_seconds"]
            for profile in ("certified-satb", "melody-plus-satb"):
                overhead = (
                    fixture["timings"]["artifact_certification_seconds"]
                    + fixture["timings"][f"{profile}.delivery_parseback_seconds"]
                )
                stages[f"{profile}.artifact_plus_parseback_over_generation"].append(
                    overhead / generation
                )

    def distribution(values: list[float]) -> dict[str, Any]:
        quartiles = (
            statistics.quantiles(values, n=4, method="inclusive")
            if len(values) > 1
            else [values[0]] * 3
        )
        return {
            "n": len(values),
            "median": statistics.median(values),
            "q1": quartiles[0],
            "q3": quartiles[2],
            "min": min(values),
            "max": max(values),
        }

    return {
        "environment": observations["environment"],
        "stages": {stage: distribution(values) for stage, values in sorted(stages.items())},
        "all_attempts": {
            "planned": len(fixtures),
            "total_generation_seconds": sum(f["timings"]["generation_seconds"] for f in fixtures),
            "outcomes": dict(sorted(Counter(f["candidate_outcome"] for f in fixtures).items())),
        },
        "rss_samples_kib": [f["process_local_rss_kib"] for f in fixtures],
    }


def write_evidence(
    directory: Path, split: str | None = None, check: bool = False
) -> dict[str, Any]:
    rows = evaluate(directory, split)
    summary = summarize(rows)
    outputs = {
        "raw.jsonl": "".join(canonical(row) + "\n" for row in rows),
        "summary.json": json.dumps(summary, indent=2, sort_keys=True) + "\n",
    }
    if check:
        for name, content in outputs.items():
            if (directory / name).read_text() != content:
                raise ValueError(f"deterministic evidence drift: {name}")
    else:
        for name, content in outputs.items():
            (directory / name).write_text(content)
        (directory / "cost_summary.json").write_text(
            json.dumps(cost_summary(directory), indent=2, sort_keys=True) + "\n"
        )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=RESULTS)
    parser.add_argument("--generate", action="store_true", help="fresh candidate yield/cost run")
    parser.add_argument("--split", choices=("development", "evaluation"))
    parser.add_argument(
        "--check", action="store_true", help="replay and assert archived outcome bytes"
    )
    args = parser.parse_args()
    if args.generate:
        if args.check:
            parser.error("--generate and --check are separate operations")
        generate_candidates(args.directory, args.split)
    summary = write_evidence(args.directory, args.split, args.check)
    print(
        canonical(
            {
                "counts": summary["counts"],
                "findings": summary["findings"],
                "shortfalls": summary["shortfalls"],
            }
        )
    )
    return 1 if summary["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
