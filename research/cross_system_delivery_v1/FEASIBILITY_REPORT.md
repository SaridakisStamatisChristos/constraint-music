# Adapted cross-system delivery feasibility

**Delivery gate: GO.** Native-profile gate remains HOLD.

| Pilot | Delivery profile | Shared delivery pass | Voice relation | Context |
| --- | --- | --- | --- | --- |
| constraint-music.C | native-certified-SATB | True | PASS | PASS |
| constraint-music.G | native-certified-SATB | True | PASS | PASS |
| music21.C | native-chorale | True | PASS | PASS |
| music21.G | native-chorale | True | PASS | PASS |
| diatony.C | diatony-plus-benchmark-renderer-v1 | True | PASS | PASS |
| diatony.G | diatony-plus-benchmark-renderer-v1 | True | PASS | PASS |

Two new Diatony generations retain explicit B/T/A/S capture rows, original native MIDI and logs alongside adapted MIDI. The benchmark renderer preserves all pitches and musical times; it declares four voice tracks/channels and adds request-supplied context. The independent byte parser and mido agree. Original Diatony delivery remains UNOBSERVABLE for voice identity and FAIL for context.

The shared request envelope is frozen in requests/C.json and requests/G.json. Existing Constraint Music/music21 inputs are mapped retrospectively. Fixed harmony, given voice and equal generator search spaces are not established. Additional native presets are disclosed in manifest.json. This supports the next development stage, not paired generation-rate or cost comparisons.

Held-out slots: 0. Full tonal obligations, a prospectively paired corpus, attack denominators and the larger benchmark remain pending. PR37 and the native feasibility archive are unchanged. No license or external research-run rights are changed.
