from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256

CONTRACT_VERSION = "2.4"


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
        "CM002", "melody_domain", "Every melody pitch is in-key and inside the configured range."
    ),
    ConstraintRule(
        "CM003", "bass_domain", "Every bass pitch is in-key and inside the configured range."
    ),
    ConstraintRule(
        "CM004", "harmony_domain", "Every chord degree is a valid diatonic degree in 0..6."
    ),
    ConstraintRule(
        "CM005",
        "strong_beat_chord_tone",
        "Every strong-beat melody pitch belongs to the active triad.",
    ),
    ConstraintRule("CM006", "bass_chord_member", "Every bass pitch belongs to the active triad."),
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
        "Solver-native SATB output contains one soprano, alto, and tenor note per beat and anchors soprano to the strong-step melody.",
        conditional=True,
    ),
    ConstraintRule(
        "CM028",
        "satb_ranges_order",
        "SATB voices remain inside their ranges and maintain strict bass-tenor-alto-soprano ordering.",
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
        "Every SATB sonority contains the complete active triad and doubles its root.",
        conditional=True,
    ),
    ConstraintRule(
        "CM031",
        "satb_inner_parallel_perfects",
        "When enabled, voice pairs involving alto or tenor avoid parallel perfect fifths and octaves.",
        conditional=True,
    ),
    ConstraintRule(
        "CM032",
        "satb_tendency_resolution",
        "When enabled, alto and tenor leading tones resolve upward by semitone.",
        conditional=True,
    ),
)

HARD_CONSTRAINT_IDS: tuple[str, ...] = tuple(rule.rule_id for rule in HARD_CONSTRAINTS)


def contract_payload() -> dict[str, object]:
    return {
        "version": CONTRACT_VERSION,
        "hard_constraints": [
            {
                "id": rule.rule_id,
                "name": rule.name,
                "description": rule.description,
                "conditional": rule.conditional,
            }
            for rule in HARD_CONSTRAINTS
        ],
    }


def contract_digest() -> str:
    canonical = json.dumps(contract_payload(), sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()
