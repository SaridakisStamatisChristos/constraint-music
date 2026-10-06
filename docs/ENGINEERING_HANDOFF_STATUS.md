# Engineering handoff implementation status

This document records the implementation state against
`Constraint_Music_Engineering_Handoff.md`. It deliberately distinguishes repaired
release behavior from unfinished research evidence. A passing build or CI run is
not a publication-readiness claim.

## Scope and baseline

- Upstream revision: `07c1e312bf40a9564ccc0e13384bcc4653e5eb03`
- Implemented package/schema/contract line: `2.13.0a1` / `2.13` / `2.13`
- Certification profile exercised: `certified-satb`
- Canonicalization profile: `constraint-music-json-v1`

## Work-package status

| Work package | Status | Implemented evidence | Remaining work |
| --- | --- | --- | --- |
| EH-01 | PR-34 assurance complete | Strict current-schema shape validation, fail-closed direct and JSON verification, stable `CM001` blocking, and a 26-case matrix covering every declared wire-field family plus strict rejection of supported legacy schema 2.12 without crashes. | Extend only when a future schema adds a new required field family or legacy version. |
| EH-02 | PR-34 assurance complete | Canonical SATB projection and independent `mido` parse-back now include four frozen cross-feature deliveries across both certified profiles, exact event counts, rhythm articulation, and output digests. | Broaden delivery formats only under an explicit contract expansion. |
| EH-03 | Core repair complete | Independent request binding, contract/request/composition/artifact/output digests, fresh validation comparison, exact evaluated-ID claims, display-claim checks, and strict write-time verification. | Add authenticated signing only if authenticated origin becomes a product claim. |
| EH-04 | Core instrumentation complete | Versioned 57-rule inventory; typed `PASS`/`FAIL`/`NOT_APPLICABLE`/`BLOCKED` ledger; predicate-level `visited` instrumentation; fail-closed `NOT_VISITED` outcomes; structured diagnostic code/rule/feature/location/voice fields; and measured per-compilation phase registrations with exact CP-SAT constraint spans. The historical compiled-ID alias has been replaced by a real registration catalogue. | Continue refining global runtime diagnostics to narrower beat/transition locations where useful; compiler registrations remain coverage evidence, not an equivalence proof. |
| EH-05 | PR-34 assurance complete | Typed semantic dispatch remains reconstruction-derived. Frozen full-piece controls cover modulation/modal mixture, modulation/secondary harmony, and modal mixture/secondary harmony on disjoint witness beats; all three targeted faults are rejected by their declared rule and independent local oracle. | Add new interaction families only when the musical contract expands. |
| EH-06 | Operational boundary complete | Checker/certifier imports and executes without OR-Tools; solver loading is lazy; generation dependencies are optional; isolation is tested. | Further split shared result types from mixed runtime modules if a stronger semantic-independence claim is desired. |
| EH-07 | PR-34 assurance complete | Standard-library-only oracles retain their exhaustive bounded partitions and now adjudicate three frozen full-piece interaction control/fault pairs. The manifest records human adjudication notes and the summary pins oracle/implementation hashes. | Changes to oracle sources require new hashes and a fresh evidence replay. |
| EH-08 | PR-34 assurance complete | Bounded partitions remain zero-disagreement. Named deletion evidence now removes `CM057`, `CM016`, and `CM018` clauses across secondary-seventh, harmony, and rhythm phases; every forced witness is rejected by the checker/finalizer, applicable independent oracles reject, and zero faults escape. | This remains bounded named-clause evidence, not global compiler/checker equivalence. |
| EH-09 | PR-34 assurance complete | The original 32-case benchmark remains intact. The consolidated corpus adds three distinct frozen specifications/seeds and retains 39 raw rows with stable fixture/case/cluster identities, expected outcomes, issues, exact denominators, crashes, and exclusions. | Neither finite corpus supports a population-level robustness claim. |
| EH-10 | Core comparative evidence complete | Research-only leave-one-channel-out signal ablations preserve all 32 EH-09 raw cases and reasons without adding production bypasses. The four overlapping channels retain 24/30, 25/30, 23/30, and 24/30 detections when wire-shape, semantic, integrity/request, and delivery signals are respectively omitted, with zero control flags. Exact-version music21 9.9.2 adapters explicitly normalize shared semantics and show zero disagreements on 9,840 bounded parallel-perfect cases and 126 bounded C-major triad-policy cases. Raw rows, exact denominators, exclusions, dependency identity, and implementation hashes are checked in and replayed in CI. | Expand to independently selected external tools and broader predeclared shared domains before making comparative-performance, general-equivalence, or superiority claims. |
| EH-11 | Core performance evidence complete | The controlled matrix records nine feature profiles at 1, 2, 4, 8, 16, and 32 bars across five fixed seeds and single/throughput worker modes on a pinned Python/OR-Tools environment. Raw rows preserve all 540 single-output attempts plus 18 multi-output throughput cases, including 40 declared scope exclusions, solver outcomes, timing decomposition, peak RSS, certification overhead, and run provenance. The checked-in report records 126 generated, strictly accepted, and released artifacts from 500 runnable single-output cases without converting timeouts into successes. | Re-run on owned, quiescent hardware with longer solve budgets and repeated independent runners before making capacity, latency-SLO, or cross-platform performance claims. |
| EH-12 | Consolidated assurance satisfied; closure partial | The closure matrix now marks all inherited EH-01–EH-11 residuals satisfied or explicitly deferred. CI replays the deterministic [39-case consolidated corpus](EH12_ASSURANCE_CORPUS.md) and rejects result/hash drift. | Publication gate remains HOLD until PR-35 and independent clean-checkout review satisfy `EH12-G03` and `EH12-G04`. |

