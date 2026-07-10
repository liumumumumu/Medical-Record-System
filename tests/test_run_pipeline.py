from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from run_pipeline import run_pipeline


class RunPipelineTest(unittest.TestCase):
    def test_run_pipeline_executes_steps_in_dependency_order(self):
        calls = []

        def fake_runner(command, cwd, check):
            calls.append((Path(command[1]).name, Path(cwd).name, check))

        run_pipeline(runner=fake_runner)

        self.assertEqual(
            [call[0] for call in calls],
            [
                "merge_nhanes.py",
                "standardize_nhanes.py",
                "analyze_data_quality.py",
                "create_analysis_subsets.py",
                "validate_outputs.py",
            ],
        )
        self.assertTrue(all(call[1] == "Medical-Record-System" for call in calls))
        self.assertTrue(all(call[2] is True for call in calls))


if __name__ == "__main__":
    unittest.main()
