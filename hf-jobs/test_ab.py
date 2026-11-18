#!/usr/bin/env python3

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ab import job_spec  # noqa: E402
from ab_report import paired_ratios  # noqa: E402
from pin_pipeline import pin  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OLD = "76f57f25a39f139d92ae861db950b7830951e6d2"
NEW = "109a9970656d94a424893b356179ef3070bbb74b"


def cell(model, corpus, **mbps):
    return {
        "dataset_metadata": {"model": model, "corpus": corpus},
        "results": [
            {"tokenizer_name": name, "mbps": value, "verified": True}
            for name, value in mbps.items()
        ],
    }


class PinTests(unittest.TestCase):
    def test_every_pin_of_an_engine_moves_together(self):
        for name in ("Cargo.toml", "src/lib.rs"):
            text = (ROOT / "engines/pipeline-base" / name).read_text()
            pinned = pin(text, NEW, "someone/tokenizers")
            self.assertNotIn(OLD, pinned)
            self.assertNotIn(OLD[:8], pinned)
            self.assertNotIn("huggingface/tokenizers", pinned)
            self.assertEqual(pinned.count(NEW), text.count(OLD))


class ReportTests(unittest.TestCase):
    def test_ratio_is_paired_within_a_run(self):
        # Pooled medians are 200 against 200, a ratio of 1.0, although two
        # runs out of three measured 1.5 on their own host conditions.
        reports = [
            {"runs": [cell("gpt2", "english", **{"pipeline": 150.0, "pipeline-base": 100.0})]},
            {"runs": [cell("gpt2", "english", **{"pipeline": 300.0, "pipeline-base": 200.0})]},
            {"runs": [cell("gpt2", "english", **{"pipeline": 200.0, "pipeline-base": 400.0})]},
        ]
        ratios, _ = paired_ratios(reports, "pipeline", "pipeline-base")
        self.assertEqual(ratios[("gpt2", "english")], [1.5, 1.5, 0.5])

    def test_a_cell_whose_ids_differ_has_no_ratio(self):
        run = cell("gpt2", "english", **{"pipeline": 150.0, "pipeline-base": 100.0})
        run["results"][0]["verified"] = False
        ratios, excluded = paired_ratios([{"runs": [run]}], "pipeline", "pipeline-base")
        self.assertEqual(ratios, {})
        self.assertEqual(excluded, {("gpt2", "english")})


class JobSpecTests(unittest.TestCase):
    def test_job_measures_with_the_submitted_tokbench_commit(self):
        spec = job_spec(
            SimpleNamespace(
                tokbench_repo="someone/tokbench", models="gpt2", runs=3, reps=5,
                repo="huggingface/tokenizers",
            ),
            tokbench_rev="a" * 40, base=OLD, tip=NEW, input_rev="b" * 40, corpora_rev="c" * 40,
        )
        script = spec["command"][-1]
        self.assertIn("https://github.com/someone/tokbench.git", script)
        self.assertIn("git checkout -q --detach " + "a" * 40, script)
        self.assertEqual(spec["env"]["TOKBENCH_AB_BASE"], OLD)
        self.assertEqual(spec["env"]["TOKBENCH_AB_TIP"], NEW)


if __name__ == "__main__":
    unittest.main()
