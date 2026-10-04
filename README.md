# Constraint Music

**Deterministic symbolic music synthesis with explicit hard constraints, CP-SAT optimization, and independent post-solve verification.**

Constraint Music treats composition as a verifiable constraint problem. A YAML specification is compiled into an OR-Tools CP-SAT model; the solver produces melody, rhythm, bass, harmonic identity, and a solver-native SATB realization; a separate application-level verifier reconstructs the declared musical semantics from ordinary serialized values; only verified results are exported.

> Current release line: **2.9.0a1** — source-aware borrowed seventh chords under explicit persistent active-key context.

## Pipeline

```text
YAML GenerationSpec
      |
      v
pitch + rhythm + phrase grammar
      |
      +--> chord degree + harmonic form
      +--> tonicization target
      +--> modal source
      +--> persistent key context / modulation identity
      |
      v
OR-Tools CP-SAT compiler
      |
      v
weighted solve / no-good enumeration / Pareto candidate search
      |
      v
ordinary serialized musical values
      |
      +--> independent 51-rule verifier
      +--> independent objective-vector recomputation
      +--> semantic provenance digests
      |
      +----> MIDI with real ties/rests
      +----> JSON + SATB + harmonic/context metadata
```

A solver status of `OPTIMAL` or `FEASIBLE` is never sufficient. Solver/verifier or solver/objective disagreement fails closed.

## Release progression

- **v2.1** — explicit rhythm CSP and motif grammar.
- **v2.2** — phrase grammar and phrase-local cadence semantics.
- **v2.3** — exact distinct enumeration and bounded Pareto search.
- **v2.4** — solver-native SATB harmony.
- **v2.5** — opt-in diatonic seventh vocabulary and structured inversions.
- **v2.6** — verified applied-dominant tonicization.
- **v2.7** — verified modal mixture with explicit parallel-source identity.
- **v2.8** — persistent active local-key regions and one certified dominant-key modulation.
- **v2.8.0a2** — strict modulation repair with context-union domains and no terminal tendency-tone exemption.
- **v2.9** — source-aware borrowed seventh chords composed with active-key and modal-source semantics.

## Harmonic identity stays decomposed

Constraint Music deliberately avoids a single opaque Roman-numeral field. Each beat may carry independent semantic axes:

- `harmony` — functional chord-degree sequence;
- `harmonic_form` — chord kind + inversion;
- `tonicization` — nullable applied/local target;
- `modal_source` — nullable canonical parallel source;
- `key_context` — persistent active local-key sequence / modulation identity;
- `voicing` — SATB realization.

The global key is immutable for the artifact. Tonicization is a local applied event; modulation changes persistent active-key interpretation without rewriting the global key.

## v2.5: expanded harmonic vocabulary

Expanded harmony is opt-in:

```yaml
harmony_vocabulary: triads+sevenths
minimum_seventh_chords: 1
```

The certified vocabulary includes complete diatonic seventh chords, root/first/second inversions, downward chordal-seventh resolution, and explicit dominant-seventh behavior. Third inversion remains intentionally deferred.

See [Expanded Harmony](docs/EXPANDED_HARMONY.md).

## v2.6: verified tonicization

```yaml
harmony_vocabulary: triads+sevenths
tonicization_enabled: true
minimum_applied_dominants: 1
```

Each applied dominant carries an explicit nullable `tonicization_target`. Exact pitch content, inversion, target resolution, chordal-seventh motion, and local leading-tone motion are reconstructed independently.

See [Applied-Dominant Tonicization](docs/TONICIZATION.md).

## v2.7: verified modal mixture

```yaml
modal_mixture_enabled: true
minimum_borrowed_chords: 1
```

Major active keys use the parallel natural minor as their canonical source; minor active keys use the parallel major. Borrowed triads are derived from the active tonic, explicit source, and stored functional degree. Modal source is explicit data, not permission for arbitrary chromatic pitches.

See [Modal Mixture](docs/MODAL_MIXTURE.md).

## v2.8: persistent local key and controlled modulation

v2.8 distinguishes persistent modulation from tonicization. Its conservative certified model supports one same-mode modulation to the dominant key with:

