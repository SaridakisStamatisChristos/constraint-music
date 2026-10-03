# Constraint Music

**Deterministic symbolic music synthesis with explicit hard constraints, CP-SAT optimization, and independent post-solve verification.**

Constraint Music treats composition as a verifiable constraint problem. A YAML specification is compiled into an OR-Tools CP-SAT model; the solver produces melody, rhythm, bass, harmonic identity, and a solver-native SATB realization; a separate application-level verifier rechecks the declared musical contract from ordinary serialized values; only verified results are exported.

> Current release line: **2.7.0a1** — verified modal mixture with explicit parallel-source identity, source-derived borrowed triads, and independently checked realization.

## Pipeline

```text
YAML specification
      |
      v
pitch + rhythm + phrase grammar + harmonic form + tonicization + modal source
      |
      v
OR-Tools CP-SAT compiler
      |
      v
weighted solve / no-good enumeration / Pareto candidate search
      |
      v
independent 42-rule verifier + objective-vector recomputation
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

Each applied dominant carries an explicit nullable `tonicization_target`. Constraint Music derives its dominant-seventh pitch classes from the declared global key and target degree, realizes the complete sonority in SATB, requires immediate resolution to the untargeted target chord, and verifies local leading-tone and chordal-seventh motion independently.

See [Applied-Dominant Tonicization](docs/TONICIZATION.md).

## v2.7: verified modal mixture

Modal mixture is opt-in and independent of the seventh vocabulary:

```yaml
modal_mixture_enabled: true
minimum_borrowed_chords: 1
```

v2.7 gives every beat an explicit nullable **modal source**. Global-major pieces borrow triads from the parallel natural minor; global-minor pieces borrow from the parallel major. The source is canonical data, not a Roman-numeral label, and the borrowed pitch classes are reconstructed directly from the global tonic, source mode, and stored functional degree.

For example, in C major, global degree IV is F-A-C while the parallel-natural-minor source yields borrowed `iv` = F-Ab-C. The altered Ab is legal only because that beat explicitly declares the source mode.

The v2.7 compatibility boundary is strict: `CM005` and `CM006` retain their established global triadic-core meaning, so borrowed chromatic tones are carried by inner voices. Borrowing is forbidden on the final beat and, when authentic closure is required, on the penultimate beat. A beat cannot simultaneously be borrowed and tonicized.

Search identity remains decomposed:

- `harmony` — global chord-degree sequence;
- `harmonic_form` — chord kind + inversion;
- `tonicization` — nullable local-target sequence;
- `modal_source` — nullable parallel-source sequence;
- `voicing` — alto/tenor realization.

```bash
constraint-music generate examples/modal_mixture.yaml \
  --count 2 \
  --distinct-on modal_source \
  --output build/mixture.mid \
  --json build/mixture.json
```

See [Modal Mixture](docs/MODAL_MIXTURE.md).

## Hard-constraint contract

v2.7 extends the certification contract to **42 stable hard-rule IDs**. `CM001`–`CM021` cover tonal, rhythmic, motif, and articulation rules; `CM022`–`CM026` cover phrase structure; `CM027`–`CM032` preserve the SATB contract; `CM033`–`CM036` certify harmonic-form and seventh-chord behavior; `CM037`–`CM040` certify tonicization; `CM041`–`CM042` certify modal-source context and exact source-derived borrowed-triad realization.

Search strategy remains separate from feasibility certification.

See [Rhythm and Motifs](docs/RHYTHM_AND_MOTIFS.md), [Phrase Grammar](docs/PHRASE_GRAMMAR.md), [Distinct Enumeration and Pareto Search](docs/ENUMERATION_AND_PARETO.md), [Solver-Native SATB Harmony](docs/SATB_HARMONY.md), [Expanded Harmony](docs/EXPANDED_HARMONY.md), [Applied-Dominant Tonicization](docs/TONICIZATION.md), [Modal Mixture](docs/MODAL_MIXTURE.md), and [Verification](docs/VERIFICATION.md).

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
constraint-music generate examples/modal_mixture.yaml \
  --output build/mixture.mid \
  --json build/mixture.json \
  --print-grid
```

## Verify without rerunning CP-SAT

```bash
constraint-music verify build/mixture.json
```

The command rechecks all 42 hard rules plus artifact schema, contract digest, semantic composition digest, full artifact-content digest, and objective-vector metadata. Artifact schema `2.7` commits SATB voices, harmonic form, tonicization targets, and modal-source metadata when present. Older payloads remain loadable without inventing missing context metadata when the corresponding feature is disabled.

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

v2.7 implements bounded modal mixture through source-identified borrowed triads only. Borrowed sevenths, secondary leading-tone chords, arbitrary altered harmony, persistent local-key regions, pivot-chord modulation, and third-inversion sevenths remain outside this release rather than being represented partially. Pareto results remain nondominated within the explored candidate pool, not a proof of the global Pareto frontier.

See [Architecture](docs/ARCHITECTURE.md), [Verification](docs/VERIFICATION.md), [History](docs/HISTORY.md), and [Roadmap](docs/ROADMAP.md).
