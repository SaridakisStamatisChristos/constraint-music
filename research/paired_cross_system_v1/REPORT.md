# Paired cross-system conformance v1: derived report

This report is derived from independently replayed archived bytes. It measures the declared major-triad request subset; it does not rank musical quality, optimization, or general generator reliability.

## Planned and observed units

Development: 12 attempts. Held out: 48 attempts, including 36 primary attempts on 12 paired requests in two new harmonic families, and 12 explicitly unsupported attempts.

## Boundary transitions

Every row starts from 12 primary requests. Later funnel stages require all preceding stages. Independent delivery counts below test byte fidelity even when harmony fails.

| System | Planned | Output | Request bound | Semantic artifact | Full delivered | Native full |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| constraint-music | 12 | 12 | 12 | 12 | 12 | 12 |
| music21 | 12 | 12 | 12 | 11 | 11 | 11 |
| diatony | 12 | 12 | 12 | 12 | 12 | 0 |

Diatony's full delivered endpoint uses its separately declared renderer; its untouched native bytes remain archived and evaluated separately. Quarter-note rearticulations from Constraint Music are retained; whole notes from the other systems are retained. No attack coalescing is permitted.

## Natural outcomes and costs

| System | Generation | End-to-end | Independent delivery pass | Native delivery | Wall min/median/max (s) | Output max-process RSS min/median/max (KiB) |
| --- | --- | --- | ---: | --- | --- | --- |
| constraint-music | {'OUTPUT': 12} | {'PASS': 12} | 12 | {'PASS': 12} | 0.466788/0.5455665000000001/0.63242 (n=12) | 101996/104434.0/108988 (n=12) |
| music21 | {'OUTPUT': 12} | {'PASS': 11, 'REJECT': 1} | 12 | {'PASS': 12} | 0.354599/0.3951605/0.455869 (n=12) | 51768/52048.0/52244 (n=12) |
| diatony | {'OUTPUT': 12} | {'PASS': 12} | 12 | {'UNOBSERVABLE': 12} | 0.071434/0.08070250000000001/0.12011 (n=12) | 17536/17720.0/18040 (n=12) |

Costs include cold-process import and generation/export work under a common 30-second outer cap. Constraint Music/Gecode also have 20-second native clocks; music21 has no comparable native clock. RSS is the largest individual worker/child process observation, not summed concurrent pipeline memory. Internal rules, registers, rhythms, solver strategies and instrumentation differ; costs are descriptive, not a speed ranking.

## Paired end-to-end outcomes

| Left minus right | Pairs | Both pass | Left only | Right only | Neither | Difference | Two-family resample range |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| constraint-music minus music21 | 12 | 11 | 1 | 0 | 0 | 0.08333333333333333 | [0, 0.16666666666666666] |
| constraint-music minus diatony | 12 | 12 | 0 | 0 | 0 | 0 | [0, 0] |
| music21 minus diatony | 12 | 11 | 0 | 1 | 0 | -0.08333333333333333 | [-0.16666666666666666, 0] |

The four ordered family-cluster resamples are fully enumerated in summary.json. With only two purposively chosen families their ranges are illustrative, not inferential confidence intervals. Mutations share baselines and do not supply independent statistical samples.

## Injected faults

| System | Planned | Applicable | Statuses | First failing boundaries | PPQN controls |
| --- | ---: | ---: | --- | --- | --- |
| constraint-music | 144 | 144 | {'BLOCKED': 12, 'REJECT': 132} | {'artifact': 48, 'delivery': 60, 'request': 36} | {'PASS': 12} |
| music21 | 144 | 132 | {'BLOCKED': 11, 'INAPPLICABLE': 12, 'REJECT': 121} | {'artifact': 44, 'delivery': 55, 'request': 33} | {'INAPPLICABLE': 1, 'PASS': 11} |
| diatony | 144 | 144 | {'BLOCKED': 12, 'REJECT': 132} | {'artifact': 48, 'delivery': 60, 'request': 36} | {'PASS': 12} |

