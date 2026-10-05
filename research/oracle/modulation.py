"""Independent oracle for the bounded persistent-modulation contract."""

from __future__ import annotations

from dataclasses import dataclass

from .contextual_harmony import DiatonicKind, TonalMode, diatonic_pitch_classes

_SCALE_INTERVALS = {
    TonalMode.MAJOR: (0, 2, 4, 5, 7, 9, 11),
    TonalMode.MINOR: (0, 2, 3, 5, 7, 8, 11),
}


@dataclass(frozen=True, slots=True)
class OracleKey:
    tonic_pc: int
    mode: TonalMode

    def __post_init__(self) -> None:
        if not 0 <= self.tonic_pc <= 11:
            raise ValueError("tonic pitch class must be in 0..11")
        object.__setattr__(self, "mode", TonalMode(self.mode))

    @property
    def pitch_classes(self) -> tuple[int, ...]:
        return tuple(
            (self.tonic_pc + interval) % 12 for interval in _SCALE_INTERVALS[self.mode]
        )


@dataclass(frozen=True, slots=True)
class ModulationDecision:
    valid: bool
    reason: str
    expected_contexts: tuple[OracleKey, ...] = ()


def dominant_destination(source: OracleKey) -> OracleKey:
    return OracleKey(source.pitch_classes[4], source.mode)


def active_key_contexts(
    source: OracleKey,
    destination: OracleKey,
    *,
    boundary: int,
    total_beats: int,
) -> tuple[OracleKey, ...]:
    if total_beats < 4:
        raise ValueError("modulation requires at least four beats")
    if not 2 <= boundary <= total_beats - 2:
        raise ValueError("boundary must leave two beats in each structural region")
    return (source,) * boundary + (destination,) * (total_beats - boundary)


def adjudicate_modulation_plan(
    *,
    source: OracleKey,
    destination: OracleKey,
    boundary: int,
    total_beats: int,
    serialized_contexts: tuple[OracleKey, ...],
) -> ModulationDecision:
    expected_destination = dominant_destination(source)
    if total_beats < 4:
        return ModulationDecision(False, "modulation has fewer than four beats")
    if not 2 <= boundary <= total_beats - 2:
        return ModulationDecision(False, "boundary is outside the certified range")
    expected = active_key_contexts(
        source,
        expected_destination,
        boundary=boundary,
        total_beats=total_beats,
    )
    if destination != expected_destination:
        return ModulationDecision(False, "destination is not the same-mode dominant", expected)
    if len(serialized_contexts) != total_beats:
        return ModulationDecision(False, "key-context cardinality is not exact", expected)
    if serialized_contexts != expected:
        return ModulationDecision(False, "serialized contexts disagree with the boundary", expected)
    return ModulationDecision(True, "exact dominant destination and persistent contexts", expected)


def pivot_destination_degree(source: OracleKey, destination: OracleKey) -> int:
    source_tonic = set(
        diatonic_pitch_classes(
            source.tonic_pc,
            source.mode,
            0,
            DiatonicKind.TRIAD,
        )
    )
    matches = tuple(
        degree
        for degree in range(7)
        if set(
            diatonic_pitch_classes(
                destination.tonic_pc,
                destination.mode,
                degree,
                DiatonicKind.TRIAD,
            )
        )
        == source_tonic
    )
    if len(matches) != 1:
        raise ValueError(f"expected one destination pivot degree; got {matches}")
    return matches[0]


def adjudicate_common_tonic_pivot(
    voices: tuple[int, int, int, int],
    *,
    source: OracleKey,
    destination: OracleKey,
    structural_degree: int,
    kind: str | DiatonicKind,
    tonicization_target: int | None,
    modal_source: str | None,
) -> ModulationDecision:
    expected_destination = dominant_destination(source)
    if destination != expected_destination:
        return ModulationDecision(False, "pivot destination is not the dominant key")
    parsed_kind = kind if isinstance(kind, DiatonicKind) else DiatonicKind(kind)
    if structural_degree != 0:
        return ModulationDecision(False, "pivot is not source tonic")
    if parsed_kind is not DiatonicKind.TRIAD:
        return ModulationDecision(False, "pivot is not triadic")
    if tonicization_target is not None:
        return ModulationDecision(False, "pivot carries tonicization metadata")
    if modal_source is not None:
        return ModulationDecision(False, "pivot carries modal-source metadata")
    destination_degree = pivot_destination_degree(source, destination)
    if destination_degree != 3:
        return ModulationDecision(False, "source tonic does not reinterpret as destination IV")
    realized = {pitch % 12 for pitch in voices}
    source_tonic = set(
        diatonic_pitch_classes(source.tonic_pc, source.mode, 0, DiatonicKind.TRIAD)
    )
    destination_fourth = set(
        diatonic_pitch_classes(
            destination.tonic_pc,
            destination.mode,
            destination_degree,
            DiatonicKind.TRIAD,
        )
    )
    if realized != source_tonic or realized != destination_fourth:
        return ModulationDecision(False, "pivot realization is not the exact common triad")
    return ModulationDecision(True, "exact source-I and destination-IV common chord")


def adjudicate_destination_cadence(
    penultimate_voices: tuple[int, int, int, int],
    final_voices: tuple[int, int, int, int],
    *,
    destination: OracleKey,
    chord_degrees: tuple[int, int],
    key_contexts: tuple[OracleKey, OracleKey],
    tonicization_targets: tuple[int | None, int | None],
    modal_sources: tuple[str | None, str | None],
    final_is_onset: bool,
) -> ModulationDecision:
    expected_contexts = (destination, destination)
    if chord_degrees != (4, 0):
        return ModulationDecision(False, "destination cadence is not V-I", expected_contexts)
    if key_contexts != expected_contexts:
        return ModulationDecision(
            False, "destination cadence is outside destination context", expected_contexts
        )
    if any(target is not None for target in tonicization_targets):
        return ModulationDecision(
            False, "destination cadence carries tonicization metadata", expected_contexts
        )
    if any(source is not None for source in modal_sources):
        return ModulationDecision(
            False, "destination cadence carries modal-source metadata", expected_contexts
        )
    if not final_is_onset:
        return ModulationDecision(
            False, "destination tonic is not newly articulated", expected_contexts
        )
    if final_voices[0] % 12 != destination.tonic_pc:
        return ModulationDecision(
            False, "final soprano is not destination tonic", expected_contexts
        )
    if final_voices[3] % 12 != destination.tonic_pc:
        return ModulationDecision(False, "final bass is not destination tonic", expected_contexts)
    leading_tone = destination.pitch_classes[6]
    if all(pitch % 12 != leading_tone for pitch in penultimate_voices):
        return ModulationDecision(
            False, "destination dominant omits its leading tone", expected_contexts
        )
    for left, right in zip(penultimate_voices, final_voices, strict=True):
        if left % 12 == leading_tone and right != left + 1:
            return ModulationDecision(
                False, "destination leading tone does not rise by semitone", expected_contexts
            )
    return ModulationDecision(True, "exact destination V-I confirmation", expected_contexts)
