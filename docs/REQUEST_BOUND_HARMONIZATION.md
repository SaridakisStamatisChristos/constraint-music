# Request-bound SATB harmonization

`constraint_music.harmonization` is an opt-in native API for satisfying explicit
major-key chord and voice obligations. The existing `ConstraintMusicSolver` is
the composition API with its established stronger musical style contract.

```python
from constraint_music.harmonization import ChordRequest, HarmonizationRequest
from constraint_music.harmonization.solver import harmonize
from constraint_music.harmonization.midi import write_midi

request = HarmonizationRequest(
    key="C",
    chords=(ChordRequest(4, seventh=True), ChordRequest(0)),
    given_voices=((77, 71, 62, 55), (76, 72, 67, 48)),  # S/A/T/B
)
result = harmonize(request, seed=7, max_time_seconds=20)
write_midi(result, "cadence.mid")
```

Generation needs the optional `[generation]` extra. Models, score verification
and MIDI verification/export work without OR-Tools. JSON requests/results use
`to_dict()`/`from_dict()`; loading a result never substitutes for verification.
Pass the independently trusted request to `verify_harmonization(request, rows)`
and `verify_midi(request, rows, bytes)`, rather than trusting an embedded request.

The request specifies 1..128 consecutive quarter chords, an eight-key major
profile, degree 0..6, root/first/second inversion, complete triads or dominant
sevenths followed by tonic, optional exact pitches in **any** voice, four pitch
ranges, upper spacing, tempo and meter. The model enforces complete chord
contents, requested inversion, strict S>A>T>B, spacing, anchors, no same-direction
parallel fifths/octaves between any pair, V-I leading-tone resolution in all
voices and downward stepwise seventh resolution. A nonroot tone may be doubled;
a seventh may appear in the soprano. No extra melody leap/recovery, tritone,
repetition, overlap, hidden-perfect or root-doubling rule is implied. Minor,
third inversions, non-dominant sevenths, rests, ties, modulation, motif and phrase
grammar are outside this API; use the established composition API where relevant.

The CP model uses small pitch-class chord tables and modular intervals plus
movement signs for parallel constraints. It does not enumerate reference paths
or import research code. A scalar checker independently reconstructs all chord,
voice and transition obligations before returning a solution. Native MIDI export
then checks the score again, writes a temporary five-track SMF, independently
parses notes/context back to the trusted request and atomically publishes only
on exact equality. Failure leaves an existing destination intact.

The result schema is `request-bound-satb-v1`. It does **not** assert legacy
CM001..CM057 composition certification, whose musical requirements differ.
First-feasible search offers no optimal musical-quality claim. NoSolutionError
distinguishes INFEASIBLE from UNKNOWN (budget exhausted without a proof).

The v2 results informed development; evaluation improvements on them are
development replay. Fresh prospective evidence is in
[`paired_cross_system_v3`](../research/paired_cross_system_v3/PROTOCOL.md).
