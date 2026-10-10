# Targeted contribution preflight (9 October 2026 UTC)

This is a claim-level comparison for manuscript framing, not a proof of global
novelty or submission readiness. The full 109-page [Pisters thesis](https://pure.tue.nl/ws/portalfiles/portal/47041658/631686-1.pdf)
was inspected, including its Exercise record (printed pp. 32–33), checker
(pp. 57–70), requirements evaluation (pp. 71–72), and conclusions (pp. 73–74).
The older portal file URL returned HTTP 403; the TU/e Pure PDF above is accessible.
The two IJCAI proceedings papers and Dai et al.'s preprint were also inspected.

## Pisters full-text comparison

Pisters (2007) specifies both generation and checking of tonal four-part harmony
exercises for a didactic tool. Its `Exercise` record includes the given soprano or
bass, voices, key, meter, figured sequence, cadence and other exercise metadata,
as well as arrays of possible figuring symbols, outer-voice notes, and chord-tone
duplications (Chapter 4). `CheckHarmony` takes a completed `Exercise` and
successively calls analysis/checking for figuring, outer voices, and inner voices
(§6.1). The figuring checker analyzes the given voice and recomputes candidate
figuring/probabilities before checking the selected figure and rules (§6.2).
The outer-voice checker analyzes the given voice and figuring and checks allowed
pitches and voice leading (§6.3). The inner-voice checker derives allowed
duplications from figuring/outer voices, then checks chord tones, duplication,
and voice leading (§6.4). It records positioned errors and warnings, with strict
versus soft rules (§§2.2, 7.2). Thus **fresh tonal analysis of a completed score,
reconstructed candidate obligations, checking, and separation of generation and
checking are prior work**. The thesis is an algorithm specification with a
proposed Finale plug-in; Chapter 7 evaluates requirements of an eventual system,
not a multi-fixture corruption study of deployed outputs.

The inspected thesis does not specify an independently supplied, immutable
request checked against a separate untrusted serialized result, nor does it
specify parsing a delivered Standard MIDI File and comparing its exact timed,
voiced events and declared context with the result. It does use MIDI *note
numbers* in musical predicates (Appendix A), so saying it has “no MIDI” would
be wrong. These are documented-scope distinctions, not a claim that no other
prior work has those mechanisms. Its exercise and rule vocabulary also differs
from the repository's versioned contract; rule coverage is not directly
equivalent.

## Contribution matrix

| Work | Request or task binding | Reconstructed tonal obligations | Relation to delivered MIDI | What it pre-empts / comparison limit |
| --- | --- | --- | --- | --- |
| [Pisters (2007)](https://pure.tue.nl/ws/portalfiles/portal/47041658/631686-1.pdf), Chs. 4, 6–8 | Checks a completed `Exercise` containing given voice, key, meter, metadata, and figuring; no separately trusted request-versus-result check is specified. | **Yes.** Reanalyzes given voice and figuring, constructs allowed figures/notes/duplications, applies rule predicates, and logs errors/warnings. | Uses MIDI pitch numbers in predicates; no exported-file parse-back or exact delivered-event relation is specified. | Checking, tonal reconstruction, staged generation/checking and flexible strict/soft rules are prior art. It is a specification, not an implemented fault-detection baseline. |
| [Diatony, IJCAI 2024](https://www.ijcai.org/proceedings/2024/0858.pdf), §§1, 3–4 | Takes composer-supplied chord names/constraints for a Gecode voicing model. | Formal diatonic four-voice constraints are enforced during search; the paper does not describe post-serialization reconstruction of the repository's contract. | Exports solutions as MIDI (§3.5); exact parse-back against an independently reconstructed projection is not described. | SATB constraint modeling, user control, and MIDI export are prior art. A solver's internal satisfaction is a different assurance boundary from certifying a returned artifact. |
| [Harmoniser, IJCAI 2025](https://www.ijcai.org/proceedings/2025/1130.pdf), §§1–4 | Models chord progressions and modulation with composer control. | Formal harmonic planning and modulation build on the Diatony voicing layer; no repository-style artifact reconstruction is reported. | No exact delivered-MIDI parse-back relation is reported in the inspected paper. | Chromatic harmony and modulation are prior art; the paper is not a scope-matched assurance evaluation. |
| [Dai et al. (2026), arXiv:2607.11334](https://arxiv.org/pdf/2607.11334), §§3.5, 5, App. B | Compiles a brief into a structured specification/blueprint; final release check can be schedule-relaxed, with stored-blueprint agreement separately reported. This is already a form of task/blueprint checking. | Final checker rescans retained twelve-tone events; this is a different musical contract, with independent collision/serialization checks and abstention. | Checks consistency among retained event, MIDI-pitch and trace fields, including pitch class and metadata; this is **not** a parsed, externally delivered SMF note/timing/context comparison as defined here. | Generate–verify–repair, independent final checks, output consistency, yield/abstention, and adversarial evaluation are prior art. Do not claim those ideas as new or compare success rates across tasks. |
| [This repository, PR37](../src/constraint_music/certification.py), [boundary](ASSURANCE_BOUNDARY.md), [evaluation](MULTIFIXTURE_ASSURANCE_EVALUATION.md) | `verify_artifact`/`certify_delivery` take a separately supplied `expected_spec`, require canonical equality with the current artifact spec, current contract/digests, and fresh claim equality. The embedded-spec `verify` command alone does **not** establish this boundary. | Deserializes and checks the current artifact; a fresh semantic report is compared with serialized claims, including applicable/blocked rules and harmonic obligations. This is a bounded implementation, not a new principle of tonal checking. | Under two declared certified render profiles, projects exact voice/channel/pitch/onset/duration plus key, meter, tempo and tick division; reparses the actual delivered MIDI and requires equality. The legacy preview is excluded. | Candidate contribution is the **conjunction** of three explicit boundaries and its fixed-corpus fault evaluation, not any one ingredient or global first-of-kind novelty. |

“Not described” in a paper is not evidence that the mechanism never existed
elsewhere. The matrix distinguishes the reported mechanisms and trust boundaries;
it does not rank musical quality or claim equivalent rule coverage.

## Smallest defensible contribution and verdict

Proposed manuscript claim: **For a finite, versioned tonal SATB contract, an
independently fixed request can be checked against a reconstructed serialized
artifact and its exact delivered MIDI projection; a fixed multi-composition fault
study measures where this conjunction rejects or blocks specified corruptions.**
This is an engineering assurance and evaluation claim. It should acknowledge
Pisters' reconstruction-based checking and Dai et al.'s output consistency and
selective delivery directly. Do not call the checker, reconstructed obligations,
MIDI export, verification-guided generation, or delivery checking alone novel.

The [fixed study](MULTIFIXTURE_ASSURANCE_EVALUATION.md) has 16 generated fixtures
(4 development, 12 held-out), 32 accepted untouched controls, and 456 held-out
fault slots. Of 332 applicable faults, 284 were rejected and 48 were blocked at
wire admission, with none accepted in this corpus; 124 slots were inapplicable.
The denominator is 12 held-out fixture clusters for illustrative uncertainty,
not 332 independent samples. The study supports this bounded fault-detection
claim but does not establish a population rate, global verifier completeness,
comparative superiority, or novelty against all literature. Chromatic/contextual
held-out fixtures are short C/G-major cases, and the Git bundle preserves local
protocol history without externally timestamped preregistration. The proprietary
license requires written permission for outside execution, limiting independent
replay as presently distributed.

**Verdict:** Pisters full-text comparison is complete; the earlier unresolved
source gate is closed. GO for a carefully bounded manuscript draft and for
claiming the evaluated conjunction as this repository's contribution. HOLD on
“first,” “novel verifier,” broad SOTA, and submission-ready novelty until a
wider targeted prior-art search and an independently runnable comparison or
reproduction route are completed.
