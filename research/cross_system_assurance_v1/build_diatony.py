"""Build the probe against an exact upstream checkout and local/system Gecode."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

PIN = "2b13446c117c02626659e819ff975fef4b5daec2"
ROOT = Path(__file__).resolve().parent


def build(source: Path, output: Path, prefix: Path | None = None) -> None:
    observed = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    if observed != PIN:
        raise ValueError(f"Diatony pin mismatch: {observed}")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=source, text=True).strip():
        raise ValueError("Diatony checkout must be unmodified")
    files = sorted((source / "c++/src").glob("*/*.cpp"))
    output.parent.mkdir(parents=True, exist_ok=True)
    # Upstream relies on a transitive chrono include available on macOS.
    command = ["g++", "-std=c++11", "-O2", "-include", "chrono", f"-I{source / 'c++/headers'}"]
    if prefix:
        lib = prefix / "usr/lib/x86_64-linux-gnu"
        command.extend(
            [
                f"-I{prefix / 'usr/include'}",
                f"-L{lib}",
                "-Wl,--disable-new-dtags",
                f"-Wl,-rpath,{lib}",
            ]
        )
    command.extend([str(ROOT / "diatony_probe.cpp"), *map(str, files)])
    command.extend(
        [
            "-lgecodeint",
            "-lgecodekernel",
            "-lgecodeminimodel",
            "-lgecodesearch",
            "-lgecodesupport",
            "-o",
            str(output),
        ]
    )
    subprocess.run(command, check=True, timeout=180)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--prefix", type=Path)
    args = parser.parse_args()
    build(
        args.source.resolve(), args.output.resolve(), args.prefix.resolve() if args.prefix else None
    )
