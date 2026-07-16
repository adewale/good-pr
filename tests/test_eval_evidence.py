from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_eval_evidence.py"
SPEC = importlib.util.spec_from_file_location("build_eval_evidence", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class EvalEvidenceTests(unittest.TestCase):
    def test_tree_hash_binds_paths_modes_and_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a.txt"
            first.write_text("alpha\n", encoding="utf-8")
            original = MODULE.hash_tree(root)
            first.write_text("beta\n", encoding="utf-8")
            self.assertNotEqual(original, MODULE.hash_tree(root))
            first.write_text("alpha\n", encoding="utf-8")
            nested = root / "nested"
            nested.mkdir()
            (nested / "a.txt").write_text("alpha\n", encoding="utf-8")
            self.assertNotEqual(original, MODULE.hash_tree(root))

    def test_focused_cases_match_shared_manifest(self) -> None:
        import json

        focused = json.loads((ROOT / "evals/visual-evidence-benchmark.json").read_text())
        shared = json.loads((ROOT / "evals/shared-benchmark.json").read_text())
        shared_by_id = {case["id"]: case for case in shared["cases"]}
        self.assertEqual(9, len(focused["cases"]))
        for case in focused["cases"]:
            self.assertEqual(case, shared_by_id[case["id"]])


if __name__ == "__main__":
    unittest.main()
