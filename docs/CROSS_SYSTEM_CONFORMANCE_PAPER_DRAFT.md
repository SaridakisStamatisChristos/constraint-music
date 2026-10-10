# Separating request, score, and delivered-file conformance in symbolic music generation

Author-review manuscript draft, 10 October 2026. This draft integrates two separately declared studies; it is not a submission or a claim of externally timestamped preregistration.

## Abstract

A symbolic-music generator can return internally consistent events while missing the requested task, or return a conforming score whose exported file loses information. We evaluate these boundaries separately using a trusted external request, reconstruction of returned score facts, and independent parsing of delivered MIDI. A first bounded Constraint Music study retains 16 fixtures, 32 accepted controls and 456 held-out fault slots. A second, prospectively frozen paired study evaluates Constraint Music, music21 and Diatony on 12 shared SATB requests in six new major keys and two held-out harmonic families, plus four unsupported request cases. All 36 primary attempts returned outputs; delivered end-to-end passes were 12/12, 11/12 and 12/12 respectively, with Diatony's latter endpoint explicitly adapted rather than native. One music21 adapter/native-path output failed the requested triad content while preserving its delivered notes exactly. Among 432 planned injected fault slots, 420 were applicable: 385 were rejected and 35 blocked, with zero accepted faults and 12 retained inapplicable slots. Eight hand-positive and 35 applicable time-division controls passed. These results support the declared finite conformance protocol and demonstrate the value of separate boundaries, without implying population reliability, musical quality, optimization quality or system superiority.

## 1. Introduction

Users can request a specific key, harmony, duration, voicing and delivery context. Meeting that request is a relation between the user's independently retained specification and the produced score. Agreement among fields inside a result is a weaker relation. Export introduces another boundary: a correct score can be delivered with altered pitch, duration, voice assignment or context. An evaluation that observes only a generator's internal validation flag cannot establish these relations.

We ask where an explicitly requested symbolic-music task fails: generation, request binding, semantic artifact or delivered MIDI. The contribution is an implemented conformance protocol that keeps these boundaries distinct, prospective cross-engine requests, independent semantic/SMF reconstruction and complete evidence accounting. The study is deliberately limited to a common SATB subset; a successful benchmark outcome is not a guarantee for arbitrary music.

The first study tests request-bound assurance within Constraint Music. The second adds two independent external generation engines under a new contract and corpus. They are presented as one paper with separate methods and denominators. Their results are neither pooled nor treated as independent draws from one population.

## 2. Related work and contribution boundary

Reconstruction and checking of tonal exercises already appear in Pisters' 2007 thesis; its full-text comparison is retained in [the contribution preflight](MULTIFIXTURE_CONTRIBUTION_PREFLIGHT.md). Constraint-based SATB modeling, composer control and MIDI export are established by [Diatony](https://www.ijcai.org/proceedings/2024/858). [Harmoniser](https://www.ijcai.org/proceedings/2025/1130) builds broader harmonic planning and modulation on the voicing layer. We use one pinned Diatony implementation, rather than counting project layers as independent engines.

