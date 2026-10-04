from __future__ import annotations

import os
import subprocess
import sys


def test_checker_imports_without_ortools() -> None:
    script = r'''
import importlib.abc
import sys

class BlockOrtools(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname == "ortools" or fullname.startswith("ortools."):
            raise ModuleNotFoundError("blocked for checker-isolation test", name=fullname)
        return None

sys.meta_path.insert(0, BlockOrtools())
from constraint_music.certification import verify_artifact
from constraint_music.provenance import load_result_json
from constraint_music.delivery import verify_delivery
assert callable(verify_artifact)
assert callable(load_result_json)
assert callable(verify_delivery)
assert "constraint_music.solver" not in sys.modules
print("checker-only import: PASS")
'''
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(__file__), environment.get("PYTHONPATH", "")))
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert completed.returncode == 0, completed.stderr
    assert "PASS" in completed.stdout
