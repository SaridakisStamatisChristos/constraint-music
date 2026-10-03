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
    """Return the single parallel source admitted by the v2.7 mixture contract."""
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