## Verified release gates

The following commands passed in the implementation workspace:

```text
python -m ruff check src tests research
python -m mypy src
python -m pytest -q
python -m build
python -m constraint_music generate examples/four_bar_arch.yaml \
  --output e2e/piece.mid --json e2e/piece.json
python -m constraint_music certify e2e/piece.json \
  --spec examples/four_bar_arch.yaml --midi e2e/piece.mid \
  --certificate e2e/certificate.json
```

The end-to-end certification returned `PASS (EXTERNAL REQUEST + DELIVERY)` and
independently observed 64 delivery note events. The generated certificate records
all binding digests and the exact evaluated/not-applicable rule sets.

The full local suite contains 615 passing tests and reports 83.48% branch-aware
source coverage. The combined `melody-plus-satb` CLI round trip also passed with 96
independently observed note events. The current bounded evidence records 27,648
pitch-class cases (5,184 accepted and 22,464 rejected), 4,824 exact register cases
(1,233 accepted and 3,591 rejected), 680 context/anchor cases (83 accepted and 597
rejected), 540,000 resolution cases (4,320 accepted and 535,680 rejected), and 24
complete-verifier cases. The pinned generator-boundary matrix rejects all five injected
semantic/objective faults before return; the exact named compiler deletion and all five
cross-feature faults are also rejected with zero escapes. The full corruption benchmark
detects all 30 attacks, accepts both controls, and reports zero crashes across 15
split-isolated attack clusters; its cluster-level 95% Wilson interval is 0.796117–1.0.
The EH-10 signal ablation preserves full 30/30 union coverage and exposes 6, 5, 7, and
6 unique catches for wire-shape, semantic, integrity/request, and delivery channels.
The two scope-normalized music21 9.9.2 adapters agree on all 9,966 bounded shared cases.
The PR-34 consolidated corpus adjudicates all 39 cases: 26 schema blocks, three accepted
full-piece controls, three rejected interaction faults, four exact delivery controls, and
three rejected compiler deletions across distinct phases, with zero crashes or exclusions.
The EH-11 performance run records 540 attempts on an AMD EPYC 7763 runner: 40
declared exclusions, 500 runnable cases, and 126 generated artifacts that all passed
strict artifact certification and delivery verification. These are finite observations
from the recorded runner and solve budget, not capacity or latency guarantees.

## Claim boundary

The implementation repairs the demonstrated P0 artifact-shape, delivery, claim,
and external-request-binding defects. It provides substantial assurance
infrastructure, but it does **not** establish global musical soundness,
solver/checker equivalence, superiority to external systems, research novelty, or
publication readiness. Those stronger claims remain gated on the unfinished work
listed above. EH-12 closure status and normative acceptance criteria are tracked in
[`EH12_CLOSURE_MATRIX.md`](EH12_CLOSURE_MATRIX.md).
