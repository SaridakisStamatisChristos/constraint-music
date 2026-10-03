# Constraint Music

**Deterministic symbolic music synthesis with explicit hard constraints, CP-SAT optimization, and independent post-solve verification.**

Constraint Music treats composition as a verifiable constraint problem. A YAML specification is compiled into an OR-Tools CP-SAT model; the solver produces melody, rhythm, bass, and harmony; a separate application-level verifier rechecks the declared musical contract from ordinary serialized values; only verified results are exported.

> Current release: **2.2.0a1** — explicit, independently verified phrase grammar on top of the rhythm/motif v2 foundation.

## Pipeline

```text
YAML specification
      |
      v
pitch + harmony + rhythm + motif + phrase grammar
      |
      v
OR-Tools CP-SAT compiler
      |
      v
optimized assignment
      |
      v
independent 26-rule verifier
      |
      +----> MIDI with real ties/rests
      +----> JSON + contract/provenance digests
```

A solver status of `OPTIMAL` or `FEASIBLE` is not sufficient. A solver assignment rejected by the independent verifier fails closed.

## v2.1: explicit rhythm and motifs

Rhythm generation is optional and uses three states per melody grid step:

- `onset` — start a note;
- `tie` — sustain the previous sounding note at the same pitch;
- `rest` — emit silence.

Motifs support exact repetition and exact semitone transposition with rhythm inheritance. When `rhythm_enabled` is false, every melody grid position is an onset, preserving v2.0 behavior.

## v2.2: phrase grammar

Phrases are explicit spans with roles, cadence semantics, and optional structural relations:

```yaml
phrases:
  - id: A
    start_bar: 0
    bars: 4
    role: antecedent
    cadence: dominant_open

  - id: B
    start_bar: 4
    bars: 4
    role: consequent
    cadence: dominant_to_tonic
    relation: answer
    source: A
    transpose_semitones: 7
    relation_steps: 4
```

Supported roles are `statement`, `antecedent`, `consequent`, `transition`, and `cadential`.

Supported relations are `independent`, `repeat`, `transpose`, `sequence`, and `answer`. Repeat/transposition operate over a complete equal-length phrase; answer reconstructs a declared opening fragment; sequence repeats a source fragment across the target with an explicit semitone step per copy.

Phrase-local cadence labels are precise symbolic contracts:

- `tonic_close`;
- `dominant_open`;
- `dominant_to_tonic`;
- `leading_tone_to_tonic`.

The older `require_authentic_cadence` field remains supported as a backward-compatible whole-piece closure rule.

See [Phrase Grammar](docs/PHRASE_GRAMMAR.md) for exact executable semantics.

## Hard-constraint contract

v2.2 declares **26 stable hard-rule IDs**. `CM001`–`CM021` retain the tonal, rhythmic, motif, and articulation contract. v2.2 adds:

| ID | Rule |
|---|---|
| CM022 | phrase spans are unique, in-bounds, and non-overlapping |
| CM023 | phrase-role opening/closing semantics |
| CM024 | exact repeat/transpose/answer/sequence reconstruction |
| CM025 | exact phrase-cadence semantics |
| CM026 | answer-linked antecedent/consequent open-to-strong structure |

See [Rhythm and Motifs](docs/RHYTHM_AND_MOTIFS.md), [Phrase Grammar](docs/PHRASE_GRAMMAR.md), and [Verification](docs/VERIFICATION.md).

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

Generate the phrase-grammar example:

```bash
constraint-music generate examples/eight_bar_period.yaml \
  --output build/eight_bar_period.mid \
  --json build/eight_bar_period.json \
  --print-grid
```

Generate seeded alternatives:

```bash
constraint-music generate examples/eight_bar_period.yaml \
  --output build/variant.mid \
  --json build/variant.json \
  --count 4
```

`--count` currently varies the seed; it does not yet guarantee unique solutions. Distinct no-good-cut enumeration is planned for v2.3.

## Verify without rerunning CP-SAT

```bash
constraint-music verify build/eight_bar_period.json
```

The command rechecks all 26 hard rules plus artifact schema, constraint-contract digest, semantic composition digest, and full artifact-content digest.

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

“Independent verification” means a code path separate from the CP-SAT model checks the serialized result against the declared contract without trusting solver state. It is not a formal proof of OR-Tools, Python, or the host machine. Constraint satisfaction demonstrates rule compliance; it does not prove aesthetic quality or historical-style authenticity.

See [Architecture](docs/ARCHITECTURE.md), [Verification](docs/VERIFICATION.md), [History](docs/HISTORY.md), and [Roadmap](docs/ROADMAP.md).
