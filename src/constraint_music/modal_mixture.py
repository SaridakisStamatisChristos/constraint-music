from __future__ import annotations

from enum import IntEnum

from .theory import Key, Mode

NO_MODAL_SOURCE = 0


class ModalSource(IntEnum):
    PARALLEL_MAJOR = 1
    PARALLEL_NATURAL_MINOR = 2

    @classmethod
    def parse(cls, value: object) -> ModalSource:
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower().replace("-", "_")
            names = {
                "parallel_major": cls.PARALLEL_MAJOR,
                "major": cls.PARALLEL_MAJOR,
                "parallel_natural_minor": cls.PARALLEL_NATURAL_MINOR,
                "natural_minor": cls.PARALLEL_NATURAL_MINOR,
                "minor": cls.PARALLEL_NATURAL_MINOR,
            }
            if normalized in names:
                return names[normalized]
        if isinstance(value, int):
            try:
                return cls(value)
            except ValueError as exc:
                raise ValueError(f"Unknown modal source: {value!r}") from exc
        raise ValueError(f"Unknown modal source: {value!r}")

    @property
    def label(self) -> str:
        if self is ModalSource.PARALLEL_MAJOR:
            return "parallel_major"
        return "parallel_natural_minor"


_SOURCE_INTERVALS: dict[ModalSource, tuple[int, ...]] = {
    ModalSource.PARALLEL_MAJOR: (0, 2, 4, 5, 7, 9, 11),
    ModalSource.PARALLEL_NATURAL_MINOR: (0, 2, 3, 5, 7, 8, 10),
}

_SOURCE_ROMANS: dict[ModalSource, tuple[str, ...]] = {
    ModalSource.PARALLEL_MAJOR: ("I", "ii", "iii", "IV", "V", "vi", "vii°"),
    ModalSource.PARALLEL_NATURAL_MINOR: ("i", "ii°", "III", "iv", "v", "VI", "VII"),
}


def canonical_modal_source(key: Key) -> ModalSource:
    """Return the single parallel source admitted by the verified mixture contract."""
    if key.mode is Mode.MAJOR:
        return ModalSource.PARALLEL_NATURAL_MINOR
    return ModalSource.PARALLEL_MAJOR


def source_pitch_classes(key: Key, source: ModalSource) -> tuple[int, ...]:
    source = ModalSource.parse(source)
    return tuple((key.tonic_pc + interval) % 12 for interval in _SOURCE_INTERVALS[source])


def borrowed_triad_pitch_classes(
    key: Key,
    degree: int,
    source: ModalSource,
) -> tuple[int, int, int]:
    scale = source_pitch_classes(key, source)
    normalized = degree % 7
    return (
        scale[normalized],
        scale[(normalized + 2) % 7],
        scale[(normalized + 4) % 7],
    )


def borrowed_seventh_pitch_classes(
    key: Key,
    degree: int,
    source: ModalSource,
) -> tuple[int, int, int, int]:
    scale = source_pitch_classes(key, source)
    normalized = degree % 7
    return (
        scale[normalized],
        scale[(normalized + 2) % 7],
        scale[(normalized + 4) % 7],
        scale[(normalized + 6) % 7],
    )


def modal_source_leading_tone_pc(key: Key, source: ModalSource) -> int | None:
    """Return a true source leading tone, excluding natural-minor subtonic behavior."""
    source = ModalSource.parse(source)
    if source is ModalSource.PARALLEL_MAJOR:
        return (key.tonic_pc - 1) % 12
    return None


def supported_borrowed_degrees(key: Key) -> tuple[int, ...]:
    """Borrowed triads that remain realizable under the unchanged outer-voice contract."""
    source = canonical_modal_source(key)
    supported: list[int] = []
    for degree in range(7):
        borrowed = set(borrowed_triad_pitch_classes(key, degree, source))
        global_triad = set(key.triad_pitch_classes(degree))
        if borrowed == global_triad:
            continue
        # CM005/CM006 keep melody and bass in the global triadic core. At least one pitch
        # class must therefore be shared so both outer voices can remain contract-compatible.
        if borrowed & global_triad:
            supported.append(degree)
    return tuple(supported)


def supported_borrowed_seventh_degrees(key: Key) -> tuple[int, ...]:
    """Return the deliberately narrow v2.9 borrowed-seventh whitelist.

    A source-derived seventh is admitted only when:
    - it is genuinely different from the active-key seventh,
    - it is not functional degree V, whose source-null seventh identity retains the historical
      CM036 active-dominant semantics rather than being reinterpreted in v2.9,
    - its complete four-tone realization still leaves two distinct tones available to the
      unchanged CM005/CM006 outer-voice triadic core,
    - its chordal seventh matches the already-certified active-key seventh pitch class, so the
      existing solver-native down-step rule remains semantically symmetric,
    - a parallel-major source leading tone is not simultaneously the chordal seventh.
    """
    source = canonical_modal_source(key)
    source_leading = modal_source_leading_tone_pc(key, source)
    supported: list[int] = []
    for degree in range(7):
        if degree == 4:
            continue
        borrowed = borrowed_seventh_pitch_classes(key, degree, source)
        active_seventh = key.seventh_pitch_classes(degree)
        if set(borrowed) == set(active_seventh):
            continue
        if len(set(key.triad_pitch_classes(degree)) & set(borrowed)) < 2:
            continue
        if borrowed[3] != active_seventh[3]:
            continue
        if source_leading is not None and borrowed[3] == source_leading:
            continue
        supported.append(degree)
    return tuple(supported)


def borrowed_chord_name(
    key: Key,
    degree: int,
    source: ModalSource,
    inversion: int,
) -> str:
    source = ModalSource.parse(source)
    if source is not canonical_modal_source(key):
        raise ValueError(f"{source.label} is not the canonical parallel source for {key}")
    if degree not in supported_borrowed_degrees(key):
        raise ValueError(f"Unsupported borrowed degree {degree} for {key}")
    figures = ("", "6", "64")
    if not 0 <= inversion < len(figures):
        raise ValueError(f"Unsupported borrowed-triad inversion: {inversion}")
    roman = _SOURCE_ROMANS[source][degree]
    return f"{roman}{figures[inversion]}[{source.label}]"


def borrowed_seventh_chord_name(
    key: Key,
    degree: int,
    source: ModalSource,
    inversion: int,
) -> str:
    source = ModalSource.parse(source)
    if source is not canonical_modal_source(key):
        raise ValueError(f"{source.label} is not the canonical parallel source for {key}")
    if degree not in supported_borrowed_seventh_degrees(key):
        raise ValueError(f"Unsupported borrowed seventh degree {degree} for {key}")
    figures = ("7", "65", "43")
    if not 0 <= inversion < len(figures):
        raise ValueError(f"Unsupported borrowed-seventh inversion: {inversion}")
    roman = _SOURCE_ROMANS[source][degree]
    return f"{roman}{figures[inversion]}[{source.label}]"
