# Constraint Music

**Deterministic symbolic music synthesis with explicit hard constraints, CP-SAT optimization, and independent post-solve verification.**

Constraint Music treats composition as a verifiable constraint problem. A YAML specification is compiled into an OR-Tools CP-SAT model; the solver produces melody, rhythm, bass, harmony, and a solver-native SATB realization; a separate application-level verifier rechecks the declared musical contract from ordinary serialized values; only verified results are exported.

> Current release: **2.4.0a1** — solver-native SATB harmony with independently verified voice-leading, chord-completeness, and provenance semantics.

## Pipeline

```text
YAML specification
      |
      v
pitch + harmony + rhythm + motif + phrase grammar + SATB harmony
      |
      v
OR-Tools CP-SAT compiler
      |
      v
weighted solve / no-good enumeration / Pareto candidate search
      |
      v
independent 32-rule verifier + objective-vector recomputation
      |
      +----> MIDI with real ties/rests
      +----> JSON + SATB + contract/provenance/search digests
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

`--count` produces genuinely distinct alternatives. After each accepted composition, CP-SAT receives a no-good cut over the selected dimensions:

```bash
constraint-music generate examples/eight_bar_period.yaml \
  --count 4 \
  --distinct-on melody,harmony \
  --output build/variant.mid \
  --json build/variant.json
```

Supported distinctness dimensions are `melody`, `rhythm`, `bass`, and `harmony`.

The objective is exposed as five minimized components:

- `tension_deviation`
- `melody_motion`
- `bass_motion`
- `harmonic_repetition`
- `contour_mismatch`

The solver computes these components internally, then Constraint Music independently reconstructs the same vector from the finished musical values. A disagreement fails closed.

Pareto mode explores deterministic weighted scalarizations, guarantees distinct candidates through no-good cuts, and filters dominated candidates from the explored pool. This is a bounded Pareto-front approximation, not a proof that the complete feasible Pareto frontier has been enumerated. See [Distinct Enumeration and Pareto Search](docs/ENUMERATION_AND_PARETO.md).

## v2.4: solver-native SATB harmony

Every solved composition now includes a beat-level four-part harmonic skeleton:

- soprano is an explicit solver variable anchored to the strong-grid melody;
- alto is solved inside MIDI range `55..74`;
- tenor is solved inside MIDI range `48..67`;
- bass remains the existing configured solver-native bass voice.

CP-SAT enforces strict `bass < tenor < alto < soprano` ordering, octave spacing between adjacent upper voices, complete diatonic triads, explicit root doubling, parallel-perfect avoidance for every pair involving an inner voice, and alto/tenor leading-tone resolution.

The SATB layer is independently rechecked after solving and after JSON reload. `distinct_on=harmony` now includes alto/tenor realizations as well as chord degrees. See [Solver-Native SATB Harmony](docs/SATB_HARMONY.md).

## Hard-constraint contract

v2.4 extends the certification contract to **32 stable hard-rule IDs**. `CM001`–`CM021` cover tonal, rhythmic, motif, and articulation rules; `CM022`–`CM026` cover phrase structure; `CM027`–`CM032` cover SATB shape, ranges/order, spacing, chord completeness/root doubling, inner-voice parallel-perfect avoidance, and tendency-tone resolution.

Search strategy remains separate from feasibility certification.

See [Rhythm and Motifs](docs/RHYTHM_AND_MOTIFS.md), [Phrase Grammar](docs/PHRASE_GRAMMAR.md), [Distinct Enumeration and Pareto Search](docs/ENUMERATION_AND_PARETO.md), [Solver-Native SATB Harmony](docs/SATB_HARMONY.md), and [Verification](docs/VERIFICATION.md).

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

The command rechecks all 32 hard rules, artifact schema, constraint-contract digest, semantic composition digest, full artifact-content digest, and objective-vector metadata. SATB voice arrays are committed by artifact schema `2.4`.

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

“Independent verification” means a code path separate from the CP-SAT model checks the serialized result against the declared contract without trusting solver state. It is not a formal proof of OR-Tools, Python, or the host machine. Constraint satisfaction demonstrates rule compliance; it does not prove aesthetic quality or historical-style authenticity. The SATB contract is intentionally limited to diatonic triads and the explicit v2.4 voice-leading rules; it is not a complete species-counterpoint or common-practice-harmony model. Likewise, the Pareto result is nondominated within the explored candidate pool, not a proof of the global Pareto frontier.

See [Architecture](docs/ARCHITECTURE.md), [Verification](docs/VERIFICATION.md), [History](docs/HISTORY.md), and [Roadmap](docs/ROADMAP.md).
