from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import Any

CONTRACT_VERSION = "2.13"


class RuleStatus(StrEnum):
    """Outcome of one rule in the executable contract ledger."""

    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class RuleOutcome:
    rule_id: str
    status: RuleStatus
    diagnostic_codes: tuple[str, ...] = ()
    rationale: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "status": self.status.value,
            "diagnostic_codes": list(self.diagnostic_codes),
            "rationale": self.rationale,
        }

    @classmethod
    def from_mapping(cls, value: Any) -> RuleOutcome:
        if not isinstance(value, dict):
            raise ValueError("rule outcome must be an object")
        rule_id = value.get("rule_id")
        status = value.get("status")
        codes = value.get("diagnostic_codes", ())
        rationale = value.get("rationale", "")
        if not isinstance(rule_id, str) or not isinstance(status, str):
            raise ValueError("rule outcome requires string rule_id/status")
        if not isinstance(codes, list) or not all(isinstance(item, str) for item in codes):
            raise ValueError("rule outcome diagnostic_codes must be a string array")
        if not isinstance(rationale, str):
            raise ValueError("rule outcome rationale must be a string")
        return cls(rule_id, RuleStatus(status), tuple(codes), rationale)


@dataclass(frozen=True, slots=True)
class ConstraintRule:
    rule_id: str
    name: str
    description: str
    conditional: bool = False


