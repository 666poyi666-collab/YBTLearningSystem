#!/usr/bin/env python3
"""Contract tests for the persistent chapter learner validator."""

from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_ROOT))

INIT_SPEC = importlib.util.spec_from_file_location(
    "ybt_progress_init", SCRIPT_ROOT / "init_chapter_learning_progress.py"
)
VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "ybt_progress_validator", SCRIPT_ROOT / "validate_chapter_learning_progress.py"
)
assert INIT_SPEC and INIT_SPEC.loader and VALIDATOR_SPEC and VALIDATOR_SPEC.loader
INIT = importlib.util.module_from_spec(INIT_SPEC)
VALIDATOR = importlib.util.module_from_spec(VALIDATOR_SPEC)
INIT_SPEC.loader.exec_module(INIT)
VALIDATOR_SPEC.loader.exec_module(VALIDATOR)


class ChapterLearningProgressTests(unittest.TestCase):
    ROOT = SCRIPT_ROOT.parents[2]

    @classmethod
    def setUpClass(cls) -> None:
        cls.progress = INIT.build_initial_progress(cls.ROOT, 1)

    def test_initial_chapter_progress_passes(self) -> None:
        self.assertEqual([], VALIDATOR.validate_progress(self.ROOT, copy.deepcopy(self.progress)))

    def test_completed_course_requires_consumption_evidence(self) -> None:
        progress = copy.deepcopy(self.progress)
        progress["course_ledger"]["records"][0]["status"] = "simulated_completed"
        errors = VALIDATOR.validate_progress(self.ROOT, progress)
        self.assertTrue(any("completed without evidence" in error for error in errors))

    def test_profile_change_requires_frozen_attempt_evidence(self) -> None:
        progress = copy.deepcopy(self.progress)
        progress["learner"]["profile_version"] = 2
        progress["learner"]["profile_history"].append({
            "version": 2,
            "reason": "observed new blocker",
            "evidence": [],
        })
        progress["sections"][-1]["profile_version_after"] = 2
        errors = VALIDATOR.validate_progress(self.ROOT, progress)
        self.assertTrue(any("changes profile without evidence" in error for error in errors))

    def test_required_course_set_is_project_derived(self) -> None:
        progress = copy.deepcopy(self.progress)
        progress["course_ledger"]["required_course_keys"] = progress["course_ledger"]["required_course_keys"][:-1]
        errors = VALIDATOR.validate_progress(self.ROOT, progress)
        self.assertTrue(any("required course order or coverage is stale" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
