"""Bounded, reproducible enumeration for the independent seventh oracle."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from itertools import permutations
from pathlib import Path

from .compiler_faults import generator_boundary_fault_report
from .differential_check import bounded_conformance_report
from .oracle.secondary_seventh import (
    SeventhQuality,
    adjudicate_secondary_seventh,
    secondary_seventh_pitch_classes,
)


def enumerate_pitch_class_domain() -> dict[str, object]:
    visited = 0
    accepted = 0
    rejected = 0
    first_rejection: dict[str, object] | None = None
    for tonic in range(12):
        for mode in ("major", "minor"):
            scale = (0, 2, 4, 5, 7, 9, 11) if mode == "major" else (0, 2, 3, 5, 7, 8, 11)
            for target_degree in range(1, 7):
                target = (tonic + scale[target_degree]) % 12
                for quality in SeventhQuality:
                    expected = secondary_seventh_pitch_classes(target, quality)
                    eligible = not (
                        mode == "minor" and quality is SeventhQuality.HALF_DIMINISHED
                    )
                    for inversion in range(4):
                        for realized in permutations(expected):
                            voices = (
                                realized[0] + 60,
                                realized[1] + 60,
                                realized[2] + 48,
                                realized[3] + 36,
                            )
                            decision = adjudicate_secondary_seventh(
                                voices,
                                target_pitch_class=target,
                                quality=quality,
                                inversion=inversion,
                                half_diminished_eligible=eligible,
                            )
                            visited += 1
                            if decision.valid:
                                accepted += 1
                            else:
                                rejected += 1
                                if first_rejection is None:
                                    first_rejection = {
                                        "tonic": tonic,
                                        "mode": mode,
                                        "target_degree": target_degree,
                                        "quality": quality.value,
                                        "inversion": inversion,
                                        "voices": voices,
                                        "decision": asdict(decision),
                                    }
    return {
        "domain": (
            "12 tonics x 2 modes x degrees 1..6 x 2 qualities x "
            "4 inversions x 24 permutations"
        ),
        "visited": visited,
        "accepted": accepted,
        "rejected": rejected,
        "first_rejection": first_rejection,
    }


def enumerate_all_domains() -> dict[str, object]:
    """Return separately named finite partitions without inflating their scope."""

    return {
        "schema_version": 4,
        "pitch_class_relation": enumerate_pitch_class_domain(),
        "bounded_conformance": bounded_conformance_report(),
        "generator_boundary_faults": generator_boundary_fault_report(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = enumerate_all_domains()
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
