# Constraint Music

**Deterministic symbolic music synthesis with explicit hard constraints, CP-SAT optimization, and an independent post-solve verifier.**

Constraint Music does not ask a neural model to improvise and then call the result valid. A composition specification is compiled into an OR-Tools CP-SAT model; the resulting melody, bass, and harmony are converted back to ordinary values; a separate verifier re-checks the declared musical contract; only verified results are exported.

> Current release: **2.0.0a1** — a clean revival of the recovered v1.1 engine with a stricter verification boundary and tamper-evident JSON artifacts.

## Why it exists

Most generative-music systems optimize plausibility. Constraint Music explores a different question: **what if the musical requirements are explicit, inspectable, and non-negotiable?**

That makes the project useful as a compact research/engineering substrate for controllable composition, symbolic generation, solver-backed repair, counterpoint experiments, and future neuro-symbolic workflows.

## Pipeline

```text
YAML specification
      |
      v
GenerationSpec + tonal theory
      |
      v
OR-Tools CP-SAT compiler
      |
      v
feasible / optimized assignment
      |
      v
independent hard-rule verifier
      |
      +----> MIDI
      +----> JSON + contract/provenance digests
```

The solver is not trusted merely because it reports `OPTIMAL` or `FEASIBLE`. If the independent verifier rejects the assignment, generation fails closed.

## Hard-constraint contract

v2.0a1 declares 16 stable rule IDs:

| ID | Rule |
|---|---|
| CM001 | output shape matches the specification |
| CM002 | melody stays in-key and in range |
| CM003 | bass stays in-key and in range |
| CM004 | chord degrees stay in `0..6` |
| CM005 | strong-beat melody notes are chord tones |
| CM006 | bass notes are chord members |
| CM007 | chord transitions obey the configured graph |
| CM008 | melodic leaps obey the configured bound |
| CM009 | melodic tritones are forbidden |
| CM010 | leading tones resolve upward when enabled |
| CM011 | repeated-note runs are bounded |
| CM012 | large melodic leaps recover by contrary step |
| CM013 | bass leaps obey the configured bound |
| CM014 | bass tritones are forbidden |
| CM015 | parallel perfect fifths/octaves are forbidden when enabled |
| CM016 | authentic phrase opening/closure is enforced when enabled |

The recovered v1.1 implementation already solved all of these musical rules, but its separate validator did **not** re-check CM009, CM012, or CM014. That drift is closed in v2.

## Soft objective

Within the feasible region, CP-SAT minimizes a weighted objective that:

- tracks a user-defined per-beat tension curve;
- discourages unnecessary melody and bass motion;
- discourages repeated notes/chords;
- encourages melodic contour to follow large tension changes;
- adds seeded micro-costs for reproducible variation.

A soft score can never purchase a violation of a hard rule.

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
constraint-music generate examples/four_bar_arch.yaml \
  --output build/four_bar_arch.mid \
  --json build/four_bar_arch.json \
  --print-grid
```

Generate reproducible alternatives:

```bash
constraint-music generate examples/d_minor_pressure.yaml \
  --output build/d_minor.mid \
  --json build/d_minor.json \
  --count 4
```

## Verify an artifact without rerunning the solver

```bash
constraint-music verify build/four_bar_arch.json
```

The command re-checks all 16 hard rules and verifies the v2 artifact schema, constraint-contract digest, semantic composition digest, and full artifact-content digest.

Recovered v1 JSON can still receive musical verification:

```bash
constraint-music verify old_result.json --allow-legacy
```

Legacy mode deliberately does not claim v2 provenance integrity.

## Configuration

```yaml
key: C
mode: major                    # major | minor (harmonic minor)
bars: 4
beats_per_bar: 4
subdivisions_per_beat: 2

tempo_bpm: 108
melody_low: 60
melody_high: 81
bass_low: 36
bass_high: 55

max_melody_leap: 12
max_bass_leap: 7
max_repeated_notes: 2
require_authentic_cadence: true
resolve_leading_tone: true
avoid_parallel_perfects: true

tension_curve: [0.06, 0.22, 0.48, 0.86, 0.54, 0.18, 0.02]
seed: 20260719
max_time_seconds: 15
workers: 8
```

`progression_graph` is optional and may be overridden per specification. Degrees are zero-based (`0=I/i`, ..., `6=vii°`). Every source degree must define at least one permitted target.

## Reproducibility

For deterministic regression work, set `workers: 1` and a fixed `seed`. Multi-worker CP-SAT search is optimized for performance and should not be assumed to reproduce an identical assignment across every platform/runtime combination.

## Quality gates

```bash
ruff check src tests
mypy src
pytest --cov=constraint_music --cov-report=term-missing
python -m build
```

GitHub Actions runs runtime tests on Python 3.11, 3.12, and 3.13. Ruff runs across the matrix; strict mypy analysis and package building are anchored to Python 3.11, the minimum supported interpreter.

## Design claim boundary

“Independent verification” here means a separate application-level code path evaluates the serialized assignment against the declared contract without inspecting the CP-SAT model or solver state. It is **not** a formal proof of OR-Tools, Python, or the host machine, and it is not a theorem establishing equivalence for arbitrary future implementations.

See [Architecture](docs/ARCHITECTURE.md), [Verification](docs/VERIFICATION.md), [Roadmap](docs/ROADMAP.md), and [Project history](docs/HISTORY.md).

## Status

`2.0.0a1` is a pre-release engineering baseline. The next development target is expressive structure: rhythm CSP, motif/phrase grammar, counterpoint, SATB voicing, Pareto enumeration, and human-readable unsatisfiable-constraint explanations.
