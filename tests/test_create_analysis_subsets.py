from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from create_analysis_subsets import build_subset, build_subset_summary


class CreateAnalysisSubsetsTest(unittest.TestCase):
    def test_build_subset_keeps_columns_and_drops_missing_required_values(self):
        df = pd.DataFrame(
            {
                "patient_id": [1, 2, 3],
                "age_years": [40, 50, 60],
                "bmi": [22.0, None, 31.0],
                "glucose_mg_dl": [90.0, 180.0, None],
                "hba1c_percent": [5.4, 8.1, 6.2],
                "unused": ["a", "b", "c"],
            }
        )

        subset = build_subset(
            df,
            columns=["patient_id", "age_years", "bmi", "glucose_mg_dl", "hba1c_percent"],
            required_columns=["bmi", "glucose_mg_dl"],
        )

        self.assertEqual(list(subset.columns), ["patient_id", "age_years", "bmi", "glucose_mg_dl", "hba1c_percent"])
        self.assertEqual(subset.shape, (1, 5))
        self.assertEqual(subset.iloc[0]["patient_id"], 1)

    def test_build_subset_summary_reports_rows_and_columns(self):
        subsets = {
            "diabetes": pd.DataFrame({"patient_id": [1, 2], "bmi": [22.0, 31.0]}),
            "kidney": pd.DataFrame({"patient_id": [1], "creatinine_mg_dl": [0.8]}),
        }

        summary = build_subset_summary(subsets)
        rows = {row["subset_name"]: row for row in summary.to_dict("records")}

        self.assertEqual(rows["diabetes"]["row_count"], 2)
        self.assertEqual(rows["diabetes"]["column_count"], 2)
        self.assertEqual(rows["kidney"]["row_count"], 1)
        self.assertEqual(rows["kidney"]["column_count"], 2)


if __name__ == "__main__":
    unittest.main()
