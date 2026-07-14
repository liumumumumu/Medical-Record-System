from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

try:
    from output_io import write_csv, write_json
except ModuleNotFoundError:
    write_csv = None
    write_json = None


class OutputIoTest(unittest.TestCase):
    def test_write_csv_uses_lf_only(self):
        self.assertIsNotNone(write_csv, "output_io.write_csv should exist")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "table.csv"
            write_csv(pd.DataFrame({"a": [1], "b": [2]}), output_file, index=False)

            content = output_file.read_bytes()

            self.assertIn(b"\n", content)
            self.assertNotIn(b"\r\n", content)

    def test_write_json_uses_lf_only(self):
        self.assertIsNotNone(write_json, "output_io.write_json should exist")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "payload.json"
            write_json({"text": "发热\n咳嗽"}, output_file)

            content = output_file.read_bytes()

            self.assertIn(b"\n", content)
            self.assertNotIn(b"\r\n", content)


if __name__ == "__main__":
    unittest.main()
