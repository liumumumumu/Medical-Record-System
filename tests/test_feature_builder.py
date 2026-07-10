from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from feature_builder import build_keyword_features


class FeatureBuilderTest(unittest.TestCase):
    def test_build_keyword_features_marks_terms_from_clean_text_and_tokens(self):
        cases = pd.DataFrame(
            [
                {
                    "case_id": "case_001",
                    "clean_text": "发热 咳嗽 白细胞 升高",
                    "tokens": "发热 咳嗽 白细胞",
                    "diagnosis_label": "上呼吸道感染",
                },
                {
                    "case_id": "case_002",
                    "clean_text": "腹痛 腹泻 恶心",
                    "tokens": "腹痛 腹泻",
                    "diagnosis_label": "急性胃肠炎",
                },
            ]
        )

        features = build_keyword_features(cases, keywords=["发热", "咳嗽", "腹泻", "白细胞"])

        self.assertEqual(
            list(features.columns),
            [
                "case_id",
                "kw_发热",
                "kw_咳嗽",
                "kw_腹泻",
                "kw_白细胞",
                "diagnosis_label",
            ],
        )
        self.assertEqual(features.loc[0, "kw_发热"], 1)
        self.assertEqual(features.loc[0, "kw_腹泻"], 0)
        self.assertEqual(features.loc[1, "kw_腹泻"], 1)
        self.assertEqual(features.loc[1, "diagnosis_label"], "急性胃肠炎")


if __name__ == "__main__":
    unittest.main()
