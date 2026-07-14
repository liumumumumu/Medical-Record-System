from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from validate_outputs import validate_outputs


class ValidateOutputsTest(unittest.TestCase):
    def test_validate_outputs_accepts_expected_shapes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            processed_dir = Path(temp_dir)
            expected_shapes = {
                "table_a.csv": (2, 2),
                "table_b.csv": (1, 3),
            }
            pd.DataFrame({"a": [1, 2], "b": [3, 4]}).to_csv(processed_dir / "table_a.csv", index=False)
            pd.DataFrame({"a": [1], "b": [2], "c": [3]}).to_csv(processed_dir / "table_b.csv", index=False)

            summary = validate_outputs(processed_dir=processed_dir, expected_shapes=expected_shapes)

            self.assertEqual(summary.shape, (2, 4))
            self.assertTrue(summary["passed"].all())

    def test_validate_outputs_raises_for_shape_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            processed_dir = Path(temp_dir)
            pd.DataFrame({"a": [1, 2]}).to_csv(processed_dir / "table_a.csv", index=False)

            with self.assertRaises(ValueError):
                validate_outputs(processed_dir=processed_dir, expected_shapes={"table_a.csv": (3, 1)})


if __name__ == "__main__":
    unittest.main()
