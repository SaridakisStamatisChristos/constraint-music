# Engineering Assurance Status

This document summarizes the durable engineering-assurance state of Constraint Music 2.13. It separates implemented release behavior from bounded research evidence and from stronger claims that remain intentionally unmade.

A passing build or CI run is not, by itself, a publication-readiness or universal-correctness claim.

## Current baseline

- Package: `2.13.0a1`
- Artifact schema: `2.13`
- Executable contract: `2.13`
- Certification profile: `certified-satb`
- Canonicalization profile: `constraint-music-json-v1`
- Hard-rule range: `CM001-CM057`

## Assurance areas

| Area | Status | Implemented evidence | Boundary / remaining work |
| --- | --- | --- | --- |
| EH-01 — artifact shape | Bounded assurance complete | Strict current-schema shape validation, fail-closed direct/JSON verification, stable blocking behavior, and a 26-case matrix spanning declared wire-field families plus supported legacy-schema rejection. | Extend only when a future schema adds a new required field family or legacy version. |
| EH-02 — delivered MIDI | Bounded assurance complete | Canonical SATB projection and independent `mido` parse-back include frozen cross-feature deliveries, exact event counts, articulation checks, and output digests. | Broaden delivery formats only through an explicit contract expansion. |
| EH-03 — request/provenance binding | Core repair complete | Independent request binding; contract/request/composition/artifact/output digests; exact evaluated-rule claims; display-claim checks; strict write-time verification. | Add authenticated signing only if authenticated origin becomes a product claim. |
| EH-04 — rule execution visibility | Core instrumentation complete | Versioned 57-rule inventory; typed `PASS`/`FAIL`/`NOT_APPLICABLE`/`BLOCKED` outcomes; predicate-level visitation; fail-closed `NOT_VISITED`; structured diagnostics; measured compiler-registration spans. | Compiler registrations are coverage evidence, not a proof of compiler/checker equivalence. |
| EH-05 — semantic interaction | Bounded interaction evidence complete | Typed semantic dispatch is reconstruction-derived; frozen full-piece controls cover modulation/modal mixture, modulation/secondary harmony, and modal mixture/secondary harmony with corresponding rejected faults. | Add new interaction families only when the musical contract expands. |
| EH-06 — checker isolation | Operational boundary complete | Checker/certifier imports and runs without OR-Tools; solver loading is lazy; generation dependencies are optional; isolation is tested. | Further split shared result types only if a stronger implementation-independence claim is required. |
| EH-07 — independent oracles | Bounded oracle evidence complete | Standard-library-only oracles retain bounded partitions and adjudicate frozen cross-feature control/fault pairs; manifests pin oracle/implementation hashes. | Oracle changes require new hashes and fresh evidence replay. |
| EH-08 — compiler deletion | Bounded deletion evidence complete | Named clause-deletion experiments span secondary-seventh, harmony, and rhythm compiler regions; exposed witnesses are rejected by checker/finalizer and applicable independent oracles. | This is bounded named-clause evidence, not global equivalence. |
| EH-09 — adversarial corruption | Bounded corpus complete | The original corruption benchmark and consolidated multi-fixture corpus retain stable case identities, expected outcomes, exact denominators, crashes, and exclusions. | Finite corpora do not establish population-level robustness. |
| EH-10 — comparative assurance | Comparative evidence complete | Leave-one-channel-out assurance ablations and exact-version music21 predicate adapters are checked in with raw rows, denominators, exclusions, dependency identity, and implementation hashes. | Broader independent tools/domains are required before general equivalence or superiority claims. |
| EH-11 — performance | Recorded finite performance evidence | Controlled feature/bar/seed/worker matrices preserve raw attempts, exclusions, timings, memory, certification overhead, and run provenance. | Re-run on owned quiescent hardware with broader budgets before capacity or latency-SLO claims. |
| EH-12 — release assurance | Bounded engineering claim complete | Machine-validated closure matrix plus one fail-closed aggregate gate covering exact dependency pins, lint/types/tests/builds, solver-free checking, deterministic evidence replay, evidence hashes, frozen claim state, and exact clean Git commit/tree attestation. | Research novelty, venue suitability, authenticated origin, global equivalence, population robustness, comparative superiority, and operational guarantees remain explicit non-claims. |

## Aggregate release gate

The repository-authored release-assurance command is:

```bash
python -m research.validate_release_assurance
```

It includes the ordinary implementation gates:

```bash
python -m ruff check src tests research
python -m mypy src
python -m pytest -q
python -m build
```

CI executes the aggregate gate across Python 3.11, 3.12, and 3.13. Separate CI steps replay preserved cross-system research histories at the source snapshots where those historical gates were last green, while the current v3 study is replayed on the current line.

## Retained bounded evidence

The current evidence packages include, among other finite domains:

- schema-shape and legacy-artifact rejection cases;
- exact MIDI delivery controls;
- independent local semantic oracles;
- named compiler-clause deletions;
- cross-feature control/fault pairs;
- a 30-attack corruption benchmark plus valid controls;
- multi-fixture assurance cases;
- music21 scope-normalized predicate comparisons;
- a controlled performance matrix with raw attempt provenance.

Exact counts, hashes, claim wording, and acceptance criteria remain in the frozen EH-12 documents and machine-readable research manifests. Those evidence records are intentionally not rewritten into product marketing claims.

See [EH-12 Closure Matrix](EH12_CLOSURE_MATRIX.md), [EH-12 Assurance Corpus](EH12_ASSURANCE_CORPUS.md), [Reproducibility](REPRODUCIBILITY.md), and [`research/`](../research/README.md).

## Claim boundary

Constraint Music 2.13 has a strong application-level verification and evidence boundary, but the repository does **not** claim:

- formal verification of OR-Tools, Python, or the host environment;
- global compiler/checker equivalence;
- universal musical soundness;
- aesthetic quality or historical authenticity;
- population-level adversarial robustness;
- general comparative superiority;
- operational capacity or latency guarantees;
- research novelty or publication acceptance.

Those stronger claims require independently scoped evidence beyond the bounded engineering assurance summarized here.
