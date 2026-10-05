"""Reproducible bounded differential partitions for secondary sevenths.

The local partitions compare independently authored oracle decisions with the
exact production predicates used by the complete verifier. The final matrix is
smaller and explicitly systematic: it embeds every permitted quality/inversion
of vii7/V in a complete two-chord artifact, plus one register and one resolution
fault per form.
"""

from __future__ import annotations

from collections import Counter
from functools import cache
from hashlib import sha256
from itertools import permutations, product
from pathlib import Path

from constraint_music.models import GenerationSpec, RhythmState
from constraint_music.satb import SatbGenerationResult, satb_register_verification_issues
from constraint_music.secondary_leading_tone import (
    SecondaryLeadingToneSeventhQuality,
    secondary_leading_tone_seventh_support_degree,
)
from constraint_music.secondary_leading_tone_seventh_runtime import (
    secondary_seventh_context_verification_issues,
    secondary_seventh_resolution_verification_issues,
)
from constraint_music.theory import ChordKind
from constraint_music.verifier import verify_result

from .oracle.secondary_seventh import (
    SatbRegisterBounds,
    SeventhQuality,
    adjudicate_satb_register,
    adjudicate_secondary_seventh,
    adjudicate_secondary_seventh_context,
    adjudicate_target_triad,
    adjudicate_voice_resolutions,
    pitches_for_pitch_classes,
    secondary_seventh_pitch_classes,
)

_BOUNDS = SatbRegisterBounds()
_DELTAS = tuple(range(-2, 3))
_ROOT = Path(__file__).resolve().parents[1]


def _production_quality(
    quality: SeventhQuality,
) -> SecondaryLeadingToneSeventhQuality:
    return (
        SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED
        if quality is SeventhQuality.FULLY_DIMINISHED
        else SecondaryLeadingToneSeventhQuality.HALF_DIMINISHED
    )


def _first_disagreement(
    current: dict[str, object] | None,
    *,
    case: dict[str, object],
    oracle_valid: bool,
    production_valid: bool,
    oracle_reasons: tuple[str, ...],
    production_issues: tuple[tuple[str, str], ...],
) -> dict[str, object] | None:
    if current is not None or oracle_valid == production_valid:
        return current
    return {
        **case,
        "oracle_valid": oracle_valid,
        "production_valid": production_valid,
        "oracle_reasons": oracle_reasons,
        "production_issues": production_issues,
    }


@cache
def enumerate_absolute_register_domain() -> dict[str, object]:
    """Enumerate all exact seventh assignments inside the declared MIDI bounds."""

    generated = 0
    pruned_non_exact_role_assignment = 0
    visited = 0
    accepted = 0
    rejected = 0
    disagreements = 0
    first_disagreement: dict[str, object] | None = None

    for target_pitch_class in range(12):
        for quality in SeventhQuality:
            expected = secondary_seventh_pitch_classes(target_pitch_class, quality)
            soprano_domain = pitches_for_pitch_classes(*_BOUNDS.soprano, expected)
            alto_domain = pitches_for_pitch_classes(*_BOUNDS.alto, expected)
            tenor_domain = pitches_for_pitch_classes(*_BOUNDS.tenor, expected)
            for inversion in range(4):
                bass_domain = pitches_for_pitch_classes(
                    *_BOUNDS.bass,
                    (expected[inversion],),
                )
                for voices in product(
                    soprano_domain,
                    alto_domain,
                    tenor_domain,
                    bass_domain,
                ):
                    generated += 1
                    realized = tuple(note % 12 for note in voices)
                    if len(set(realized)) != 4 or set(realized) != set(expected):
                        pruned_non_exact_role_assignment += 1
                        continue
                    visited += 1
                    oracle = adjudicate_satb_register(voices, bounds=_BOUNDS)
                    production_issues = satb_register_verification_issues(
                        voices,
                        melody_low=_BOUNDS.soprano[0],
                        melody_high=_BOUNDS.soprano[1],
                    )
                    production_valid = not production_issues
                    accepted += int(oracle.valid)
                    rejected += int(not oracle.valid)
                    if oracle.valid != production_valid:
                        disagreements += 1
                    first_disagreement = _first_disagreement(
                        first_disagreement,
                        case={
                            "target_pitch_class": target_pitch_class,
                            "quality": quality.value,
                            "inversion": inversion,
                            "voices": voices,
                        },
                        oracle_valid=oracle.valid,
                        production_valid=production_valid,
                        oracle_reasons=oracle.reasons,
                        production_issues=production_issues,
                    )

    return {
        "domain": (
            "12 target pitch classes x 2 qualities x 4 inversions x every exact "
            "S/A/T/B octave placement in the closed bounds"
        ),
        "bounds": {
            "soprano": _BOUNDS.soprano,
            "alto": _BOUNDS.alto,
            "tenor": _BOUNDS.tenor,
            "bass": _BOUNDS.bass,
            "max_upper_spacing": _BOUNDS.max_upper_spacing,
        },
        "generated": generated,
        "pruned_non_exact_role_assignment": pruned_non_exact_role_assignment,
        "pruning_rationale": (
            "The pitch-class partition already classifies incomplete or doubled relations; "
            "this partition keeps only exact four-role realizations with the declared bass."
        ),
        "visited": visited,
        "accepted": accepted,
        "rejected": rejected,
        "disagreements": disagreements,
        "first_disagreement": first_disagreement,
    }


