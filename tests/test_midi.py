from mido import MidiFile

from constraint_music.midi import write_midi
from constraint_music.models import GenerationSpec
from constraint_music.solver import ConstraintMusicSolver


def test_midi_export_has_conductor_and_four_certified_voice_tracks(tmp_path) -> None:
    spec = GenerationSpec(
        bars=2,
        subdivisions_per_beat=1,
        max_time_seconds=10,
        workers=2,
        tension_curve=(0.0, 0.8, 0.0),
    )
    result = ConstraintMusicSolver().generate(spec)
    path = write_midi(result, tmp_path / "piece.mid")
    parsed = MidiFile(path)
    assert len(parsed.tracks) == 5
    assert {track.name for track in parsed.tracks[1:]} == {
        "Soprano",
        "Alto",
        "Tenor",
        "Bass",
    }
    assert path.stat().st_size > 100
