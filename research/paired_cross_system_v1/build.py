"""Build the new request-parameterized capture harness against pinned clean Diatony."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from research.cross_system_assurance_v1.build_diatony import PIN


def build(source: Path, output: Path, prefix: Path) -> None:
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip() != PIN:
        raise ValueError("wrong upstream pin")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=source, text=True).strip():
        raise ValueError("dirty upstream source")
    lib = prefix / "usr/lib/x86_64-linux-gnu"
    files = sorted((source / "c++/src").glob("*/*.cpp"))
    command = [
        "g++",
        "-std=c++11",
        "-O2",
        "-include",
        "chrono",
        f"-I{source / 'c++/headers'}",
        f"-I{prefix / 'usr/include'}",
        f"-L{lib}",
        "-Wl,--disable-new-dtags",
        f"-Wl,-rpath,{lib}",
        str(Path(__file__).with_name("diatony_probe.cpp")),
        *map(str, files),
        "-lgecodeint",
        "-lgecodekernel",
        "-lgecodeminimodel",
        "-lgecodesearch",
        "-lgecodesupport",
        "-o",
        str(output),
    ]
    subprocess.run(command, check=True, timeout=180)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("prefix", type=Path)
    args = parser.parse_args()
    build(args.source.resolve(), args.output.resolve(), args.prefix.resolve())
