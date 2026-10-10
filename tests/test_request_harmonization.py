from __future__ import annotations

import json
from dataclasses import replace
from io import BytesIO

import pytest
from mido import Message, MidiFile
from ortools.sat.python import cp_model
from research.paired_cross_system_v2.contract import KEYS, make_request
from research.paired_cross_system_v2.reference import candidates, edge

from constraint_music.errors import InternalVerificationError, NoSolutionError
from constraint_music.harmonization import (
    ChordRequest,
    HarmonizationRequest,
    HarmonizationResult,
    verify_harmonization,
)
from constraint_music.harmonization.midi import verify_midi, write_midi
from constraint_music.harmonization.solver import compile_request, harmonize


def seventh_request() -> HarmonizationRequest:
    return HarmonizationRequest(
        "C",
        (ChordRequest(4, seventh=True), ChordRequest(0)),
        ((77, 71, 62, 55), (76, 72, 67, 48)),
    )


def test_outer_seventh_and_nonroot_doubling_are_explicitly_supported():
    request = seventh_request()
    assert harmonize(request).rows == request.given_voices
    third_doubled = HarmonizationRequest("C", (ChordRequest(0),), ((76, 67, 64, 48),))
    assert harmonize(third_doubled).rows == third_doubled.given_voices


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("inversion", range(3))
def test_complete_single_chord_space_matches_independent_reference(key, inversion):
    raw = make_request("enumerated", key, [0], [inversion], [False], [None], 108)
    request = HarmonizationRequest(
        key, (ChordRequest(0, inversion),), ((None, None, None, raw["bass"][0]),)
    )
    model, rows = compile_request(request)

    class Collector(cp_model.CpSolverSolutionCallback):
        def __init__(self):
            super().__init__()
            self.rows = set()

        def on_solution_callback(self):
            self.rows.add(tuple(self.value(v) for v in rows[0]))

    collector = Collector()
    solver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = True
    solver.parameters.num_search_workers = 1
    assert solver.solve(model, collector) == cp_model.OPTIMAL
    assert collector.rows == set(candidates(raw, 0))
    assert all(not verify_harmonization(request, (row,)) for row in collector.rows)


def test_transition_compiler_matches_reference_on_adversarial_fixed_paths():
    # Sample fixed complete chords without cadential motion to expose each pair's
    # parallel interval and direction, including stationary and contrary motion.
    raw = make_request("edges", "C", [0, 3], [0, 0], [False, False], [None, None], 108)
    left_pool = candidates(raw, 0)
    right_pool = candidates(raw, 1)
    checked = {True: 0, False: 0}
    for left in left_pool:
        for right in right_pool:
            accepted = edge(raw, 0, left, right)
            if checked[accepted] >= 32:
                continue
            request = HarmonizationRequest("C", (ChordRequest(0), ChordRequest(3)), (left, right))
            assert (not verify_harmonization(request, (left, right))) == accepted
            if accepted:
                assert harmonize(request).rows == (left, right)
            else:
                with pytest.raises(NoSolutionError, match="INFEASIBLE"):
                    harmonize(request)
            checked[accepted] += 1
    assert checked == {True: 32, False: 32}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"key": "Am"},
        {"chords": ()},
        {"ranges": ((0, 128),) * 4},
        {"given_voices": ((True, None, None, None),)},
        {"given_voices": ((60,),)},
        {"tempo_bpm": True},
        {"max_upper_spacing": 0},
        {"chords": (ChordRequest(4, seventh=True),)},
    ],
)
def test_invalid_request_fails_closed(kwargs):
    payload = {"key": "C", "chords": (ChordRequest(0),)}
    payload.update(kwargs)
    with pytest.raises(ValueError):
        HarmonizationRequest(**payload)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"degree": True},
        {"degree": 7},
        {"degree": 0, "inversion": 3},
        {"degree": 0, "seventh": True},
        {"degree": 4, "seventh": 1},
    ],
)
def test_invalid_chord_fails_closed(kwargs):
    with pytest.raises(ValueError):
        ChordRequest(**kwargs)


