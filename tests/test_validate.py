"""Regression tests: validate both the real baseline and intentionally broken copies."""
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("factory_validate", ROOT / "scripts" / "validate.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FactoryValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "factory"
        shutil.copytree(ROOT, self.root,
                        ignore=shutil.ignore_patterns(".git", ".obsidian", "__pycache__", ".local"))

    def mutate_json(self, relative, update):
        path = self.root / relative
        value = json.loads(path.read_text(encoding="utf-8"))
        update(value)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def check_failure(self, fragment):
        errors = MODULE.validate(self.root)
        self.assertTrue(any(fragment in item for item in errors), errors)

    def test_baseline_passes(self):
        self.assertEqual([], MODULE.validate(ROOT))

    def test_missing_local_link_is_reported(self):
        with (self.root / "Home.md").open("a", encoding="utf-8") as handle:
            handle.write("\n[missing](<absent.md>)\n")
        self.check_failure("Broken or out-of-root link")

    def test_unicode_space_link_and_external_url(self):
        (self.root / "中文 笔记.md").write_text("# 测试\n", encoding="utf-8")
        with (self.root / "Home.md").open("a", encoding="utf-8") as handle:
            handle.write("\n[笔记](<中文%20笔记.md>)\n[external](https://example.invalid/x)\n")
        self.assertEqual([], MODULE.validate(self.root))

    def test_out_of_root_link_is_rejected(self):
        (self.root.parent / "outside.md").write_text("outside", encoding="utf-8")
        with (self.root / "Home.md").open("a", encoding="utf-8") as handle:
            handle.write("\n[outside](<../outside.md>)\n")
        self.check_failure("Broken or out-of-root link")

    def test_version_drift_is_rejected(self):
        self.mutate_json("lines/app/pipeline.json", lambda value: value.update(version="9.0.0"))
        self.check_failure("Pipeline VERSION mismatch")

    def test_duplicate_node_is_rejected(self):
        self.mutate_json("lines/app/pipeline.json", lambda value: value["nodes"].append(value["nodes"][0]))
        self.check_failure("Invalid node IDs")

    def test_gate_at_wrong_node_is_rejected(self):
        self.mutate_json("lines/app/pipeline.json", lambda value: value["gates"][0].update(after="APP-01"))
        self.check_failure("Gate location mismatch")

    def test_unimplemented_game_cannot_claim_version(self):
        self.mutate_json("factory/production-lines.json", lambda value: value["lines"][1].update(version="0.1.0"))
        self.check_failure("Planned line must not claim")

    def test_malformed_json_fails_cleanly(self):
        (self.root / "factory/production-lines.json").write_text("{broken", encoding="utf-8")
        self.check_failure("Invalid JSON")

    def test_skill_metadata_is_required(self):
        path = self.root / ".dsh/skills/app-production-line/SKILL.md"
        path.write_text("# Missing metadata\n", encoding="utf-8")
        self.check_failure("Skill frontmatter missing")

    def test_automatic_approval_is_rejected(self):
        self.mutate_json("lines/app/pipeline.json", lambda value: value["gates"][0].update(approval="agent"))
        self.check_failure("Baseline gates require human approval")

    def test_unknown_successor_is_rejected(self):
        self.mutate_json("lines/app/pipeline.json", lambda value: value["nodes"][0].update(next=["APP-99"]))
        self.check_failure("Invalid next targets")


if __name__ == "__main__":
    unittest.main()