- an explicit destination key;
- an explicit boundary;
- source I as a common-chord pivot reinterpreted as destination IV;
- persistent destination-key interpretation after the boundary;
- destination V-I confirmation;
- one serialized active key context per beat.

The strict v2.8.0a2 repair uses union storage domains only as storage. Every melody/bass step is still admitted against its exact active key. The terminal destination cadence retains generic tendency-tone rules and independently requires every SATB carrier of the destination leading tone to resolve upward by semitone.

## v2.9: source-aware borrowed seventh chords

Borrowed sevenths are enabled by composing the existing modal-mixture and expanded-harmony switches:

```yaml
harmony_vocabulary: triads+sevenths
modal_mixture_enabled: true
minimum_borrowed_chords: 1
minimum_seventh_chords: 1
```

v2.9 does **not** make every parallel-source seventh legal. The theory layer admits only a narrow source-derived subset that can preserve the established CM005/CM006 outer-voice contract and reuse certified seventh-resolution semantics. Each admitted borrowed seventh must:

- use the canonical parallel source for the exact active local key;
- be genuinely distinct from the active-key seventh;
- contain all four source-derived chord members exactly once;
- use only root, first, or second inversion;
- keep soprano and bass compatible with the active-key triadic core;
- carry no simultaneous tonicization target;
- stay outside certified modulation pivot/cadence anchors;
- resolve its chordal seventh downward by step;
- resolve any admitted parallel-major source leading tone upward by semitone.

After modulation, borrowing is derived from the **destination active key**, never from stale global-key context.

See [Borrowed Seventh Chords](docs/BORROWED_SEVENTHS.md).

## Hard-constraint contract

v2.9 exposes **51 stable hard-rule IDs**:

- `CM001–CM021` — tonal, rhythmic, motif, and articulation rules;
- `CM022–CM026` — phrase structure;
- `CM027–CM032` — SATB contract;
- `CM033–CM036` — expanded harmonic form and seventh behavior;
- `CM037–CM040` — tonicization;
- `CM041–CM042` — modal-source context and borrowed-triad realization;
- `CM043–CM048` — persistent key context and controlled modulation;
- `CM049–CM051` — borrowed-seventh eligibility, source-derived realization, and tendency resolution.

Search/ranking semantics cannot waive a hard rule.

See [Verification](docs/VERIFICATION.md).

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
constraint-music generate examples/modal_mixture.yaml \
  --output build/composition.mid \
  --json build/composition.json \
  --print-grid
```

## Verify without rerunning CP-SAT

```bash
constraint-music verify build/composition.json
```

The verifier rechecks the musical contract plus artifact schema, contract digest, semantic composition digest, full artifact-content digest, and objective-vector metadata. Current package version is `2.9.0a1`; artifact and constraint-contract versions are `2.9`.

Older payloads remain loadable without inventing newer semantic metadata when the corresponding feature is disabled. `--allow-legacy` remains available for intentional inspection of older provenance versions.

## Reproducibility

Use `workers: 1` with a fixed `seed` for deterministic regression work and deterministic enumeration order. Multi-worker CP-SAT search is for performance and should not be assumed to return an identical optimum or enumeration order on every runtime.

## Quality gates

Every supported interpreter runs the same complete gate:

```bash
ruff check src tests
mypy --python-version <3.11|3.12|3.13> src
pytest --cov=constraint_music --cov-report=term-missing
python -m build
```

GitHub Actions runs those gates independently on Python **3.11, 3.12, and 3.13**.

## Scope boundary

Independent verification is an application-level separation of trust, not a formal proof of OR-Tools, Python, or the host machine. Constraint satisfaction demonstrates conformance to the declared executable contract; it does not prove aesthetic quality or complete historical-style authenticity.

v2.9 deliberately does not certify secondary leading-tone chords, third-inversion sevenths, arbitrary modulation chains, distant-key networks, enharmonic reinterpretation, augmented-sixth/Neapolitan reinterpretation, free key-center inference, or probabilistic harmony certification.

See [Architecture](docs/ARCHITECTURE.md), [Verification](docs/VERIFICATION.md), [History](docs/HISTORY.md), [Roadmap](docs/ROADMAP.md), and [Changelog](CHANGELOG.md).
