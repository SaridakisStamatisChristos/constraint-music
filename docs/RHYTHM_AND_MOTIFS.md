# Rhythm and Motif Grammar — v2.1

Constraint Music v2.1 promotes rhythm from an implicit fixed grid to an explicit verified structure.

## Rhythm states

Each melody grid step has exactly one state:

- `onset` — start a new note;
- `tie` — extend the immediately preceding sounding note and preserve its pitch;
- `rest` — emit no melody note for that grid step.

The solver and independent verifier both enforce the same rhythm grammar. A tie cannot follow a rest, tie/rest runs are bounded, and optional per-bar onset/rest/tie density constraints are exact hard constraints. `require_bar_downbeat_onset` can force the first grid position of every bar to articulate a note.

Rhythm generation is opt-in with `rhythm_enabled: true`. Existing v2.0-style configurations remain behaviorally compatible: when disabled, every melody step is an onset.

## Motif relations

`motif_relation` accepts:

- `none` — no motif relation;
- `repeat` — target motif copies source pitches and rhythm exactly;
- `transpose` — target motif copies source rhythm and shifts every source pitch by `motif_transpose_semitones`.

Motifs are addressed by source/target bar and a length in grid steps. The relation is compiled into CP-SAT equalities and independently rechecked from the serialized artifact as rule `CM020`.

## Verification contract additions

v2.1 adds five hard-rule IDs:

- `CM017` rhythm state domain;
- `CM018` rhythm transition/tie grammar;
- `CM019` per-bar rhythm density and downbeat structure;
- `CM020` motif pitch/rhythm relation;
- `CM021` cadential articulation.

JSON provenance is schema `2.1`; the semantic composition digest now commits to the rhythm sequence as well as pitches, bass, harmony, and tension.
