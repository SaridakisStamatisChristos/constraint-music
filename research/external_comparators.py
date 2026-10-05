"""Pinned, scope-normalized music21 comparator adapters for EH-10.

The adapters compare only explicitly shared predicates.  They do not compare
generation quality, complete compositions, provenance, request binding, MIDI
delivery, or the full Constraint Music rule contract.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Final

from constraint_music.theory import Key, Mode, is_parallel_perfect, midi_note_name

MUSIC21_VERSION: Final = "9.9.2"
VOICE_LEADING_ADAPTER: Final = "music21-voice-leading-v1"
TRIAD_ADAPTER: Final = "music21-c-major-triad-v1"


@dataclass(frozen=True, slots=True)
class ComparatorOutcome:
    case_id: str
    internal: bool
    external: bool


def _music21() -> tuple[Any, Any, Any, str]:
    try:
        import music21
        from music21 import chord, note, voiceLeading
    except ImportError as exc:  # pragma: no cover - exercised by checker-only install
        raise RuntimeError(
            "external comparator support requires `pip install .[comparators]`"
        ) from exc
    if music21.__version__ != MUSIC21_VERSION:
        raise RuntimeError(
            f"music21 comparator pin mismatch: expected {MUSIC21_VERSION}, "
            f"got {music21.__version__}"
        )
    return chord, note, voiceLeading, music21.__version__


def _note(note_module: Any, midi: int) -> Any:
    return note_module.Note(midi_note_name(midi))


def _normalized_upper(lower: Any, semitones: int) -> Any:
    octaves, remainder = divmod(semitones, 12)
    if remainder == 7:
        return lower.transpose(f"P{5 + 7 * octaves}")
    if remainder == 0 and semitones > 0:
        return lower.transpose(f"P{1 + 7 * octaves}")
    return lower.transpose(semitones)


def voice_leading_outcomes() -> list[ComparatorOutcome]:
    """Compare the exact shared parallel-perfect predicate on a bounded grid."""

    _, note, voice_leading, _ = _music21()
    outcomes: list[ComparatorOutcome] = []
    motions = (-3, -2, -1, 1, 2, 3)
    for lower_a in range(48, 60):
        for vertical_span in range(1, 25):
            upper_a = lower_a + vertical_span
            for upper_motion in motions:
                for lower_motion in motions:
                    upper_b = upper_a + upper_motion
                    lower_b = lower_a + lower_motion
                    if upper_b <= lower_b:
                        continue
                    internal = is_parallel_perfect(upper_a, lower_a, upper_b, lower_b)
                    lower_note_a = _note(note, lower_a)
                    lower_note_b = _note(note, lower_b)
                    # Normalize enharmonic spelling to the vertical chromatic span.
                    # music21 deliberately reasons about written interval quality,
                    # while Constraint Music's predicate is pitch-class based.
                    upper_note_a = _normalized_upper(lower_note_a, vertical_span)
                    upper_note_b = _normalized_upper(lower_note_b, upper_b - lower_b)
                    quartet = voice_leading.VoiceLeadingQuartet(
                        upper_note_a,
                        upper_note_b,
                        lower_note_a,
                        lower_note_b,
                    )
                    external = bool(
                        quartet.similarMotion()
                        and (quartet.parallelFifth() or quartet.parallelOctave())
                    )
                    case_id = f"vl.{upper_a}.{lower_a}.{upper_b}.{lower_b}"
                    outcomes.append(ComparatorOutcome(case_id, internal, external))
    return outcomes


def _at_or_above(pitch_class: int, minimum: int) -> int:
    return minimum + ((pitch_class - minimum) % 12)


def _voicing(pitch_classes: list[int], bass_pitch_class: int) -> tuple[int, ...]:
    remaining = list(pitch_classes)
    remaining.remove(bass_pitch_class)
    values = [_at_or_above(bass_pitch_class, 48)]
    for pitch_class in remaining:
        values.append(_at_or_above(pitch_class, values[-1] + 1))
    return tuple(values)


def _internal_triad_policy(
    notes: tuple[int, ...], triad: tuple[int, int, int], declared_inversion: int
) -> bool:
    pitch_classes = [value % 12 for value in notes]
    return (
        set(pitch_classes) == set(triad)
        and pitch_classes.count(triad[0]) >= 2
        and pitch_classes[0] == triad[declared_inversion]
    )


def _external_triad_policy(
    chord_module: Any,
    note_module: Any,
    notes: tuple[int, ...],
    triad: tuple[int, int, int],
    declared_inversion: int,
    expected_quality: str,
) -> bool:
    value = chord_module.Chord([_note(note_module, midi) for midi in notes])
    root = value.root()
    return bool(
        value.isTriad()
        and root is not None
        and root.pitchClass == triad[0]
        and value.quality == expected_quality
        and sum(pitch.pitchClass == triad[0] for pitch in value.pitches) >= 2
        and value.inversion() == declared_inversion
    )


def triad_outcomes() -> list[ComparatorOutcome]:
    """Compare the shared C-major diatonic triad/doubling/inversion policy."""

    chord, note, _, _ = _music21()
    key = Key("C", Mode.MAJOR)
    outcomes: list[ComparatorOutcome] = []
    for degree in range(7):
        triad = key.triad_pitch_classes(degree)
        expected_quality = key.triad_quality(degree)
        for inversion in range(3):
            bass_pc = triad[inversion]
            for doubled_index in range(3):
                pcs = [*triad, triad[doubled_index]]
                notes = _voicing(pcs, bass_pc)
                cases = {
                    f"triad.d{degree + 1}.i{inversion}.double{doubled_index}": (
                        notes,
                        inversion,
                    )
                }
                if doubled_index == 0:
                    missing = list(notes)
                    missing_pc = triad[1]
                    missing_index = next(
                        i for i, value in enumerate(missing) if value % 12 == missing_pc
                    )
                    missing[missing_index] = _at_or_above(triad[0], missing[0] + 1)
                    cases[f"triad.d{degree + 1}.i{inversion}.missing-third"] = (
                        tuple(sorted(missing)),
                        inversion,
                    )
                    foreign = list(notes)
                    fifth_index = next(
                        i for i, value in enumerate(foreign) if value % 12 == triad[2]
                    )
                    foreign[fifth_index] += 1
                    cases[f"triad.d{degree + 1}.i{inversion}.foreign-tone"] = (
                        tuple(sorted(foreign)),
                        inversion,
                    )
                    cases[f"triad.d{degree + 1}.i{inversion}.wrong-inversion"] = (
                        notes,
                        (inversion + 1) % 3,
                    )
                for case_id, (case_notes, declared_inversion) in cases.items():
                    outcomes.append(
                        ComparatorOutcome(
                            case_id,
                            _internal_triad_policy(case_notes, triad, declared_inversion),
                            _external_triad_policy(
                                chord,
                                note,
                                case_notes,
                                triad,
                                declared_inversion,
                                expected_quality,
                            ),
                        )
                    )
    return outcomes


def _summarize_adapter(
    adapter_id: str,
    scope: str,
    outcomes: list[ComparatorOutcome],
) -> dict[str, object]:
    disagreements = [outcome for outcome in outcomes if outcome.internal != outcome.external]
    pairs = Counter(
        f"internal_{str(outcome.internal).lower()}__external_{str(outcome.external).lower()}"
        for outcome in outcomes
    )
    return {
        "adapter_id": adapter_id,
        "scope": scope,
        "case_denominator": len(outcomes),
        "agreements": len(outcomes) - len(disagreements),
        "disagreements": len(disagreements),
        "agreement_rate": round((len(outcomes) - len(disagreements)) / len(outcomes), 6),
        "decision_pairs": dict(sorted(pairs.items())),
        "first_disagreements": [
            {
                "case_id": outcome.case_id,
                "internal": outcome.internal,
                "external": outcome.external,
            }
            for outcome in disagreements[:20]
        ],
    }


def run_external_comparators() -> dict[str, object]:
    """Execute all pinned adapters and return scope-normalized evidence."""

    _, _, _, observed_version = _music21()
    return {
        "schema_version": 1,
        "comparator": {
            "package": "music21",
            "required_version": MUSIC21_VERSION,
            "observed_version": observed_version,
            "source_tag": "v9.9.2",
            "release_commit": "aa9780a",
            "license": "BSD-3-Clause",
        },
        "claim_boundary": (
            "Predicate agreement on declared finite shared scopes only; this is not a "
            "whole-system quality, robustness, generation, or superiority comparison."
        ),
        "excluded_from_comparison": [
            "generation and objective quality",
            "complete SATB rule-contract coverage",
            "artifact shape and schema validation",
            "provenance and request binding",
            "certified MIDI delivery parse-back",
            "contextual harmony, rhythm, motifs, phrases, and modulation",
        ],
        "adapters": [
            _summarize_adapter(
                VOICE_LEADING_ADAPTER,
                "Two ordered voices; initial lower MIDI 48..59; initial vertical spans "
                "1..24; signed nonzero motions of 1..3 semitones (overall MIDI 45..86); "
                "ending order preserved; similar-motion parallel perfect fifths or "
                "octave-equivalent intervals.",
                voice_leading_outcomes(),
            ),
            _summarize_adapter(
                TRIAD_ADAPTER,
                "Four-note C-major diatonic triads only; degrees 1..7; declared "
                "inversions 0..2; exact chord-tone completeness, root doubling, and bass "
                "inversion; bounded doubling, missing-third, foreign-tone, and wrong-"
                "inversion cases.",
                triad_outcomes(),
            ),
        ],
    }
