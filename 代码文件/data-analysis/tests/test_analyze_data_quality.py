from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from analyze_data_quality import build_outlier_summary, build_quality_summary


class AnalyzeDataQualityTest(unittest.TestCase):
    def test_build_quality_summary_reports_missing_and_numeric_stats(self):
        df = pd.DataFrame(
            {
                "patient_id": [1, 2, 3],
                "bmi": [22.0, None, 31.0],
                "gender": ["male", "female", None],
            }
        )

        summary = build_quality_summary(df)
        bmi = summary.loc[summary["column"] == "bmi"].iloc[0]
        gender = summary.loc[summary["column"] == "gender"].iloc[0]

        self.assertEqual(bmi["missing_count"], 1)
        self.assertEqual(bmi["missing_rate"], 0.3333)
        self.assertEqual(bmi["mean"], 26.5)
        self.assertEqual(bmi["min"], 22.0)
        self.assertEqual(bmi["max"], 31.0)
        self.assertEqual(gender["missing_count"], 1)
        self.assertTrue(pd.isna(gender["mean"]))

    def test_build_outlier_summary_counts_values_outside_expected_ranges(self):
        df = pd.DataFrame(
            {
                "bmi": [18.5, 60.0, 12.0, None],
                "systolic_bp_mean": [120.0, 260.0, 80.0, None],
                "glucose_mg_dl": [90.0, 500.0, 20.0, None],
            }
        )

        summary = build_outlier_summary(df)
        counts = dict(zip(summary["column"], summary["outlier_count"]))

        self.assertEqual(counts["bmi"], 2)
        self.assertEqual(counts["systolic_bp_mean"], 2)
        self.assertEqual(counts["glucose_mg_dl"], 2)


if __name__ == "__main__":
    unittest.main()