@pytest.mark.parametrize("budget", [True, float("nan"), float("inf"), 0, -1])
def test_invalid_search_budget(budget):
    with pytest.raises(ValueError):
        harmonize(seventh_request(), max_time_seconds=budget)


def test_request_and_result_json_roundtrip_and_unknown_fields():
    result = harmonize(seventh_request())
    raw = json.loads(json.dumps(result.to_dict()))
    assert HarmonizationResult.from_dict(raw) == result
    with pytest.raises(ValueError):
        HarmonizationRequest.from_dict({**raw["request"], "repair": True})
    with pytest.raises(ValueError):
        HarmonizationResult.from_dict({**raw, "schema": "legacy"})


@pytest.mark.parametrize("rows", [(), ((True, 64, 55, 48),), ((60, 64, 55),), "bad"])
def test_malformed_score_rejected(rows):
    assert verify_harmonization(seventh_request(), rows)


def test_resolution_given_voice_range_and_inversion_corruption():
    request = seventh_request()
    for row, issue in [
        ((78, 71, 62, 55), "GIVEN_VOICE"),
        ((89, 71, 62, 55), "RANGE"),
        ((77, 71, 62, 59), "INVERSION"),
    ]:
        assert issue in verify_harmonization(request, (row, request.given_voices[1]))
    loose = replace(request, given_voices=())
    assert "SEVENTH_RESOLUTION" in verify_harmonization(loose, ((77, 71, 62, 55), (79, 72, 64, 48)))
    assert "LEADING_TONE" in verify_harmonization(loose, ((77, 71, 62, 55), (76, 67, 60, 48)))


def test_solver_independent_boundary_rejects_compiler_fault(monkeypatch):
    import constraint_music.harmonization.solver as module

    original = module.compile_request

    # Simulate a compiler resolving a different anchor obligation.
    def corrupt(request):
        return original(replace(request, given_voices=()))

    monkeypatch.setattr(module, "compile_request", corrupt)
    request = HarmonizationRequest(
        "C",
        (ChordRequest(0),),
        ((127, None, None, None),),
        ranges=((60, 127), (55, 74), (48, 67), (48, 59)),
    )
    with pytest.raises(InternalVerificationError):
        module.harmonize(request)


def mutate_midi(data, mutation):
    midi = MidiFile(file=BytesIO(data))
    mutation(midi)
    output = BytesIO()
    midi.save(file=output)
    return output.getvalue()


def test_native_midi_exact_delivery_and_corruptions(tmp_path):
    result = harmonize(seventh_request())
    path = write_midi(result, tmp_path / "harmonization.mid")
    data = path.read_bytes()
    assert not verify_midi(result.request, result.rows, data)
    changes = [
        lambda m: setattr(m.tracks[0][1], "tempo", 1000000),
        lambda m: setattr(m.tracks[0][3], "key", "G"),
        lambda m: setattr(m.tracks[1][2], "note", 78),
        lambda m: setattr(m.tracks[1][3], "time", 479),
        lambda m: setattr(m.tracks[1][2], "channel", 3),
        lambda m: m.tracks[1].insert(2, Message("control_change", control=64, value=127)),
        lambda m: setattr(m.tracks[1][0], "name", "Bass"),
    ]
    for change in changes:
        assert verify_midi(result.request, result.rows, mutate_midi(data, change))
    assert verify_midi(result.request, result.rows, b"not-midi")
    assert verify_midi(result.request, result.rows, data + b"ignored-trailer")
    assert verify_midi(result.request, result.rows, data[:-1])
    assert verify_midi(replace(result.request, tempo_bpm=120), result.rows, data)


def test_atomic_delivery_does_not_replace_existing_file_on_failed_check(tmp_path, monkeypatch):
    import constraint_music.harmonization.midi as module

    destination = tmp_path / "existing.mid"
    destination.write_bytes(b"existing")
    monkeypatch.setattr(module, "verify_midi", lambda *args: ("INJECTED_FAILURE",))
    with pytest.raises(ValueError, match="certification"):
        module.write_midi(harmonize(seventh_request()), destination)
    assert destination.read_bytes() == b"existing"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["existing.mid"]
