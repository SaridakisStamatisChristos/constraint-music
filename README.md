# Constraint Music

**Deterministic symbolic music synthesis with explicit hard constraints, CP-SAT optimization, and independent post-solve verification.**

Constraint Music treats composition as a verifiable constraint problem. A YAML specification is compiled into an OR-Tools CP-SAT model; the solver produces melody, rhythm, bass, harmonic identity, and a solver-native SATB realization; a separate application-level verifier reconstructs the declared musical semantics from ordinary serialized values; only verified results are exported.

> Current release line: **2.10.0a1** — verified secondary leading-tone chords with explicit local target identity and independent tendency-tone semantics.

## Pipeline

```text
YAML GenerationSpec
      |
      v
pitch + rhythm + phrase grammar
      |
      +--> chord degree + harmonic form
      +--> local target identity
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
      +--> independent 54-rule verifier
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
- **v2.10** — target-derived secondary leading-tone triads with independent local tendency-tone resolution.

## Harmonic identity stays decomposed

Constraint Music deliberately avoids a single opaque Roman-numeral field. Each beat may carry independent semantic axes:

- `harmony` — functional/support chord-degree sequence;
- `harmonic_form` — chord kind + inversion;
- `tonicization` — nullable local target identity used by certified target-bearing chromatic functions;
- `modal_source` — nullable canonical parallel source;
- `key_context` — persistent active local-key sequence / modulation identity;
- `voicing` — SATB realization.

The global key is immutable for the artifact. A target-bearing seventh is an applied dominant; in v2.10 a target-bearing triad is a secondary leading-tone chord. Modulation changes persistent active-key interpretation without rewriting the global key.

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

v2.8 distinguishes persistent modulation from local target events. Its conservative certified model supports one same-mode modulation to the dominant key with:

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

v2.9 does **not** make every parallel-source seventh legal. The theory layer admits only a narrow source-derived subset that can preserve the established CM005/CM006 outer-voice contract and reuse certified seventh-resolution semantics. After modulation, borrowing is derived from the **destination active key**, never from stale global-key context.

See [Borrowed Seventh Chords](docs/BORROWED_SEVENTHS.md).

## v2.10: verified secondary leading-tone chords

Secondary leading-tone harmony is independently opt-in:

```yaml
secondary_leading_tone_enabled: true
minimum_secondary_leading_tone_chords: 1
```

v2.10 derives `vii°/x` directly from the exact active local key and explicit target degree. It does not grant unrestricted chromatic pitch permission and it does not encode the chromatic root as a fake diatonic degree. Instead, the serialized `chord_degree` remains a deterministic **support degree** chosen so legacy CM005/CM006/CM007 semantics remain intact, while the actual diminished sonority is independently reconstructed from active key + target identity.

Every certified secondary leading-tone chord must:

- target a supported non-tonic diatonic major/minor triad;
- carry `ChordKind.TRIAD` plus explicit target identity;
- realize the complete target-derived diminished triad;
- contain the local leading tone and diminished fifth exactly once and double the stable third;
- use root, first, or second inversion with bass agreement;
- resolve immediately to the declared unaltered triadic target;
- resolve the local leading tone upward by semitone;
- resolve the diminished fifth downward by step;
- remain disjoint from modal borrowing and certified pivot/cadence anchors;
- use the persistent destination key after modulation rather than stale global context.

A target-bearing seventh remains an applied dominant. This form-based disambiguation prevents secondary leading-tone chords from satisfying `minimum_applied_dominants` accidentally.

See [Secondary Leading-Tone Chords](docs/SECONDARY_LEADING_TONE.md).

## Hard-constraint contract

v2.10 exposes **54 stable hard-rule IDs**:

- `CM001–CM021` — tonal, rhythmic, motif, and articulation rules;
- `CM022–CM026` — phrase structure;
- `CM027–CM032` — SATB contract;
- `CM033–CM036` — expanded harmonic form and seventh behavior;
- `CM037–CM040` — applied-dominant tonicization;
- `CM041–CM042` — modal-source context and borrowed-triad realization;
- `CM043–CM048` — persistent key context and controlled modulation;
- `CM049–CM051` — borrowed-seventh eligibility, source-derived realization, and tendency resolution;
- `CM052–CM054` — secondary leading-tone context, exact diminished realization, and target/tendency resolution.

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

The verifier rechecks the musical contract plus artifact schema, contract digest, semantic composition digest, full artifact-content digest, and objective-vector metadata. Current package version is `2.10.0a1`; artifact and constraint-contract versions are `2.10`.

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

v2.10 deliberately does not certify secondary leading-tone seventh chords, third-inversion sevenths, arbitrary modulation chains, distant-key networks, enharmonic reinterpretation, augmented-sixth/Neapolitan reinterpretation, free key-center inference, or probabilistic harmony certification.

See [Architecture](docs/ARCHITECTURE.md), [Verification](docs/VERIFICATION.md), [History](docs/HISTORY.md), [Roadmap](docs/ROADMAP.md), and [Changelog](CHANGELOG.md).