HARD_CONSTRAINTS: tuple[ConstraintRule, ...] = (
    ConstraintRule(
        "CM001", "shape", "Melody, rhythm, bass, and harmony lengths match the specification."
    ),
    ConstraintRule(
        "CM002",
        "melody_domain",
        (
            "Every melody pitch is in the active key and inside the configured range, except an "
            "exactly reconstructed strong-beat secondary leading-tone seventh may carry one of "
            "its certified chromatic chord tones."
        ),
    ),
    ConstraintRule(
        "CM003",
        "bass_domain",
        (
            "Every bass pitch is in the active key and inside the configured range, except an "
            "exactly reconstructed secondary leading-tone seventh may carry its certified "
            "chromatic inversion tone."
        ),
    ),
    ConstraintRule(
        "CM004", "harmony_domain", "Every chord degree is a valid diatonic degree in 0..6."
    ),
    ConstraintRule(
        "CM005",
        "strong_beat_chord_tone",
        (
            "Every strong-beat melody pitch belongs to the active support triad or, for an exact "
            "certified secondary leading-tone seventh, to the realized target-derived seventh."
        ),
    ),
    ConstraintRule(
        "CM006",
        "bass_chord_member",
        (
            "Every bass pitch belongs to the active support triad or, for an exact certified "
            "secondary leading-tone seventh, to the realized target-derived seventh."
        ),
    ),
    ConstraintRule(
        "CM007",
        "progression_graph",
        "Every adjacent chord transition is allowed by the configured graph.",
    ),
    ConstraintRule(
        "CM008", "melody_leap", "Adjacent melody motion stays within the configured leap bound."
    ),
    ConstraintRule("CM009", "melody_tritone", "Adjacent melody motion never forms a tritone."),
    ConstraintRule(
        "CM010",
        "leading_tone_resolution",
        "When enabled, a melodic leading tone resolves upward by semitone.",
        conditional=True,
    ),
    ConstraintRule(
        "CM011", "melody_repetition", "Repeated-note runs do not exceed the configured limit."
    ),
    ConstraintRule(
        "CM012",
        "large_leap_recovery",
        "A melodic leap larger than a perfect fifth is followed by contrary stepwise motion.",
    ),
    ConstraintRule(
        "CM013", "bass_leap", "Adjacent bass motion stays within the configured leap bound."
    ),
    ConstraintRule("CM014", "bass_tritone", "Adjacent bass motion never forms a tritone."),
    ConstraintRule(
        "CM015",
        "parallel_perfects",
        "When enabled, outer voices avoid parallel perfect fifths and octaves.",
        conditional=True,
    ),
    ConstraintRule(
        "CM016",
        "legacy_whole_piece_closure",
        (
            "When enabled, the piece opens on tonic and closes dominant-function to tonic "
            "with tonic outer voices."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM017",
        "rhythm_domain",
        "Every melody grid step is explicitly classified as onset, tie, or rest.",
    ),
    ConstraintRule(
        "CM018",
        "rhythm_grammar",
        "Ties extend a sounding note, preserve pitch, and tie/rest runs stay within bounds.",
        conditional=True,
    ),
    ConstraintRule(
        "CM019",
        "rhythm_bar_density",
        (
            "When rhythm generation is enabled, each bar satisfies onset/rest/tie density "
            "and downbeat rules."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM020",
        "motif_relation",
        (
            "When configured, a target motif repeats or transposes the source motif exactly, "
            "including rhythm."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM021",
        "cadential_articulation",
        "The legacy whole-piece closure ends on a newly articulated tonic melody onset.",
        conditional=True,
    ),
    ConstraintRule(
        "CM022",
        "phrase_boundary",
        "Declared phrase spans are in bounds, uniquely identified, and pairwise non-overlapping.",
        conditional=True,
    ),
    ConstraintRule(
        "CM023",
        "phrase_role",
        (
            "Antecedent, consequent, and cadential roles impose explicit opening/closing "
            "harmonic semantics."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM024",
        "phrase_relation",
        (
            "Repeat, transpose, answer, and sequence relations reconstruct target melodic/rhythmic "
            "material exactly from their declared source."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM025",
        "phrase_cadence",
        (
            "Phrase cadence labels impose their exact tonic-close, dominant-open, "
            "dominant-to-tonic, or leading-tone-to-tonic semantics."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM026",
        "antecedent_consequent_structure",
        (
            "An answer-linked antecedent/consequent pair opens stably, leaves the antecedent open, "
            "recalls source material, and closes the consequent more strongly."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM027",
        "satb_shape",
        (
            "Solver-native SATB output contains one soprano, alto, and tenor note per beat "
            "and anchors soprano to the strong-step melody."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM028",
        "satb_ranges_order",
        (
            "SATB voices remain inside their ranges and maintain strict "
            "bass-tenor-alto-soprano ordering."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM029",
        "satb_spacing",
        "Adjacent upper SATB voices stay within octave spacing.",
        conditional=True,
    ),
    ConstraintRule(
        "CM030",
        "satb_chord_completeness",
        "Every SATB triad contains the complete active-key triad and doubles its root.",
        conditional=True,
    ),
    ConstraintRule(
        "CM031",
        "satb_inner_parallel_perfects",
        (
            "When enabled, voice pairs involving alto or tenor avoid parallel perfect fifths "
            "and octaves."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM032",
        "satb_tendency_resolution",
        "When enabled, alto and tenor active-key leading tones resolve upward by semitone.",
        conditional=True,
    ),
    ConstraintRule(
        "CM033",
        "harmonic_form_shape",
        (
            "When expanded harmonic-form metadata is present, chord kind and inversion arrays "
            "cover every beat and comply with the declared vocabulary/minimum seventh count."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM034",
        "expanded_chord_realization",
        (
            "Seventh forms contain all four active-key chord tones exactly once, while every "
            "serialized inversion agrees with the realized bass pitch class."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM035",
        "chordal_seventh_resolution",
        "Every diatonic chordal seventh has a following sonority and resolves downward by step.",
        conditional=True,
    ),
    ConstraintRule(
        "CM036",
        "dominant_seventh_resolution",
        (
            "Every active-key dominant seventh resolves to tonic and each voice carrying its "
            "leading tone resolves upward by semitone."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM037",
        "tonicization_context",
        (
            "When applied-dominant tonicization is enabled, only target-bearing sevenths whose "
            "active-key pitch content and support identity reconstruct exactly as applied V7/x "
            "count toward the declared minimum. Target-bearing triads remain governed by "
            "CM052-CM054; v2.12 secondary leading-tone sevenths by CM055-CM057."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM038",
        "applied_dominant_realization",
        (
            "Every seventh certified as an applied dominant has active-key target-derived "
            "dominant-seventh pitch classes exactly once, the correct root degree, and an "
            "inversion matching the bass."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM039",
        "applied_dominant_target_resolution",
        (
            "Every applied dominant resolves immediately to its declared untargeted diatonic "
            "local tonic."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM040",
        "applied_dominant_tendency_resolution",
        (
            "Each applied-dominant chordal seventh resolves downward by step and each voice "
            "carrying the local leading tone resolves upward by semitone."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM041",
        "modal_mixture_context",
        (
            "When modal mixture is enabled, every beat carries explicit nullable source-mode "
            "metadata; borrowed beats use the active-key canonical parallel source, do not "
            "coincide with local-target metadata, stay outside certified cadential/context "
            "anchors, and satisfy the declared minimum borrowed-chord count. Borrowed triads are "
            "certified by CM042; eligible borrowed sevenths by CM049-CM051."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM042",
        "borrowed_chord_realization",
        (
            "Every borrowed triad contains the complete triad derived from its explicit parallel "
            "source mode, active key, and degree, with inversion agreeing with realized bass."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM043",
        "key_context_shape",
        "Enabled modulation serializes exactly one explicit local-key identity per beat.",
        conditional=True,
    ),
    ConstraintRule(
        "CM044",
        "modulation_boundary_destination",
        "The single modulation boundary targets the declared same-mode dominant key.",
        conditional=True,
    ),
    ConstraintRule(
        "CM045",
        "modulation_pivot",
        (
            "The pre-boundary source-tonic triad is an unaltered common chord reinterpretable "
            "as destination IV."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM046",
        "post_modulation_interpretation",
        (
            "All post-boundary harmony is independently reconstructed against the persistent "
            "destination-key context."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM047",
        "destination_confirmation",
        (
            "The destination region closes with an unborrowed, untargeted destination V-I "
            "and destination-tonic outer voices."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM048",
        "serialized_key_context_consistency",
        (
            "Serialized key contexts equal the exact source-before/destination-after boundary "
            "sequence declared by the specification."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM049",
        "borrowed_seventh_context_eligibility",
        (
            "A source-bearing seventh requires expanded harmony and modal mixture, uses the "
            "active-key canonical parallel source and an explicitly supported degree, carries no "
            "local target, and stays outside certified modulation/cadence anchors."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM050",
        "borrowed_seventh_realization",
        (
            "Every eligible borrowed seventh contains all four pitch classes derived from its "
            "explicit source, active key, and degree exactly once, and its root/first/second "
            "inversion agrees with the realized bass."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM051",
        "borrowed_seventh_tendency_resolution",
        (
            "Every borrowed chordal seventh resolves downward by step; any admitted "
            "parallel-source leading tone carried by a SATB voice resolves upward by semitone."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM052",
        "secondary_leading_tone_context",
        (
            "Every target-bearing triad used as a secondary leading-tone chord declares a "
            "supported non-tonic active-key target, uses its deterministic CM005/CM006 support "
            "degree, does not overlap modal borrowing, and stays outside certified anchors."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM053",
        "secondary_leading_tone_realization",
        (
            "Every secondary leading-tone chord is the complete target-derived diminished triad, "
            "with local leading tone and diminished fifth undoubled, stable third doubled, and "
            "serialized inversion matching the realized bass."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM054",
        "secondary_leading_tone_resolution",
        (
            "Every secondary leading-tone chord resolves immediately to its declared unaltered "
            "triadic target; each local leading tone rises by semitone and each diminished fifth "
            "resolves downward by step."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM055",
        "secondary_leading_tone_seventh_context",
        (
            "Every v2.12 target-bearing secondary leading-tone seventh declares a supported "
            "non-tonic target in the exact active local key, uses its deterministic progression "
            "support degree, does not overlap modal borrowing or applied-dominant identity, and "
            "stays outside certified cadence/modulation anchors. Fully diminished quality is "
            "eligible for major and minor targets; half-diminished quality only for major targets."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM056",
        "secondary_leading_tone_seventh_realization",
        (
            "Every certified secondary leading-tone seventh contains exactly once the four "
            "target-derived pitch classes of its independently reconstructed fully diminished or "
            "eligible half-diminished quality. Root, first, second, and third inversions are "
            "admitted and the serialized inversion must match the realized bass."
        ),
        conditional=True,
    ),
    ConstraintRule(
        "CM057",
        "secondary_leading_tone_seventh_resolution",
        (
            "Every certified secondary leading-tone seventh resolves immediately to its declared "
            "untargeted, unborrowed triadic target. The local leading tone rises by semitone; the "
            "diminished fifth descends by the exact target-quality step; the chordal seventh "
            "descends by the exact quality-dependent step, including when carried by the bass in "
            "third inversion."
        ),
        conditional=True,
    ),
)

HARD_CONSTRAINT_IDS: tuple[str, ...] = tuple(rule.rule_id for rule in HARD_CONSTRAINTS)


def rule_applicability(rule_id: str, spec: Any) -> tuple[bool, str]:
    """Return the contract applicability decision without executing the predicate."""

    number = int(rule_id[2:])
    if (number <= 17 and number not in {10, 15, 16}) or number in {27, 28, 29, 30, 33}:
        return True, "mandatory for the current SATB certification profile"
    if number == 10:
        enabled = bool(spec.resolve_leading_tone)
        return enabled, "melodic leading-tone resolution is enabled" if enabled else "rule disabled"
    if number == 15:
        enabled = bool(spec.avoid_parallel_perfects)
        return enabled, "parallel-perfect avoidance is enabled" if enabled else "rule disabled"
    if number == 16:
        enabled = bool(spec.require_authentic_cadence)
        return enabled, "whole-piece closure is required" if enabled else "closure is disabled"
    if number in {18, 19}:
        enabled = bool(spec.rhythm_enabled)
        return enabled, "rhythm generation is enabled" if enabled else "rhythm feature is disabled"
    if number == 20:
        enabled = spec.motif_relation != "none"
        rationale = "a motif relation is declared" if enabled else "no motif relation is declared"
        return enabled, rationale
    if number == 21:
        enabled = bool(spec.require_authentic_cadence)
        rationale = (
            "cadential closure is required" if enabled else "cadential closure is disabled"
        )
        return enabled, rationale
    if 22 <= number <= 26:
        enabled = bool(spec.phrases)
        return enabled, "phrases are declared" if enabled else "no phrase grammar is declared"
    if number == 31:
        enabled = bool(spec.avoid_parallel_perfects)
        return enabled, "parallel-perfect avoidance is enabled" if enabled else "rule disabled"
    if number == 32:
        enabled = bool(spec.resolve_leading_tone)
        return enabled, "leading-tone resolution is enabled" if enabled else "rule disabled"
    if 34 <= number <= 36:
        enabled = bool(spec.expanded_harmony_enabled)
        return enabled, "expanded harmony is enabled" if enabled else "triad-only vocabulary"
    if 37 <= number <= 40:
        enabled = bool(spec.tonicization_enabled)
        return enabled, "tonicization is enabled" if enabled else "tonicization is disabled"
    if 41 <= number <= 42:
        enabled = bool(spec.modal_mixture_enabled)
        return enabled, "modal mixture is enabled" if enabled else "modal mixture is disabled"
    if 43 <= number <= 48:
        enabled = bool(spec.modulation_enabled)
        return enabled, "modulation is enabled" if enabled else "modulation is disabled"
    if 49 <= number <= 51:
        enabled = bool(
            spec.modal_mixture_enabled
            and spec.expanded_harmony_enabled
        )
        return enabled, (
            "borrowed sevenths are in scope" if enabled else "borrowed sevenths are out of scope"
        )
    if 52 <= number <= 54:
        enabled = bool(spec.secondary_leading_tone_enabled)
        return enabled, (
            "secondary leading-tone triads are enabled"
            if enabled
            else "secondary leading-tone triads are disabled"
        )
    if 55 <= number <= 57:
        enabled = bool(spec.secondary_leading_tone_seventh_enabled)
        return enabled, (
            "secondary leading-tone sevenths are enabled"
            if enabled
            else "secondary leading-tone sevenths are disabled"
        )
    raise ValueError(f"Unknown contract rule {rule_id!r}")


def build_rule_outcomes(
    spec: Any,
    failed_rules: tuple[str, ...],
    *,
    blocked_rules: tuple[str, ...] = (),
) -> tuple[RuleOutcome, ...]:
    failed = set(failed_rules)
    blocked = set(blocked_rules)
    outcomes: list[RuleOutcome] = []
    for rule_id in HARD_CONSTRAINT_IDS:
        applicable, rationale = rule_applicability(rule_id, spec)
        if rule_id in failed:
            status = RuleStatus.FAIL
        elif rule_id in blocked:
            status = RuleStatus.BLOCKED
        elif applicable:
            status = RuleStatus.PASS
        else:
            status = RuleStatus.NOT_APPLICABLE
        codes = (f"{rule_id}.FAILED",) if status is RuleStatus.FAIL else ()
        outcomes.append(RuleOutcome(rule_id, status, codes, rationale))
    return tuple(outcomes)


def contract_payload() -> dict[str, object]:
    return {
        "version": CONTRACT_VERSION,
        "hard_constraints": [
            {
                "id": rule.rule_id,
                "name": rule.name,
                "description": rule.description,
                "conditional": rule.conditional,
                "applicability": _applicability_label(rule.rule_id),
            }
            for rule in HARD_CONSTRAINTS
        ],
    }


def contract_digest() -> str:
    canonical = json.dumps(contract_payload(), sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def _applicability_label(rule_id: str) -> str:
    number = int(rule_id[2:])
    if (number <= 17 and number not in {10, 15, 16}) or number in {27, 28, 29, 30, 33}:
        return "always"
    if number == 10:
        return "resolve_leading_tone"
    if number == 15:
        return "avoid_parallel_perfects"
    if number == 16:
        return "require_authentic_cadence"
    if number in {18, 19}:
        return "rhythm_enabled"
    if number == 20:
        return "motif_relation != none"
    if number == 21:
        return "require_authentic_cadence"
    if 22 <= number <= 26:
        return "phrases declared"
    if number == 31:
        return "avoid_parallel_perfects"
    if number == 32:
        return "resolve_leading_tone"
    if 34 <= number <= 36:
        return "expanded_harmony_enabled"
    if 37 <= number <= 40:
        return "tonicization_enabled"
    if 41 <= number <= 42:
        return "modal_mixture_enabled"
    if 43 <= number <= 48:
        return "modulation_enabled"
    if 49 <= number <= 51:
        return "modal_mixture_enabled and expanded_harmony_enabled"
    if 52 <= number <= 54:
        return "secondary_leading_tone_enabled"
    return "secondary_leading_tone_seventh_enabled"
