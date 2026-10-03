# Constraint Music

**Deterministic symbolic music synthesis with explicit hard constraints, CP-SAT optimization, and independent post-solve verification.**

Constraint Music treats composition as a verifiable constraint problem. A YAML specification is compiled into an OR-Tools CP-SAT model; the solver produces melody, rhythm, bass, and harmony; a separate application-level verifier rechecks the declared musical contract from ordinary serialized values; only verified results are exported.

> Current release: **2.3.0a1** — guaranteed distinct enumeration and independently auditable multi-objective search on top of the verified phrase-grammar foundation.

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
weighted solve / no-good enumeration / Pareto candidate search
      |
      v
independent 26-rule verifier + objective-vector recomputation
      |
      +----> MIDI with real ties/rests
      +----> JSON + contract/provenance/search digests
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

Phrase-local cadence labels are precise symbolic contracts: `tonic_close`, `dominant_open`, `dominant_to_tonic`, and `leading_tone_to_tonic`.

See [Phrase Grammar](docs/PHRASE_GRAMMAR.md) for exact executable semantics.

## v2.3: distinct enumeration and Pareto search

`--count` now produces genuinely distinct alternatives. After each accepted composition, CP-SAT receives a no-good cut over the selected dimensions:

```bash
constraint-music generate examples/eight_bar_period.yaml \
  --count 4 \
  --distinct-on melody,harmony \
  --output build/variant.mid \
  --json build/variant.json
```

Supported distinctness dimensions are `melody`, `rhythm`, `bass`, and `harmony`.

The objective is also exposed as five minimized components:

- `tension_deviation`
- `melody_motion`
- `bass_motion`
- `harmonic_repetition`
- `contour_mismatch`

The solver computes these components internally, then Constraint Music independently reconstructs the same vector from the finished musical values. A disagreement fails closed.

Pareto mode explores deterministic weighted scalarizations, guarantees distinct candidates through no-good cuts, and filters dominated candidates from the explored pool:

```bash
constraint-music generate examples/eight_bar_period.yaml \
  --pareto \
  --count 4 \
  --pareto-candidate-multiplier 3 \
  --distinct-on melody,harmony \
  --output build/pareto.mid \
  --json build/pareto.json
```

This is a bounded Pareto-front approximation, not a proof that the complete feasible Pareto frontier has been enumerated. See [Distinct Enumeration and Pareto Search](docs/ENUMERATION_AND_PARETO.md).

## Hard-constraint contract

v2.3 keeps the **26 stable hard-rule IDs** from v2.2. `CM001`–`CM021` cover tonal, rhythmic, motif, and articulation rules; `CM022`–`CM026` cover phrase spans, roles, relations, cadences, and antecedent/consequent structure.

No new hard rule is introduced for search strategy. Feasibility certification remains separate from ranking and enumeration.

See [Rhythm and Motifs](docs/RHYTHM_AND_MOTIFS.md), [Phrase Grammar](docs/PHRASE_GRAMMAR.md), [Distinct Enumeration and Pareto Search](docs/ENUMERATION_AND_PARETO.md), and [Verification](docs/VERIFICATION.md).

## Install

Python 3.11+:

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Generate one verified composition

```bash
constraint-music generate examples/eight_bar_period.yaml \
  --output build/eight_bar_period.mid \
  --json build/eight_bar_period.json \
  --print-grid
```

## Verify without rerunning CP-SAT

```bash
constraint-music verify build/eight_bar_period.json
```

The command rechecks all 26 hard rules, artifact schema, constraint-contract digest, semantic composition digest, full artifact-content digest, and v2.3 objective-vector metadata.

## Reproducibility

Use `workers: 1` with a fixed `seed` for deterministic regression work and deterministic enumeration order. Multi-worker CP-SAT search is intended for performance and should not be assumed to return an identical optimum or enumeration order on every platform/runtime combination.

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

“Independent verification” means a code path separate from the CP-SAT model checks the serialized result against the declared contract without trusting solver state. It is not a formal proof of OR-Tools, Python, or the host machine. Constraint satisfaction demonstrates rule compliance; it does not prove aesthetic quality or historical-style authenticity. Likewise, the v2.3 Pareto result is nondominated within the explored candidate pool, not a proof of the global Pareto frontier.

See [Architecture](docs/ARCHITECTURE.md), [Verification](docs/VERIFICATION.md), [History](docs/HISTORY.md), and [Roadmap](docs/ROADMAP.md).
