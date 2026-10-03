from constraint_music.models import GenerationSpec
from constraint_music.theory import Key, Mode, is_parallel_perfect, midi_note_name


def test_major_key_pitch_classes() -> None:
    assert Key("C", Mode.MAJOR).pitch_classes == (0, 2, 4, 5, 7, 9, 11)


def test_harmonic_minor_has_leading_tone() -> None:
    assert Key("D", Mode.MINOR).pitch_classes == (2, 4, 5, 7, 9, 10, 1)


def test_tension_interpolation_matches_beat_count() -> None:
    spec = GenerationSpec(bars=2, beats_per_bar=3, tension_curve=(0.0, 1.0))
    assert spec.expanded_tension() == (0, 20, 40, 60, 80, 100)


def test_note_name() -> None:
    assert midi_note_name(60) == "C4"


def test_parallel_fifth_detection() -> None:
    assert is_parallel_perfect(67, 48, 69, 50)
    assert not is_parallel_perfect(67, 48, 65, 50)