def _voice_assignments(
    expected: tuple[int, int, int, int],
    inversion: int,
) -> tuple[tuple[int, int, int, int], ...]:
    return tuple(
        assignment
        for assignment in permutations(expected)
        if assignment[3] == expected[inversion]
    )


@cache
def enumerate_voice_resolution_domain() -> dict[str, object]:
    """Enumerate all -2..+2 motions for every voice-role assignment."""

    visited = 0
    accepted = 0
    rejected = 0
    disagreements = 0
    first_disagreement: dict[str, object] | None = None

    for target_pitch_class in range(12):
        for target_is_major in (False, True):
            qualities = (
                (SeventhQuality.FULLY_DIMINISHED, SeventhQuality.HALF_DIMINISHED)
                if target_is_major
                else (SeventhQuality.FULLY_DIMINISHED,)
            )
            for quality in qualities:
                expected = secondary_seventh_pitch_classes(target_pitch_class, quality)
                production_quality = _production_quality(quality)
                for inversion in range(4):
                    for assignment in _voice_assignments(expected, inversion):
                        source = tuple(60 + pitch_class for pitch_class in assignment)
                        for deltas in product(_DELTAS, repeat=4):
                            destination = tuple(
                                note + delta
                                for note, delta in zip(source, deltas, strict=True)
                            )
                            visited += 1
                            oracle = adjudicate_voice_resolutions(
                                source,
                                destination,
                                target_pitch_class=target_pitch_class,
                                target_is_major=target_is_major,
                                quality=quality,
                            )
                            production_issues = (
                                secondary_seventh_resolution_verification_issues(
                                    source,
                                    destination,
                                    expected=expected,
                                    quality=production_quality,
                                    target_is_major=target_is_major,
                                )
                            )
                            production_valid = not production_issues
                            accepted += int(oracle.valid)
                            rejected += int(not oracle.valid)
                            if oracle.valid != production_valid:
                                disagreements += 1
                            first_disagreement = _first_disagreement(
                                first_disagreement,
                                case={
                                    "target_pitch_class": target_pitch_class,
                                    "target_is_major": target_is_major,
                                    "quality": quality.value,
                                    "inversion": inversion,
                                    "source": source,
                                    "deltas": deltas,
                                },
                                oracle_valid=oracle.valid,
                                production_valid=production_valid,
                                oracle_reasons=oracle.reasons,
                                production_issues=production_issues,
                            )

    return {
        "domain": (
            "12 target pitch classes x target quality policy (minor: fully diminished; "
            "major: fully/half diminished) x 4 inversions x 6 voice assignments x "
            "5^4 simultaneous voice motions"
        ),
        "motion_bounds_semitones": (_DELTAS[0], _DELTAS[-1]),
        "pruning_rationale": (
            "Source pitches are octave-normalized because the local tendency predicate depends "
            "only on source pitch class and signed melodic delta. Register and destination-triad "
            "membership are classified in separate partitions."
        ),
        "visited": visited,
        "accepted": accepted,
        "rejected": rejected,
        "disagreements": disagreements,
        "first_disagreement": first_disagreement,
    }


def _context_specs() -> tuple[tuple[str, GenerationSpec], ...]:
    specs: list[tuple[str, GenerationSpec]] = []
    for total_beats in range(2, 9):
        common = {
            "bars": 1,
            "beats_per_bar": total_beats,
            "subdivisions_per_beat": 1,
            "harmony_vocabulary": "triads+sevenths",
            "secondary_leading_tone_seventh_enabled": True,
        }
        specs.append(
            (
                "open_form",
                GenerationSpec(require_authentic_cadence=False, **common),
            )
        )
        specs.append(
            (
                "authentic_cadence",
                GenerationSpec(require_authentic_cadence=True, **common),
            )
        )
        if total_beats >= 4:
            for boundary in range(2, total_beats - 1):
                specs.append(
                    (
                        "modulation",
                        GenerationSpec(
                            require_authentic_cadence=False,
                            modulation_enabled=True,
                            modulation_destination_key="G",
                            modulation_boundary_beat=boundary,
                            **common,
                        ),
                    )
                )
    return tuple(specs)


