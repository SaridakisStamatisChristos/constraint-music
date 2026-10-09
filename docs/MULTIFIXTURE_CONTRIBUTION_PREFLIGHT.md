# Targeted contribution preflight (9 October 2026 UTC)

This comparison informs the research framing; it does not clear novelty or certify
submission readiness. Primary proceedings texts were inspected for the two IJCAI
papers and the arXiv HTML/PDF for Dai et al. Pisters' university record was verified,
but its full-text endpoint returned HTTP 403. That full-text comparison remains open.

| Prior work | Mechanisms already established | Limit on the present contribution |
| --- | --- | --- |
| [Pisters (2007)](https://research.tue.nl/en/studentTheses/an-approach-to-automatic-generation-and-verification-of-solutions/), master's thesis | Its title explicitly covers generation and verification of tonal four-part harmony exercises. Internal mechanisms remain unverified here because full text was inaccessible. | Neither having a checker nor separating generation and verification supports novelty by itself. Obtain and inspect the thesis before asserting a mechanism absent there. |
| [Sprockeels and Van Roy, IJCAI 2024](https://www.ijcai.org/proceedings/2024/0858.pdf), Diatony | Formal tonal constraints, four-voice diatonic harmony, configurable preferences and Gecode search. Section 4 also describes exporting MIDI solutions. | SATB constraints, constraint solving, formal musical rules and MIDI export are prior art. |
| [Sprockeels and Van Roy, IJCAI 2025](https://www.ijcai.org/proceedings/2025/1130.pdf), Harmoniser | Models chord progressions, chromatic harmony and neighbouring-key modulation, building on the voicing layer in Diatony. | Modulation and chromatic/contextual features are not novelty claims for this repository. |
| [Dai et al. (2026), arXiv:2607.11334v1](https://arxiv.org/html/2607.11334v1) | A generate/verify/repair/trace pipeline, abstention, a separate collision and serialization checker, delivery yield, cost and adversarial evaluation. Appendix B distinguishes copy consistency among retained event, MIDI and trace fields from serial-row legality; it also discusses stored-blueprint agreement. | Verification-guided generation, independent checks, end-to-end delivery accounting, abstention and boundary comparisons are already represented. This is a twelve-tone LLM system, so its reported rates are not scope-normalized comparators for tonal CP-SAT certification. |

The smallest candidate contribution is a **reproducible assurance evaluation**:
strictly bind an independently fixed tonal request to a serialized SATB artifact,
reconstruct its protected musical and harmonic obligations, and compare the actual
delivered MIDI against an exact register/channel/onset/duration/context projection
under explicit render profiles. Report conditional fault detection across fixed
pieces, retained generation failures, independent finite-domain oracle agreement,
and overlapping boundary signals.

This is a proposed framing inferred from the implementation and the inspected
sources, not an established literature gap. Hashes, CP-SAT, a checker or MIDI do not
make it novel individually. The fixed 16-request study strengthens evidence for the
bounded engineering claim; it does not prove the claim has not appeared elsewhere.
A focused literature comparison and the Pisters full text remain required before
any submission-ready or first-of-its-kind assertion.
