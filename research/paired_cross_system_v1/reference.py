"""Independent matrix-based semantic reference; no oracle or adapter imports."""

from __future__ import annotations

from typing import Any


def valid(request: dict[str, Any], events: list[list[Any]]) -> bool:
    roots = {"C": 0, "G": 7, "D": 2, "A": 9, "E": 4, "F": 5, "Bb": 10, "Eb": 3}
    intervals = ((0, 4, 7), (0, 3, 7), (0, 3, 7), (0, 4, 7), (0, 4, 7), (0, 3, 7), (0, 3, 6))
    offsets = (0, 2, 4, 5, 7, 9, 11)
    voices = ("Soprano", "Alto", "Tenor", "Bass")
    try:
        tonic = roots[request["key"]]
        length = 4 * len(request["degrees"])
        grid: list[list[int | None]] = [[None] * length for _ in voices]
        for voice, pitch, onset, duration in events:
            if type(pitch) is not int or not 0 <= pitch <= 127:
                return False
            start, size = int(onset), int(duration)
            if str(start) != onset or str(size) != duration or size not in (1, 4):
                return False
            if start < 0 or start + size > length:
                return False
            column = voices.index(voice)
            for tick in range(start, start + size):
                if grid[column][tick] is not None:
                    return False
                grid[column][tick] = pitch
        frames: list[tuple[int, ...]] = []
        for tick in range(length):
            values = tuple(part[tick] for part in grid)
            if any(p is None for p in values):
                return False
            pitches = tuple(int(p) for p in values if p is not None)
            degree = request["degrees"][tick // 4]
            root = (tonic + offsets[degree]) % 12
            pcs = {(root + interval) % 12 for interval in intervals[degree]}
            if set(p % 12 for p in pitches) != pcs or pitches[-1] % 12 != root:
                return False
            if any(pitches[i] < pitches[i + 1] for i in range(3)):
                return False
            if tick % 4 == 0:
                frames.append(pitches)
            elif pitches != frames[-1]:
                return False
        for index in range(1, len(frames)):
            old, new = frames[index - 1], frames[index]
            for a in range(4):
                for b in range(a + 1, 4):
                    old_interval = abs(old[a] - old[b]) % 12
                    new_interval = abs(new[a] - new[b]) % 12
                    up = new[a] > old[a] and new[b] > old[b]
                    down = new[a] < old[a] and new[b] < old[b]
                    if old_interval in (0, 7) and old_interval == new_interval and (up or down):
                        return False
                if (
                    request["degrees"][index - 1 : index + 1] == [4, 0]
                    and old[a] % 12 == (tonic - 1) % 12
                    and new[a] - old[a] != 1
                ):
                    return False
        return True
    except (ValueError, TypeError, KeyError, IndexError):
        return False
