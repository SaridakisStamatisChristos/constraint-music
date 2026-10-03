# Solver-Native SATB Harmony

Constraint Music v2.4 adds a beat-level four-part harmonic realization directly to the CP-SAT model. SATB is not a post-processing voicer: soprano, alto, tenor, and bass assignments must satisfy the hard contract before CP-SAT can return a feasible composition.

## Representation

- **Soprano** is an explicit beat-level solver variable and is constrained equal to the melody pitch at the beat's strong grid step.
- **Alto** is an independent solver variable in MIDI range **55..74**.
- **Tenor** is an independent solver variable in MIDI range **48..67**.
- **Bass** reuses the existing solver-native bass variable and its configured range.

The SATB layer is a harmonic skeleton at one sonority per beat. Melody subdivisions between strong steps remain part of the melodic/rhythmic layer.

## Hard rules

v2.4 extends the musical contract with six conditional rules:

- `CM027` — SATB shape and soprano anchoring.
- `CM028` — voice ranges and strict `bass < tenor < alto < soprano` ordering.
- `CM029` — soprano/alto and alto/tenor spacing is at most one octave.
- `CM030` — all four voices are chord members, all three triad pitch classes are present, and the active triad root is doubled.
- `CM031` — when parallel-perfect avoidance is enabled, every adjacent-beat voice pair involving alto or tenor avoids parallel perfect fifths and octaves.
- `CM032` — when leading-tone resolution is enabled, alto and tenor leading tones resolve upward by semitone.

The pre-v2.4 outer-voice rules remain active as separate contract items. SATB rules do not weaken or replace `CM001`–`CM026`.

## Chord policy

The v2.4 harmonic vocabulary remains diatonic triads. A SATB sonority therefore contains exactly three active triad pitch classes across four voices. The fourth voice implements an explicit **root-doubling** policy. Seventh chords, applied dominants, mixture, tonicization, and modulation remain later-roadmap work.

## Search semantics

`distinct_on=("harmony",)` now treats the inner-voice realization as part of harmony. A no-good cut therefore covers chord degrees plus alto and tenor assignments. Soprano is already anchored to melody and bass remains available as its own distinctness dimension.

## Independent verification

The SATB verifier receives only the finished serialized musical values. It recomputes the six SATB invariants without querying CP-SAT state. A solver assignment that violates any SATB contract rule raises the same fail-closed solver/verifier breach used by the existing tonal, rhythm, motif, and phrase layers.

Artifact schema `2.4` includes `soprano_midi`, `alto_midi`, and `tenor_midi` in the semantic composition digest, so SATB tampering is detectable offline.
