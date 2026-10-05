# Reproducibility

## Environment

Supported interpreters are Python 3.11–3.13. Record the following with every result:

- repository commit and dirty-state flag;
- package, artifact-schema, contract, and oracle versions;
- `python --version` and `python -m pip freeze`;
- operating system, CPU, memory, and worker count;
- request, seed, time limit, render profile, and input/output SHA-256 values;
- command, UTC timestamp, raw failures, solver `UNKNOWN` outcomes, and exclusions.

Install the complete development environment with:

```bash
python -m pip install -e ".[dev]"
```

The development extra pins `ortools==9.15.6755` because the checked-in CP-SAT
generator-boundary evidence is version-specific. The broader `generation` extra retains
the supported compatible range for ordinary package use; do not regenerate research
evidence from that unpinned environment.

The checker-only runtime intentionally omits CP-SAT:

```bash
python -m pip install -e .
python -c "from constraint_music.certification import verify_artifact"
```

## Required gates

```bash
ruff check src tests research
mypy src
python -m pytest
python -m build
python -m research.enumerate_fragments \
  --output research/results/bounded_conformance.json
```

The bounded enumerator reports separately named pitch-class, absolute-register,
context/anchor, voice-resolution, and complete-verifier partitions. It records
generated/visited cardinalities, explicit pruning, category counts, first disagreements,
and implementation hashes. The context/anchor partition enumerates every beat in
2..8-beat open and authentic-cadence forms plus every valid single-modulation boundary,
crossed with supported-target and modal-overlap truth values.
The checked-in evidence must match a fresh run data-for-data after JSON parsing. It
must not be described as exhaustive beyond each declared domain; the complete-verifier
matrix is explicitly systematic.
The same aggregate evidence also records a pinned six-case generator finalization
matrix: one valid control, four generated-assignment corruptions, and one
compiled-objective corruption. Every injected fault must raise the production
`InternalVerificationError` boundary; source and dependency hashes are persisted.
It additionally deletes one exact named `CM057` CP-SAT clause, checks that its index
falls inside the registered compiler phase, and requires the independent oracle,
application verifier, and production finalizer to reject the exposed witness. Five
cross-feature partitions pair valid controls with targeted faults under coenabled
tonicization, modal mixture, rhythm, authentic cadence, and modulation. These are
finite local comparisons, not a global compiler/checker-equivalence claim.

The artifact corruption harness records `ACCEPT`, `REJECT`, `BLOCKED`, and `CRASH`
separately:

```bash
python -m research.run_corruption_benchmark ARTIFACT.json \
  --spec REQUEST.yaml \
  --output research/results/corruption.jsonl
```

Run performance measurements on recorded hardware, preserve unsuccessful attempts in
denominators, and separate compile, solve, artifact verification, export, and parse-back
time. Shared CI timing is a smoke signal, not a controlled performance result.

## Determinism

Use a fixed seed and `workers: 1` for deterministic regression and enumeration order.
Multi-worker CP-SAT runs may return different feasible/optimal assignments across
runtimes. All research tables must retain raw machine-readable results and the exact
configuration used to derive them.
