# Constraint Music

**Deterministic symbolic music synthesis with explicit hard constraints, CP-SAT optimization, and independent post-solve verification.**

Constraint Music treats composition as a verifiable constraint problem. A YAML specification is compiled into an OR-Tools CP-SAT model; the solver produces melody, rhythm, bass, harmonic identity, and a solver-native SATB realization; a separate application-level verifier rechecks the declared musical contract from ordinary serialized values; only verified results are exported.

> Current release line: **2.6.0a1** — verified applied-dominant tonicization with explicit local target identity, exact dominant-seventh realization, and independently checked target/tendency resolution.

## Pipeline

```text
YAML specification
      |
      v
pitch + rhythm + phrase grammar + harmonic form + tonicization context
      |
      v
OR-Tools CP-SAT compiler
      |
      v
weighted solve / no-good enumeration / Pareto candidate search
      |
      v
independent 40-rule verifier + objective-vector recomputation
      |
      +----> MIDI with real ties/rests
      +----> JSON + SATB + harmonic context + contract/provenance/search digests
```

A solver status of `OPTIMAL` or `FEASIBLE` is not sufficient. A solver assignment rejected by the independent verifier fails closed.

## v2.1: explicit rhythm and motifs

Rhythm generation is optional and uses three states per melody grid step: `onset`, `tie`, and `rest`. Motifs support exact repetition and exact semitone transposition with rhythm inheritance. When `rhythm_enabled` is false, every melody grid position is an onset, preserving v2.0 behavior.

## v2.2: phrase grammar

Phrases are explicit spans with roles, cadence semantics, and optional structural relations. Supported roles are `statement`, `antecedent`, `consequent`, `transition`, and `cadential`; supported relations are `independent`, `repeat`, `transpose`, `sequence`, and `answer`.

See [Phrase Grammar](docs/PHRASE_GRAMMAR.md) for exact executable semantics.

## v2.3: distinct enumeration and Pareto search

`--count` produces genuinely distinct alternatives through CP-SAT no-good cuts. The established `harmony` dimension means **chord-degree sequence** and remains backward compatible.

```bash
constraint-music generate examples/eight_bar_period.yaml \
  --count 4 \
  --distinct-on melody,harmony \
  --output build/variant.mid \
  --json build/variant.json
```

The objective exposes five minimized components: `tension_deviation`, `melody_motion`, `bass_motion`, `harmonic_repetition`, and `contour_mismatch`. Constraint Music independently reconstructs the vector from finished musical values and fails closed on disagreement.

See [Distinct Enumeration and Pareto Search](docs/ENUMERATION_AND_PARETO.md).

## v2.4: solver-native SATB harmony

Every solved composition includes a beat-level four-part harmonic skeleton. Soprano is solver-native and anchored to the strong-grid melody; alto and tenor are independently solved; bass remains the configured solver-native bass voice. CP-SAT enforces ordering, spacing, complete triads/root doubling, inner-voice parallel-perfect avoidance, and inner leading-tone resolution.

`--distinct-on voicing` enumerates different alto/tenor realizations without redefining `harmony`.

See [Solver-Native SATB Harmony](docs/SATB_HARMONY.md).

## v2.5: expanded harmonic vocabulary

Expanded harmony is opt-in so existing specifications keep the v2.4 triadic feasible set:

```yaml
harmony_vocabulary: triads+sevenths
minimum_seventh_chords: 1
```

v2.5 adds structured chord kind (`triad` / `seventh`) and inversion metadata, complete diatonic seventh chords, root/first/second inversions, downward chordal-seventh resolution, and explicit `V7 -> I` behavior with leading-tone resolution in whichever SATB voice carries the tendency tone.

The legacy `harmony` search dimension still means only the chord-degree sequence. `harmonic_form` distinguishes chord kind and inversion.

See [Expanded Harmony](docs/EXPANDED_HARMONY.md).

## v2.6: applied-dominant tonicization

Tonicization is a separate, opt-in harmonic-context dimension layered on top of the v2.5 seventh vocabulary:

