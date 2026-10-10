# Native cross-system feasibility report

**Decision: HOLD.** The corrected development pilot has 6 of 6 planned outputs. Only music21 qualifies for the inspected native delivery scope; the handoff requires two independent external candidates before the larger experiment.

| Pilot | Status | Shared symbolic issues | Parsed MIDI notes | Pitch/time relation (voice erased) | Native voice relation | Key/meter/tempo relation | Two parsers agree |
| --- | --- | --- | ---: | --- | --- | --- | --- |
| [constraint-music.C](native/constraint-music.C/input.json) | OUTPUT | none | 64 | PASS | PASS | PASS | True |
| [constraint-music.G](native/constraint-music.G/input.json) | OUTPUT | none | 64 | PASS | PASS | PASS | True |
| [music21.C](native/music21.C/input.json) | OUTPUT | none | 16 | PASS | PASS | PASS | True |
| [music21.G](native/music21.G/input.json) | OUTPUT | none | 16 | PASS | PASS | PASS | True |
| [diatony.C](native/diatony.C/input.json) | OUTPUT | none | 16 | PASS | UNOBSERVABLE | FAIL | True |
| [diatony.G](native/diatony.G/input.json) | OUTPUT | none | 16 | PASS | UNOBSERVABLE | FAIL | True |

The independent MIDI parsers agree on all six native files. The elementary symbolic checks pass for each returned score. These checks cover scale membership, duration, voice set and ordering only; they do not certify the full tonal contract.

## Traceable blocker

[Diatony C-major input](native/diatony.C/input.json), [native voice rows](native/diatony.C/score.txt), [original MIDI](native/diatony.C/delivered.mid) and [normalized events](native/diatony.C/normalized.json) form one linked witness. The four symbolic voices yield sixteen native MIDI notes, all on track 1/channel 0, with no key, meter or tempo events. Pitch/onset/duration multisets match when voice identity is erased. Voice identity is UNOBSERVABLE, and the explicit context relation fails. Sorting pitches into parts would add information absent from that delivery. The G-major witness has the same boundary limitation.

Music21 uses the supported chorale-style output setting, with separate native tracks for the four parts. Constraint Music uses its native certified-SATB profile. No candidate file was repaired by adding tracks or metadata.

## Comparability and limits

These are system-native development examples, not identical paired requests: music21/Diatony receive fixed I-IV-V-I while Constraint Music receives its own progression contract. Constraint Music's inspected public generation API does not accept that fixed progression or a given bass line. Unsupported is distinct from failed generation. A common request and eligibility matrix still need to be frozen after choosing a viable second external delivery path. Timing measurements are retained in observations.json but must not be ranked across these different tasks.

All six initial harness trials are retained separately in debug_attempts/v0; four contained harness errors, corrected before this pilot. A tuple-versus-JSON-array validation correction is documented in debug_attempts/serialization. Original collection rows/source are preserved; musical outcomes and native bytes are unchanged.

This gate concerns the pinned native interfaces, not all possible systems or adapters. Harmoniser is not counted as an independent Diatony voicing engine. No broader literature or musical-quality verdict follows. PR37 remains a separate bounded study, and PR38's contribution matrix remains applicable.

## Required next implementation

Use a second independently implemented generator with identity-preserving delivery, or explicitly declare a Diatony-plus-benchmark-renderer profile while retaining its native export as separate evidence. Freeze the shared request mapping, independent tonal oracle, development/holdout split, attacks and denominators only after that profile passes pilots. A renderer added by the benchmark evaluates an adapted pipeline; it cannot retroactively certify Diatony's original native exporter.

The larger held-out benchmark and paper expansion remain pending. Per the handoff's failed-gate instruction, the bounded PR37 manuscript can proceed now. Outside replay still requires an explicit research-run permission or separate evaluator license; this implementation changes neither the repository license nor third-party rights.
