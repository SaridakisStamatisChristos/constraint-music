from __future__ import annotations

from .theory import PC_TO_SHARP_NAME, Key


def dominant_key(source: Key) -> Key:
    """Return the same-mode dominant key used by the bounded v2.8 contract."""
    return Key(PC_TO_SHARP_NAME[source.pitch_classes[4]], source.mode)


def common_tonic_pivot_destination_degree(source: Key, destination: Key) -> int:
    """Return the destination degree sharing the source-tonic triad, or raise."""
    source_pcs = set(source.triad_pitch_classes(0))
    matches = tuple(
        degree
        for degree in range(7)
        if set(destination.triad_pitch_classes(degree)) == source_pcs
    )
    if len(matches) != 1:
        raise ValueError(
            f"Expected one destination triad matching source tonic {source}; got {matches}"
        )
    return matches[0]