[Dai et al.](https://arxiv.org/html/2607.11334v2) already use independent retained-event checks, serialization consistency and selective release in twelve-tone generation. [MusicConstraintBench/MusicRLVR](https://arxiv.org/html/2609.23665v2) already evaluates jointly requested, programmatically checked musical properties with malformed-score gating, controls, mutations and generalization splits in monophonic ABC. Harmony realization and chorale export are existing [music21](https://music21.org/music21docs/moduleReference/moduleFiguredBassRealizer.html) capabilities.

We therefore do not claim that tonal verification, joint constraint benchmarking, final checking, verifier-guided generation or MIDI export is new. The candidate distinction is the concrete conjunction of a separately fixed request, reconstructed polyphonic score facts, exact independently parsed delivered-SMF relations, and prospective complete-slot evidence across independent engines. The [updated claim matrix](CROSS_SYSTEM_CONTRIBUTION_UPDATE.md) documents overlap and limits. This focused review does not establish global priority, and cross-paper success percentages are not comparable across different musical contracts.

## 3. Assurance model

Let R be the independently fixed request, S the returned native score, A its normalized artifact, and M the actual delivered SMF bytes. Acceptance requires request admission and binding, equality of reconstructed S and A events, integrity admission, fresh semantic evaluation against R, and exact parsed MIDI projection against those events and R's context. A stored hash alone checks integrity; it does not establish harmony or request satisfaction.

Semantic reconstruction derives pitch classes, chord membership, voice order, coverage, harmonic transitions and cadence movement from events. Delivery reconstruction derives actual note pitch, onset and duration plus declared track/channel identity, key, meter and tempo. Parser disagreement or unavailable required evidence prevents acceptance. Unobservable native identity/context is recorded explicitly; it is not presumed correct.

The cumulative transition funnel counts output, request-bound output, semantic artifact and full delivered result from the same fixed attempt denominator. Independent stage outcomes additionally measure faithful delivery of a semantically wrong score. This distinction explains why an exact export can pass its own boundary while the whole request fails.

## 4. Study A: bounded request-bound assurance

The merged PR37 study retains its original frozen protocol, native observations, oracles, hashes and denominators. Its 16 fixtures comprise four development and twelve held-out requests. Its 32 controls passed. Of 456 held-out fault slots, 332 were applicable: 284 rejected and 48 blocked; 124 were inapplicable. These are finite observations under that study's eligibility conditions, not estimates of universal fault detection.

The executable strict API uses an externally supplied expected specification, rather than treating the embedded-spec inspection path as equivalent. Its artifact integrity and fresh semantic checks are paired with exact parsed-back MIDI projection under supported certified profiles. See [the original evaluation](MULTIFIXTURE_ASSURANCE_EVALUATION.md) and [assurance boundary](ASSURANCE_BOUNDARY.md) for its distinct contracts, partitions and claim limits. Study B does not modify or enlarge those counts.

## 5. Study B: prospective paired cross-system evaluation

### 5.1 Systems and common obligations

We pin Constraint Music core to `9de73eae948eac366e7e1a45047a970795ed76bf`, OR-Tools to 9.15.6755, music21 to 9.9.2, Diatony to `2b13446c117c02626659e819ff975fef4b5daec2`, Gecode to 6.2.0 and the secondary MIDI parser mido to 1.3.3. CP-SAT, native figured-bass realization and Gecode are independent generation implementations; two wrappers of one engine are not counted independently.

The shared request names a major key, zero-based degree sequence, 4/4 meter and tempo. Every chord occupies four quarters and must contain all three diatonic triad pitch classes with root bass. Four SATB voices continuously cover the phrase, remain noncrossing and keep stable pitches within harmonic blocks. Quarter or whole durations are allowed. Parallel octave/fifth movement in the same nonzero direction between blocks is forbidden; a leading tone on V must ascend one semitone on I. The contract does not imply every rule of tonal harmony.

Constraint Music's benchmark subclass posts degrees, root inversions, block constancy and cadence obligations before native CP-SAT search; its objective is cleared for first-feasible selection. music21 uses root bass MIDI 48+root pitch class, default native rules plus a benchmark consecutive-possibility cadence hook, and the first viable native movement-DAG path. Diatony uses a benchmark subclass posting complete triad presence and cadence obligations before first-feasible native DFS. Upstream source and core Constraint Music code are unchanged. The profiles retain additional native rules and registers, so shared-obligation conformance is comparable while internal optimization problems are not identical.

Quarter attacks from Constraint Music are retained; the other systems' whole notes are retained. They both satisfy the request's allowed durations but remain distinct delivery projections. music21 outputs native chorale MusicXML/MIDI with explicitly inserted request tempo. Diatony's original MIDI is preserved and separately evaluated; a declared benchmark renderer adds observable SATB identity and exact context to captured native events. Adapted Diatony success must not be attributed to untouched native export.

### 5.2 Split, budgets and development

Development comprises four C/G requests using I-IV-V-I or I-V-I. The primary holdout comprises twelve D/A/E/F/Bb/Eb requests using I-ii-V-I or I-vi-IV-ii-V-I. Both tonic keys and entire harmonic families differ between development and holdout. The two held-out strata have four and six chords. Tempos cycle through 90/108/132. Four additional cases explicitly request minor mode, rests, ties or a given voice; all three adapters declare these unsupported before attempting generation. Native broader capability is not inferred from adapter support.

Each attempt runs in a fresh sequential process group under the same 30-second wall cap; system order rotates by request. CP-SAT and Gecode also have 20-second native limits, while music21 has no equivalent native search clock. CP-SAT uses one worker and seed 7; numerical-library thread environments are capped at one. Costs include startup/import/export. Memory is maximum observed RSS of an individual worker/child process, not concurrent process sums. These measurements are descriptive.

The first development revision exposed native omissions/alternative cadence treatment. All original code and bytes are retained in `development_v0.zip`. Before freezing, explicit native conditioning was added without removing any shared obligation or calling the oracle to select/repair outputs. All twelve revised development attempts passed. Protocol, source, corpus, support, budgets, fault plan and analysis were committed at `167ed84`; the freeze receipt was committed at `ff15f25` before held-out collection. Original history is retained in a Git bundle. This is local prospective declaration, not externally timestamped preregistration. No adapter/oracle/protocol change followed held-out observation.

### 5.3 Oracles and evidence

Native JSON, MusicXML and text captures are independently reconstructed and compared with normalized events. Captured input mappings bind to the trusted request. One semantic implementation uses rational event coverage and scale-degree pitch classes; a separate matrix implementation uses occupancy and chord-quality interval tables. Neither uses a generator's reported validity or imports the other. Hand-positive, negative and metamorphic cases validate agreement. Disagreements block acceptance.

A handwritten SMF parser and mido independently reconstruct delivered bytes and must agree. Tracks 1–4 carry SATB; channels 0–3 apply to Constraint Music/adapted Diatony, and channel 0 on each voice track applies to music21. Key, meter and rounded microseconds-per-quarter tempo are exact at zero. Positive PPQN scaling with proportional ticks is permitted; velocity, program and track names are ignored. Repeated attacks are not coalesced. Malformed SMF is blocked, distinct from semantic rejection.

Every planned attempt retains its trusted request, actual native score/input/MIDI, adapted delivery where applicable, normalized artifact, available metrics and logs with explicit IDs and byte hashes. Unique IDs, exact planned sets, archive coverage, hashes, source reconstruction, both semantic implementations, both parsers, mutations and derived tables are replayed in CI. Unsupported/time-out/no-solution/harness/parse outcomes cannot silently disappear.

### 5.4 Faults, controls and analysis

Twelve predeclared slots per primary attempt give 432 fault slots. The faults change request key/tempo, coordinate a request/score/MIDI transpose, alter score pitch/completeness/crossing/duration with repaired hashes, or alter MIDI pitch/duration/channel/tempo/truncation. Faults are applicable only to untouched fully accepted baselines; a nonconforming baseline retains all its INAPPLICABLE slots. Each mutation must change actual data before observation.

One positive PPQN slot per primary attempt gives 36 planned slots with identical baseline eligibility. Eight hand-positive controls cover two keys, two development families and original/scaled PPQN. Report false rejection only for applicable known-valid controls. False acceptance is a PASS on an applicable injected fault; malformed-MIDI BLOCKED and semantic REJECT are reported separately.

Primary rates use twelve request clusters per system. Pair identical request identities; mutation outcomes do not become independent samples. For descriptive paired uncertainty, enumerate four ordered resamples of the two held-out harmonic-family clusters. Only two purposively selected families are available, so the resulting ranges are illustrative and are not inferential confidence intervals.

## 6. Results

### 6.1 Complete attempt accounting and transitions

All 48 held-out slots are retained: 36 primary OUTPUT and 12 UNSUPPORTED. No primary timeout, no-solution or harness-error outcome occurred in this run. Both semantic implementations agreed on all 36 primary outputs.

| System/profile | Primary planned | Output | Request bound | Semantic artifact | Full delivered | Observable native full |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Constraint Music conditioned/native export | 12 | 12 | 12 | 12 | 12 | 12 |
| music21 conditioned/native export | 12 | 12 | 12 | 11 | 11 | 11 |
| Diatony conditioned/adapted delivery | 12 | 12 | 12 | 12 | 12 | 0 |

All 36 delivered files pass the independent event/context relation. The music21 score failure therefore occurs at the semantic-artifact boundary. Diatony's twelve untouched native files have an observable correct unvoiced event relation but unobservable required voice identity/context; zero observable native full endpoints does not mean twelve demonstrated semantic failures.

### 6.2 Traceable discrepancy

`heldout.extended-submediant.Eb.music21` follows I-vi-IV-ii-V-I. Its third block, at quarter 8, contains SATB MIDI pitches 70/62/58/56, giving pitch classes {10,2,8}. The requested IV in Eb requires {8,0,3}. Both semantic implementations reject triad content/completeness while native reconstruction and delivered MIDI remain exact.

The preserved MusicXML spells the MIDI-56 bass as G-sharp. The adapter constructs bass notes from integer MIDI values; an enharmonic translation issue in this adapter/native realization path is consistent with the observed discrepancy. We do not attribute a general defect to music21 or claim causality established by a repair experiment. No held-out-informed spelling repair was performed. A revised spelling policy needs a new declaration and fresh holdout. The row, native XML and delivered SMF are linked in the archived evidence.

A coordinated request/score/MIDI mutation provides a separate boundary witness: internal consistency remains repaired, yet the result no longer matches the externally retained request. A truncated-MIDI witness demonstrates why admission failures must block acceptance without claiming that a particular harmony rule diagnosed them. All witness bytes and verdicts are linked by baseline IDs.

### 6.3 Faults and known-valid controls

| System | Planned faults | Applicable | REJECT | BLOCKED | INAPPLICABLE | Accepted faults |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Constraint Music | 144 | 144 | 132 | 12 | 0 | 0 |
| music21 | 144 | 132 | 121 | 11 | 12 | 0 |
| Diatony adapted delivery | 144 | 144 | 132 | 12 | 0 | 0 |
| Total | 432 | 420 | 385 | 35 | 12 | 0 |

Truncation accounts for the 35 BLOCKED outcomes; all other applicable injected faults are REJECT. Request faults fail the trusted request boundary, repaired score faults fail semantic artifact checks, and MIDI-only faults fail delivery. The one naturally rejected music21 baseline accounts for twelve inapplicable faults and one inapplicable PPQN control; it is not silently removed from primary request yield.

All eight hand controls and 35 applicable PPQN controls pass: zero observed false rejections among 43 declared valid controls. This finite count does not estimate false rejection for arbitrary valid music.

### 6.4 Pairing and descriptive costs

| Left minus right | Request pairs | Both pass | Left only | Right only | Difference | Illustrative two-family resample range |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Constraint Music minus music21 | 12 | 11 | 1 | 0 | 1/12 | 0 to 1/6 |
| Constraint Music minus adapted Diatony | 12 | 12 | 0 | 0 | 0 | 0 to 0 |
| music21 minus adapted Diatony | 12 | 11 | 0 | 1 | -1/12 | -1/6 to 0 |

The sample is too small and too selected to infer relative generator reliability. Native-rule differences, adapter conditioning and one translation discrepancy further qualify interpretation. A zero resample range is not proof of a zero population difference.

| System | Primary wall min/median/max, seconds | Output max-process RSS min/median/max, KiB |
| --- | --- | --- |
| Constraint Music | 0.467 / 0.546 / 0.632 | 101996 / 104434 / 108988 |
| music21 | 0.355 / 0.395 / 0.456 | 51768 / 52048 / 52244 |
| Diatony | 0.071 / 0.081 / 0.120 | 17536 / 17720 / 18040 |

Each cost distribution has twelve observations from this Linux runner; exact values are in the machine-derived report. Different registers, internal constraints, algorithms, note rhythms and clocks prevent a speed-superiority interpretation.

## 7. Threats to validity and release

The shared contract is a narrow major-triad intersection. Minor, rest, tie, fixed-voice and contextual chromatic tasks are unsupported, not covertly weakened or counted as generation failures. Six keys and two longer families broaden the earlier pilot but do not represent all tonal music. Oracle agreement cannot exclude shared conceptual errors, and independent parsers may share format assumptions. Native capture relies on declared pinned adapters; the evidence establishes observed relations, not authenticated origin or resistance to arbitrary malicious provenance fabrication.

Conditioning explicitly changes benchmark models before search; results characterize those profiles, not unrestricted default APIs. Diatony's adapted renderer guarantees observable information by construction, so its score-to-render byte relation is checked independently and native export remains separate. The music21 spelling discrepancy illustrates how an adapter can be part of the evaluated failure path. Natural failures are retained rather than fixed after inspection.

Faults are deterministic and correlated within accepted baselines. A zero accepted-fault count concerns those witnesses; the test set is not an adversarial completeness proof. BLOCKED outcomes prevent release but do not imply semantic fault localization. Positive controls have known constructed truth only within the supported domain. No listening study is needed for machine-checkable conformance, and none supports an aesthetic claim here.

The proprietary Constraint Music license remains unchanged. Public evidence can be inspected, but independent repository execution requires written permission. The [permission route/template](RESEARCH_REPLAY_PERMISSION_TEMPLATE.md) provides a reviewable case-by-case path; it does not issue an automatic public grant. External projects retain their licenses and no upstream code/binary is redistributed. Outside replication has not been conducted. The [replay README](../research/paired_cross_system_v1/README.md) supplies the exact archived-byte checks and a new-version generation procedure.

## 8. Conclusion

The two bounded studies provide concrete evidence for separately checking a trusted request, returned score facts and actual delivered MIDI. The paired extension retains every planned slot, a natural adapter/native-path discrepancy, explicit native unobservability and complete eligible-fault accounting. It supports the declared protocol on the sampled domain and makes its limits inspectable. Future work requires fresh held-out versions for spelling revisions and broader musical domains, explicit evaluator permissions and actual independent replication; it does not retroactively expand these results.

## References and evidence

Primary related-work links are given in section 2 and the claim matrix. Version-specific papers are Dai et al., arXiv:2607.11334v2 (14 July 2026), and Liu and Tang, arXiv:2609.23665v2 (7 October 2026). The retained full-text Pisters comparison and IJCAI papers establish the credited overlaps.

Study A: [MULTIFIXTURE_ASSURANCE_EVALUATION.md](MULTIFIXTURE_ASSURANCE_EVALUATION.md), original frozen corpus and PR37 history. Study B: [PROTOCOL.md](../research/paired_cross_system_v1/PROTOCOL.md), [manifest.json](../research/paired_cross_system_v1/manifest.json), [freeze.json](../research/paired_cross_system_v1/freeze.json), [REPORT.md](../research/paired_cross_system_v1/REPORT.md), [summary.json](../research/paired_cross_system_v1/summary.json), native/normalized byte archives and original-history bundle. The report generator recomputes tables from verified evidence rather than accepting handwritten totals.
