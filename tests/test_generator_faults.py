from __future__ import annotations

from research.compiler_faults import generator_boundary_fault_report


def test_pinned_generator_boundary_faults_all_fail_closed() -> None:
    report = generator_boundary_fault_report()

    assert report["schema_version"] == 1
    assert report["toolchain"]["ortools"] == "9.15.6755"
    assert report["toolchain"]["workers"] == 1
    assert set(report["implementation_hashes"]) == {
        "pyproject.toml",
        "research/compiler_faults.py",
        "src/constraint_music/solver.py",
    }
    assert all(
        len(digest) == 64 for digest in report["implementation_hashes"].values()
    )
    assert report["visited"] == 6
    assert report["escaped_faults"] == 0

    cases = report["cases"]
    assert cases["control"] == {
        "expected": "ACCEPT",
        "observed": "ACCEPT",
        "diagnostic": None,
    }
    for name in (
        "melody_domain",
        "target_metadata",
        "inversion_bass",
        "tendency_resolution",
    ):
        assert cases[name]["expected"] == "REJECT"
        assert cases[name]["observed"] == "REJECT"
        assert str(cases[name]["diagnostic"]).startswith(
            "Solver/verifier contract breach:"
        )
    assert cases["compiled_objective"] == {
        "expected": "REJECT",
        "observed": "REJECT",
        "diagnostic": (
            "Solver/objective-vector breach: compiled and independent objective vectors differ"
        ),
    }
