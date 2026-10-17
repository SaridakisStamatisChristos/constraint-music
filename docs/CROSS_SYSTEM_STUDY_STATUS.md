# Cross-System Study Status

Status: 10 October 2026.

Constraint Music retains three distinct cross-system study lines rather than pooling their denominators or rewriting earlier outcomes. The studies evaluate finite, explicitly declared SATB conformance tasks and delivery endpoints. They do not establish general musical quality, research novelty, or unconditional system superiority.

## Study lineage

| Study component | Retained result | Boundary |
| --- | --- | --- |
| Primary-source contribution comparison | Focused claim matrix retained, including MusicConstraintBench v2 | Not exhaustive novelty clearance |
| Native-interface feasibility | Two external independent engines are executable within the inspected scope | Native Diatony identity/context remains partly unobservable |
| Shared contract and support matrix | Versioned requests, explicit support declarations, and native/adapted conditioning | The earliest shared grammar is intentionally narrow |
| Independent semantic/delivery oracles | Native-source reconstruction, separate scale/matrix semantics, handwritten SMF parser, and `mido` parse-back | Conceptual shared assumptions remain possible |
| Prospective protocol and holdout handling | Development/freeze commits precede collection; source hashes and Git bundles are retained | Local prospective history, not external preregistration |
| Paired collection and replay | Raw native/adapted outputs, faults, controls, hashes, reports, and replay tooling retained | Archive replay does not imply outside replication |
| Literature integration | Focused primary-source comparison and manuscript integration retained | No first-benchmark, aesthetic-quality, or universal-superiority claim |
| External replay route | Written-permission template and concrete replay instructions retained | Permission must be granted by the owner; the proprietary license is unchanged |

## Earlier bounded conformance study

The earlier finite-domain study remains unchanged in its archived protocol, observations, hashes, and denominators. It contains 16 fixtures, 32 accepted controls, and 456 held-out fault slots. Of 332 applicable fault slots, 284 were rejected and 48 were blocked; 124 were inapplicable.

The native/adapted feasibility work is preserved separately. Those pilot records are evidence about the declared interfaces and adapters, not a universal comparison of music-generation systems.

## Paired cross-system study v1

The first prospective paired study retains all 48 held-out attempt slots, including 36 outputs and 12 unsupported attempts. Its archive contains the actual native, delivered, and mutated bytes needed for replay.

The retained accounting is:

- 35/36 full delivered passes;
- 432 fault slots;
- 385 `REJECT` outcomes;
- 35 `BLOCKED` outcomes;
- 12 `INAPPLICABLE` outcomes;
- zero accepted faults;
- 43 applicable valid controls accepted.

A controlled replay later reproduced the study's music21 counterexample and showed that changing only the bass spelling from G-sharp to A-flat at unchanged MIDI 56 satisfied the declared obligations. That finding is retained as an adapter error for that case; the original v1 result is not rewritten.

See [`research/paired_cross_system_v1/`](../research/paired_cross_system_v1/).

## Fair paired comparison v2

V2 introduced explicit diatonic spelling, equal fixed bass inputs/ranges, inversions, dominant sevenths, and soprano anchors. Its primary endpoint uses the same adapted delivery form for all three engines while retaining native exports separately.

The completed study retains all 792 planned slots and reports reproducible adapted passes of:

- Constraint Music: **45/128**;
- music21: **113/128**;
- Diatony: **51/128**.

There were zero timeouts, harness errors, or inspection blocks in the retained study. The prespecified superiority gate failed: music21 completed more requests under that declared conditional grammar, while the Diatony comparison was inconclusive. That negative result is preserved in the manuscript rather than replaced by later engineering changes.

See the [v2 report](../research/paired_cross_system_v2/REPORT.md).

## Request-bound harmonization study v3

The opt-in [request-bound harmonization API](REQUEST_BOUND_HARMONIZATION.md) solves complete chord requests with all-voice pitch anchors and performs independent score/native-MIDI checking under a separate explicit contract. Legacy composition constraints and certificates remain separate.

All 128 archived v2 cases pass both seeds as development replay for the new API. Source and receipt commits precede the fresh v3 holdout. On the fresh paired corpus, reproducible native/adapted passes are:

- new request-bound Constraint Music: **128/128**;
- legacy Constraint Music configuration: **53/128**;
- music21: **111/128**;
- adapted Diatony: **38/128**.

All 1,056 planned slots and retained native/adapted artifacts replay without errors, blocks, or timeouts. Against music21, there are 17 Constraint-Music-only passes and no losses. The corrected exact paired p-value is **0.0000458** and the conservative simultaneous completion-difference interval is **[+2.34, +23.01] percentage points**.

This supports a positive completion difference on the declared grammar and configurations. The separately prespecified **+10-point minimum practical margin is not established against music21**. That threshold remains a frozen negative gate result and is not silently redefined after observing the data.

See the [v3 report](../research/paired_cross_system_v3/REPORT.md).

## Publication boundary

The integrated manuscript draft is [`CROSS_SYSTEM_CONFORMANCE_PAPER_DRAFT.md`](CROSS_SYSTEM_CONFORMANCE_PAPER_DRAFT.md). It keeps the finite-domain study, v1, v2, and v3 results separate and preserves the negative findings that motivated later work.

The repository does not claim that these studies establish:

- aesthetic quality;
- historical-style authenticity;
- universal SATB completeness;
- first use of constraint programming for harmony;
- general superiority over music21, Diatony, or other systems;
- independent external replication;
- journal or conference acceptance.

External execution remains subject to the proprietary license and the [research replay permission template](RESEARCH_REPLAY_PERMISSION_TEMPLATE.md).