| Fault | Constraint Music | music21 | Diatony |
| --- | --- | --- | --- |
| request_key | {'REJECT': 12} | {'INAPPLICABLE': 1, 'REJECT': 11} | {'REJECT': 12} |
| request_tempo | {'REJECT': 12} | {'INAPPLICABLE': 1, 'REJECT': 11} | {'REJECT': 12} |
| coordinated_request | {'REJECT': 12} | {'INAPPLICABLE': 1, 'REJECT': 11} | {'REJECT': 12} |
| chromatic_pitch | {'REJECT': 12} | {'INAPPLICABLE': 1, 'REJECT': 11} | {'REJECT': 12} |
| missing_triad | {'REJECT': 12} | {'INAPPLICABLE': 1, 'REJECT': 11} | {'REJECT': 12} |
| crossing | {'REJECT': 12} | {'INAPPLICABLE': 1, 'REJECT': 11} | {'REJECT': 12} |
| artifact_duration | {'REJECT': 12} | {'INAPPLICABLE': 1, 'REJECT': 11} | {'REJECT': 12} |
| midi_pitch | {'REJECT': 12} | {'INAPPLICABLE': 1, 'REJECT': 11} | {'REJECT': 12} |
| midi_duration | {'REJECT': 12} | {'INAPPLICABLE': 1, 'REJECT': 11} | {'REJECT': 12} |
| midi_channel | {'REJECT': 12} | {'INAPPLICABLE': 1, 'REJECT': 11} | {'REJECT': 12} |
| midi_tempo | {'REJECT': 12} | {'INAPPLICABLE': 1, 'REJECT': 11} | {'REJECT': 12} |
| midi_truncated | {'BLOCKED': 12} | {'BLOCKED': 11, 'INAPPLICABLE': 1} | {'BLOCKED': 12} |

Total fault accounting: {'planned': 432, 'applicable': 420, 'statuses': {'BLOCKED': 35, 'INAPPLICABLE': 12, 'REJECT': 385}, 'false_accepts': 0}. Inapplicable slots retain their baseline IDs and reasons; malformed MIDI is blocked and is not relabeled as semantic rejection.

Known-valid controls: {'hand_planned': 8, 'hand_pass': 8, 'ppqn_applicable': 35, 'ppqn_pass': 35, 'known_valid_false_rejections': 0}. These are false-rejection observations on the declared controls, not an estimate for arbitrary valid music.

## Traceable natural discrepancies

- `heldout.extended-submediant.Eb.music21`: generation=OUTPUT; evaluation={'boundary': 'artifact', 'issues': ['TRIAD_COMPLETENESS_OR_CONTENT'], 'status': 'REJECT'}. Native and normalized bytes/logs: `heldout/evidence.zip`, members under `attempts/heldout.extended-submediant.Eb.music21/`.

## Gates and limits

Machine-derived gates: `{'complete_paired_collection': True, 'semantic_reference_agreement': True, 'positive_controls_pass': True, 'no_injected_false_accepts': True, 'outside_independent_replication_completed': False, 'public_research_run_permission_granted': False}`.

The protocol/source/corpus/budgets/faults were committed before held-out collection, with original Git history retained. This is a local prospective freeze, not externally timestamped preregistration. Six held-out keys and 4/6-chord requests broaden the earlier C/G pilot; minor, rest, tie and given-voice requests are explicitly unsupported. Shared obligations are a narrow intersection and native systems retain extra restrictions. Both semantic implementations may share conceptual mistakes; two MIDI parsers can share format assumptions. No human aesthetic evaluation, global novelty proof, outside replication or population reliability guarantee is claimed.

The proprietary license is unchanged. Outside research execution requires case-by-case written permission; the replay procedure and permission template make that route reviewable without granting rights automatically.
