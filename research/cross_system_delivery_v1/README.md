# Diatony plus benchmark renderer: development profile v1

This profile implements the second external **delivery path** using Diatony's
independent Gecode generator and a separately declared renderer. It keeps the
original `cross_system_assurance_v1/` archive and its native HOLD result intact.
It does not change generation code, PR37, or the repository's proprietary license.

## Contract and mapping

`requests/C.json` and `requests/G.json` freeze a minimal common envelope: four
explicit voices, major-key scale membership, contiguous sixteen-quarter duration,
quarter or whole notes, no crossing, and exact delivered pitch/time/voice plus
key/meter/tempo. No fixed harmony or given voice is requested. Unsupported request
fields or values fail; adapters never silently discard them.

Constraint Music and music21 use their previously captured native development
outputs, mapped retrospectively. Two **new** Diatony generations use the original
pinned executable and capture harness. Generation uses the declared I-IV-V-I
whole-note preset. All additional presets and context defaults appear in
`manifest.json`. These are different search spaces, so the profile does not
establish paired generation rates or comparable costs. The elementary oracle
does not check complete triads, parallels, or leading-tone resolution.

Diatony's public capture is four chord rows whose columns are bass, tenor, alto,
soprano. `renderer.py` writes SMF type 1: track 0 contains request-supplied context;
tracks 1..4/channels 0..3 carry soprano, alto, tenor, bass. Whole-note duration is
part of this pinned capture profile, not inferred from an arbitrary score. Pitches
are copied by explicit column identity; pitch sorting and voice reconstruction
from native MIDI are forbidden. PPQN scaling with exact rational times is the
declared timing equivalence. Velocity is 64, note-off velocity 0.

The checker independently reconstructs expected events from source rows and
requires agreement between the byte-level SMF parser and mido 1.3.3. It checks
native input projection and links each adapted file to the separately supplied
request. Original MIDI, score rows, normalized events, stdout/stderr, input and
request are retained with hashes beside each adapted MIDI. Native MIDI is never
overwritten. This does not certify the original exporter.

## Replay

```bash
python -m research.cross_system_delivery_v1.pilot --check
python -m pytest tests/test_cross_system_delivery.py
```

Checks require no solver, Gecode installation, or network access. CI checks both
the original native archive and this adapted archive. The runner refuses to
overwrite existing evidence. Before the initial collection, the manifest, requests,
renderer, checker and tests are committed locally; original local history is
retained in `research/history/cross_system_delivery_v1.bundle`. This is not an
externally timestamped preregistration or a held-out experiment.

For a fresh development version, use the build documented in the native study
and the pinned probe binary. The binary digest must match the original inspected
probe, and the collector requires mido 1.3.3:

```bash
python -m research.cross_system_delivery_v1.pilot --diatony-binary /path/to/diatony-probe
```

The command above is for an uncollected, separately versioned copy, not an
overwrite of this archive. A failed slot is retained with its logs/error and
prevents the adapted gate from passing. Execution/inspection of this repository
by outsiders still requires explicit owner permission; no research-use grant
is added by this profile.

## Next gate

A delivery GO establishes two external engine paths for this small development
envelope. The next study must prospectively bind the same requests, resolve
comparable generation obligations/budgets, implement and validate any additional
tonal oracle, then freeze held-out families, faults, and denominators before
collection. Zero held-out slots and no broader-paper completion are claimed here.
