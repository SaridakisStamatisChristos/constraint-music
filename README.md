# Constraint Music

**Deterministic symbolic music synthesis with explicit hard constraints, CP-SAT optimization, and independent post-solve verification.**

Constraint Music treats composition as a verifiable constraint problem. A YAML specification is compiled into an OR-Tools CP-SAT model; the solver produces melody, rhythm, bass, and harmony; a separate application-level verifier rechecks the declared musical contract from ordinary serialized values; only verified results are exported.

> Current release: **2.1.0a1** — expressive rhythm and motif grammar on top of the verified v2 foundation.

## Pipeline

```text
YAML specification
      |
      v
pitch + harmony + rhythm + motif grammar
      |
      v
OR-Tools CP-SAT compiler
      |
      v
optimized assignment
      |
      v
independent 21-rule verifier
      |
      +----> MIDI with real ties/rests
      +----> JSON + contract/provenance digests
```

A solver status of `OPTIMAL` or `FEASIBLE` is not sufficient. A solver assignment rejected by the independent verifier fails closed.

## v2.1: explicit rhythm

Rhythm generation is optional and uses three states per melody grid step:

- `onset` — start a note;
- `tie` — sustain the previous sounding note at the same pitch;
- `rest` — emit silence.

The YAML can constrain exact per-bar ranges for onsets, rests, and ties, plus maximum consecutive rests/ties and bar-downbeat articulation.

```yaml
rhythm_enabled: true
min_onsets_per_bar: 5
max_onsets_per_bar: 6
min_rests_per_bar: 1
max_rests_per_bar: 2
min_ties_per_bar: 1
max_ties_per_bar: 1
max_consecutive_rests: 1
max_tie_steps: 1
require_bar_downbeat_onset: true
```

When `rhythm_enabled` is false, every melody grid position is an onset, preserving v2.0 behavior.

## v2.1: motif grammar

A motif can be declared between two bar locations:

```yaml
motif_relation: transpose       # none | repeat | transpose
motif_source_bar: 0
motif_target_bar: 2
motif_length_steps: 4
motif_transpose_semitones: 12
```

`repeat` copies pitch and rhythm exactly. `transpose` copies rhythm exactly and constrains each target pitch to `source + motif_transpose_semitones`. The independent verifier rechecks the same relationship from the finished artifact.

## Hard-constraint contract

v2.1 declares **21 stable hard-rule IDs**. `CM001`–`CM016` cover shape, tonal domains, chord membership, progression legality, leap/tritone rules, leading-tone resolution, repetition, leap recovery, outer-voice parallels, and authentic cadence. v2.1 adds:

| ID | Rule |
|---|---|
| CM017 | rhythm state domain |
| CM018 | tie/rest transition grammar and run limits |
| CM019 | per-bar rhythm density and downbeat structure |
| CM020 | motif repetition/transposition including rhythm |
| CM021 | cadential onset articulation |

See [Rhythm and Motifs](docs/RHYTHM_AND_MOTIFS.md) and [Verification](docs/VERIFICATION.md).

## Install

Python 3.11+:

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Generate

```bash
constraint-music generate examples/rhythm_motif.yaml \
  --output build/rhythm_motif.mid \
  --json build/rhythm_motif.json \
  --print-grid
```

Generate seeded alternatives:

```bash
constraint-music generate examples/rhythm_motif.yaml \
  --output build/variant.mid \
  --json build/variant.json \
  --count 4
```

## Verify without rerunning CP-SAT

```bash
constraint-music verify build/rhythm_motif.json
```

The command rechecks all 21 hard rules plus artifact schema, constraint-contract digest, semantic composition digest, and full artifact-content digest.

## Reproducibility

Use `workers: 1` with a fixed `seed` for deterministic regression work. Multi-worker CP-SAT search is intended for performance and should not be assumed to return an identical optimum on every platform/runtime combination.

## Quality gates

Every supported interpreter runs the same complete gate:

```bash
ruff check src tests
mypy --python-version <3.11|3.12|3.13> src
pytest --cov=constraint_music --cov-report=term-missing
python -m build
```

GitHub Actions requires all four gates independently on Python **3.11, 3.12, and 3.13**.

## Scope boundary

“Independent verification” means a code path separate from the CP-SAT model checks the serialized result against the declared contract without trusting solver state. It is not a formal proof of OR-Tools, Python, or the host machine.

See [Architecture](docs/ARCHITECTURE.md), [Verification](docs/VERIFICATION.md), [History](docs/HISTORY.md), and [Roadmap](docs/ROADMAP.md).