```yaml
harmony_vocabulary: triads+sevenths
tonicization_enabled: true
minimum_applied_dominants: 1
```

An applied dominant is not represented as an opaque Roman-numeral string or as unrestricted chromatic permission. Each beat carries an explicit nullable `tonicization_target`. For a non-null target, Constraint Music derives the dominant root and the complete dominant-seventh pitch-class set from the declared global key and target degree, realizes that sonority in SATB, and requires immediate resolution to the untargeted diatonic local tonic.

For example, in C major a tonicization of scale degree 5 is represented semantically as `V7/V`; its realized pitch classes are D-F#-A-C, its local leading tone F# must resolve to G, and its chordal seventh C must resolve downward by step.

The v2.6 compatibility boundary is deliberate: CM005/CM006 retain their historical global-diatonic triadic-core meanings. Therefore chromatic applied tones are carried by inner voices, while soprano and bass remain compatible with the established outer-voice contract. Targets that cannot satisfy that representation are rejected structurally rather than silently weakening older rules.

Search identity remains decomposed:

- `harmony` — chord-degree sequence;
- `harmonic_form` — chord kind + inversion;
- `tonicization` — nullable local target sequence;
- `voicing` — alto/tenor realization.

```bash
constraint-music generate examples/applied_dominants.yaml \
  --count 3 \
  --distinct-on harmonic_form,tonicization,voicing \
  --output build/tonicized.mid \
  --json build/tonicized.json
```

See [Applied-Dominant Tonicization](docs/TONICIZATION.md).

## Hard-constraint contract

v2.6 extends the certification contract to **40 stable hard-rule IDs**. `CM001`–`CM021` cover tonal, rhythmic, motif, and articulation rules; `CM022`–`CM026` cover phrase structure; `CM027`–`CM032` preserve the SATB contract; `CM033`–`CM036` certify harmonic-form and seventh-chord behavior; `CM037`–`CM040` certify tonicization context, exact applied-dominant realization, target resolution, and local tendency-tone resolution.

Search strategy remains separate from feasibility certification.

See [Rhythm and Motifs](docs/RHYTHM_AND_MOTIFS.md), [Phrase Grammar](docs/PHRASE_GRAMMAR.md), [Distinct Enumeration and Pareto Search](docs/ENUMERATION_AND_PARETO.md), [Solver-Native SATB Harmony](docs/SATB_HARMONY.md), [Expanded Harmony](docs/EXPANDED_HARMONY.md), [Applied-Dominant Tonicization](docs/TONICIZATION.md), and [Verification](docs/VERIFICATION.md).

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
constraint-music generate examples/applied_dominants.yaml \
  --output build/applied.mid \
  --json build/applied.json \
  --print-grid
```

## Verify without rerunning CP-SAT

```bash
constraint-music verify build/applied.json
```

The command rechecks all 40 hard rules plus artifact schema, contract digest, semantic composition digest, full artifact-content digest, and objective-vector metadata. Artifact schema `2.6` commits SATB voices, harmonic kind/inversion metadata, and tonicization targets when present. Older SATB/harmonic-form payloads remain loadable without inventing missing tonicization metadata when tonicization is disabled.

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

“Independent verification” means a code path separate from the CP-SAT model checks the serialized result against the declared contract without trusting solver state. It is not a formal proof of OR-Tools, Python, or the host machine. Constraint satisfaction demonstrates rule compliance; it does not prove aesthetic quality or complete historical-style authenticity.

v2.6 implements bounded tonicization through verified applied dominant sevenths only. Modal mixture, secondary leading-tone chords, arbitrary chromatic harmony, persistent local-key regions, pivot-chord analysis, and modulation remain outside this release rather than being represented partially. Third-inversion sevenths likewise remain deferred because they would require an explicit revision of the preserved outer-voice compatibility contract. Pareto results remain nondominated within the explored candidate pool, not a proof of the global Pareto frontier.

See [Architecture](docs/ARCHITECTURE.md), [Verification](docs/VERIFICATION.md), [History](docs/HISTORY.md), and [Roadmap](docs/ROADMAP.md).