@cache
def enumerate_context_anchor_domain() -> dict[str, object]:
    """Enumerate every declared placement/context bit over bounded form topologies."""

    visited = 0
    accepted = 0
    rejected = 0
    disagreements = 0
    first_disagreement: dict[str, object] | None = None
    categories: Counter[str] = Counter()

    for topology, spec in _context_specs():
        for beat in range(spec.total_beats):
            for target_supported, modal_overlap in product((False, True), repeat=2):
                boundary = (
                    spec.modulation_boundary_beat if spec.modulation_enabled else None
                )
                oracle = adjudicate_secondary_seventh_context(
                    beat=beat,
                    total_beats=spec.total_beats,
                    target_supported=target_supported,
                    modal_overlap=modal_overlap,
                    require_authentic_cadence=spec.require_authentic_cadence,
                    modulation_boundary_beat=boundary,
                )
                production_issues = secondary_seventh_context_verification_issues(
                    spec,
                    beat,
                    target=4,
                    supported_targets={4} if target_supported else set(),
                    modal_overlap=modal_overlap,
                )
                production_valid = not production_issues
                visited += 1
                accepted += int(oracle.valid)
                rejected += int(not oracle.valid)
                categories[f"{topology}:{'accept' if oracle.valid else 'reject'}"] += 1
                if oracle.valid != production_valid:
                    disagreements += 1
                first_disagreement = _first_disagreement(
                    first_disagreement,
                    case={
                        "topology": topology,
                        "total_beats": spec.total_beats,
                        "beat": beat,
                        "modulation_boundary_beat": boundary,
                        "target_supported": target_supported,
                        "modal_overlap": modal_overlap,
                    },
                    oracle_valid=oracle.valid,
                    production_valid=production_valid,
                    oracle_reasons=oracle.reasons,
                    production_issues=production_issues,
                )

    return {
        "domain": (
            "2..8 beats x open/authentic-cadence forms plus every valid single-modulation "
            "boundary x every beat x supported-target/modal-overlap truth table"
        ),
        "bounds": {
            "total_beats": (2, 8),
            "modulation_boundary": "every valid boundary in 2..total_beats-2",
        },
        "visited": visited,
        "accepted": accepted,
        "rejected": rejected,
        "categories": dict(sorted(categories.items())),
        "disagreements": disagreements,
        "first_disagreement": first_disagreement,
    }


def _complete_artifact(
    quality: SeventhQuality,
    inversion: int,
    fault: str,
) -> tuple[SatbGenerationResult, tuple[int, int, int, int], tuple[int, int, int, int]]:
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=2,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
        harmony_vocabulary="triads+sevenths",
        secondary_leading_tone_seventh_enabled=True,
        minimum_secondary_leading_tone_seventh_chords=1,
        avoid_parallel_perfects=False,
        resolve_leading_tone=False,
        bass_high=59,
        tension_curve=(0.8, 0.1),
    )
    production_quality = _production_quality(quality)
    target = 4
    support = secondary_leading_tone_seventh_support_degree(
        spec.tonal_key,
        target,
        spec.progression_graph,
        production_quality,
    )
    if quality is SeventhQuality.FULLY_DIMINISHED:
        source_by_inversion = {
            0: (69, 63, 60, 54),
            1: (66, 63, 60, 57),
            2: (69, 63, 54, 48),
            3: (69, 60, 54, 51),
        }
    else:
        source_by_inversion = {
            0: (69, 64, 60, 54),
            1: (66, 64, 60, 57),
            2: (69, 64, 54, 48),
            3: (69, 60, 54, 52),
        }
    source = source_by_inversion[inversion]
    expected = secondary_seventh_pitch_classes(7, quality)
    root, third, diminished_fifth, chordal_seventh = expected
    destination_values: list[int] = []
    for note in source:
        if note % 12 == root:
            destination_values.append(note + 1)
        elif note % 12 == diminished_fifth:
            destination_values.append(note - 1)
        elif note % 12 == chordal_seventh:
            destination_values.append(
                note - (1 if quality is SeventhQuality.FULLY_DIMINISHED else 2)
            )
        elif note % 12 == third:
            destination_values.append(note - 2)
        else:  # pragma: no cover - static template invariant
            raise AssertionError("Unexpected secondary-seventh template tone")
    destination = tuple(destination_values)
    target_triad = spec.tonal_key.triad_pitch_classes(target)
    destination_inversion = target_triad.index(destination[3] % 12)

    if fault == "register":
        source = (source[0] + 24, *source[1:])
        destination = (destination[0] + 24, *destination[1:])
    elif fault == "resolution":
        root_voice = next(index for index, note in enumerate(source) if note % 12 == root)
        changed = list(destination)
        changed[root_voice] = source[root_voice] + 2
        destination = tuple(changed)
    elif fault != "none":  # pragma: no cover - internal caller invariant
        raise ValueError(f"Unknown fault: {fault}")

    soprano = (source[0], destination[0])
    alto = (source[1], destination[1])
    tenor = (source[2], destination[2])
    bass = (source[3], destination[3])
    result = SatbGenerationResult(
        spec=spec,
        melody=soprano,
        bass=bass,
        chord_degrees=(support, target),
        target_tension=(80, 10),
        actual_tension=(80, 10),
        objective_value=0.0,
        solver_status="BOUNDED-CONFORMANCE",
        wall_time_seconds=0.0,
        rhythm=(RhythmState.ONSET, RhythmState.ONSET),
        soprano=soprano,
        alto=alto,
        tenor=tenor,
        chord_kinds=(ChordKind.SEVENTH, ChordKind.TRIAD),
        chord_inversions=(inversion, destination_inversion),
        tonicization_targets=(target, None),
        modal_sources=(None, None),
    )
    return result, source, destination


@cache
def evaluate_complete_verifier_matrix() -> dict[str, object]:
    """Run the systematic full-artifact control/fault matrix."""

    visited = 0
    disagreements = 0
    first_disagreement: dict[str, object] | None = None
    categories: Counter[str] = Counter()
    full_bounds = SatbRegisterBounds(bass=(36, 59))

    for quality in SeventhQuality:
        for inversion in range(4):
            for fault in ("none", "register", "resolution"):
                result, source, destination = _complete_artifact(quality, inversion, fault)
                pitch_class = adjudicate_secondary_seventh(
                    source,
                    target_pitch_class=7,
                    quality=quality,
                    inversion=inversion,
                    half_diminished_eligible=True,
                )
                source_register = adjudicate_satb_register(source, bounds=full_bounds)
                destination_register = adjudicate_satb_register(
                    destination,
                    bounds=full_bounds,
                )
                resolution = adjudicate_voice_resolutions(
                    source,
                    destination,
                    target_pitch_class=7,
                    target_is_major=True,
                    quality=quality,
                )
                target_triad = adjudicate_target_triad(
                    destination,
                    target_pitch_class=7,
                    target_is_major=True,
                )
                oracle_valid = all(
                    (
                        pitch_class.valid,
                        source_register.valid,
                        destination_register.valid,
                        resolution.valid,
                        target_triad.valid,
                    )
                )
                report = verify_result(result)
                production_valid = report.valid
                visited += 1
                categories[f"{fault}:oracle_{'accept' if oracle_valid else 'reject'}"] += 1
                categories[
                    f"{fault}:verifier_{'accept' if production_valid else 'reject'}"
                ] += 1
                if oracle_valid != production_valid:
                    disagreements += 1
                    if first_disagreement is None:
                        first_disagreement = {
                            "quality": quality.value,
                            "inversion": inversion,
                            "fault": fault,
                            "oracle_valid": oracle_valid,
                            "production_valid": production_valid,
                            "production_issues": report.issues,
                        }

    return {
        "domain": (
            "systematic complete-verifier matrix: 2 qualities x 4 inversions x "
            "valid/register-fault/resolution-fault"
        ),
        "scope": (
            "C major vii7/V -> V two-beat artifacts; this matrix is systematic, not an "
            "exhaustive full-composition claim"
        ),
        "visited": visited,
        "categories": dict(sorted(categories.items())),
        "disagreements": disagreements,
        "first_disagreement": first_disagreement,
    }


def _source_hash(relative_path: str) -> str:
    return sha256((_ROOT / relative_path).read_bytes()).hexdigest()


def bounded_conformance_report() -> dict[str, object]:
    return {
        "schema_version": 2,
        "claim_boundary": (
            "Agreement is limited to the declared finite partitions and systematic matrix; "
            "it is not global solver/checker equivalence."
        ),
        "implementation_hashes": {
            path: _source_hash(path)
            for path in (
                "research/oracle/secondary_seventh.py",
                "research/differential_check.py",
                "src/constraint_music/satb.py",
                "src/constraint_music/secondary_leading_tone_seventh_runtime.py",
            )
        },
        "partitions": {
            "absolute_register": enumerate_absolute_register_domain(),
            "context_anchor": enumerate_context_anchor_domain(),
            "voice_resolution": enumerate_voice_resolution_domain(),
            "complete_verifier": evaluate_complete_verifier_matrix(),
        },
    }
