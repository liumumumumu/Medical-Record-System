from pathlib import Path
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from preprocess import CaseValidationError, load_resources, standardize_case


class PreprocessCaseTest(unittest.TestCase):
    def write_resources(self, directory: Path) -> None:
        (directory / "symptom_dict.txt").write_text(
            "发热\n咳嗽\n乏力\n腹泻\n咽痛\n胸闷\n气促\n", encoding="utf-8"
        )
        (directory / "medical_terms.txt").write_text(
            "上呼吸道感染\n白细胞\n血常规\n肺炎\n急性胃肠炎\n高血压\n糖尿病\n", encoding="utf-8"
        )
        (directory / "stopwords.txt").write_text("的\n了\n和\n以及\n", encoding="utf-8")
        (directory / "synonyms.json").write_text(
            json.dumps({"发烧": "发热", "拉肚子": "腹泻"}, ensure_ascii=False),
            encoding="utf-8",
        )

    def test_standardize_case_maps_frontend_fields_and_extracts_tokens(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            resource_dir = Path(temp_dir)
            self.write_resources(resource_dir)
            resources = load_resources(resource_dir)

            raw_case = {
                "patientName": "张某",
                "gender": "male",
                "age": "32",
                "department": "internal",
                "visitDate": "2026-07-10",
                "chiefComplaint": "<b>发烧、咳嗽 3 天!!!</b>",
                "presentIllness": "3天前受凉后出现发烧、咳嗽、乏力。",
                "pastHistory": "无高血压、糖尿病史。",
                "allergyHistory": "青霉素过敏",
                "vitalSigns": "体温 38.5℃，脉搏 88 次/分",
                "physicalExam": "咽部充血。",
                "auxiliaryExam": "血常规提示白细胞轻度升高。",
                "preliminaryDiagnosis": "上呼吸道感染",
                "treatmentTaken": "已给予退热处理",
                "medicationUsage": "口服对乙酰氨基酚",
                "generationNeeds": ["record", "symptom", "diagnosis"],
                "attachments": [
                    {
                        "fileName": "blood-test.pdf",
                        "mimeType": "application/pdf",
                        "parseStatus": "parsed",
                        "extractedText": "白细胞轻度升高",
                    }
                ],
            }

            result = standardize_case(raw_case, resources=resources)

            self.assertEqual(result["patient_name"], "张某")
            self.assertEqual(result["gender"], "male")
            self.assertEqual(result["age"], 32)
            self.assertEqual(result["chief_complaint"], "发热、咳嗽 3 天!")
            self.assertEqual(result["present_illness"], "3天前受凉后出现发热、咳嗽、乏力。")
            self.assertEqual(result["generation_needs"], ["record", "symptom", "diagnosis"])
            self.assertEqual(result["attachments"][0]["file_name"], "blood-test.pdf")
            self.assertEqual(result["attachments"][0]["parse_status"], "parsed")
            self.assertIn("发热", result["tokens"])
            self.assertIn("咳嗽", result["tokens"])
            self.assertIn("白细胞", result["tokens"])
            self.assertNotIn("上呼吸道感染", result["medical_terms"])
            self.assertNotIn("气促", result["symptoms"])
            self.assertNotIn("高血压", result["medical_terms"])
            self.assertNotIn("糖尿病", result["medical_terms"])
            self.assertNotIn("发烧", result["clean_text"])
            self.assertNotIn("上呼吸道感染", result["clean_text"])
            self.assertNotIn("退热处理", result["clean_text"])
            self.assertNotIn("对乙酰氨基酚", result["clean_text"])

    def test_standardize_case_reports_frontend_field_errors(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            resource_dir = Path(temp_dir)
            self.write_resources(resource_dir)
            resources = load_resources(resource_dir)

            raw_case = {
                "patientName": "张某",
                "gender": "unknown",
                "age": 131,
                "presentIllness": "发热咳嗽。",
                "pastHistory": "无",
            }

            with self.assertRaises(CaseValidationError) as context:
                standardize_case(raw_case, resources=resources)

            self.assertEqual(context.exception.code, "VALIDATION_ERROR")
            self.assertIn("gender", context.exception.field_errors)
            self.assertIn("age", context.exception.field_errors)
            self.assertIn("chiefComplaint", context.exception.field_errors)

    def test_standardize_case_defaults_optional_fields_and_attachment_failure(self):
        raw_case = {
            "patientName": "李某",
            "gender": "female",
            "age": 28,
            "chiefComplaint": "腹痛、拉肚子 1 天",
            "presentIllness": "进食后腹痛伴拉肚子。",
            "pastHistory": "无",
            "attachments": [
                {
                    "fileName": "blurred-photo.jpg",
                    "mimeType": "image/jpeg",
                    "parseStatus": "failed",
                    "failureReason": "图片模糊，无法识别文字",
                }
            ],
        }

        result = standardize_case(raw_case)

        self.assertEqual(result["department"], "other")
        self.assertEqual(result["allergy_history"], "无")
        self.assertEqual(result["generation_needs"], ["record", "symptom", "diagnosis"])
        self.assertEqual(result["attachments"][0]["parse_status"], "failed")
        self.assertEqual(result["attachments"][0]["failure_reason"], "图片模糊，无法识别文字")
        self.assertIn("腹泻", result["clean_text"])

    def test_standardize_case_accepts_frontend_attachment_string(self):
        raw_case = {
            "patientName": "赵某",
            "gender": "male",
            "age": 40,
            "chiefComplaint": "发热、咳嗽 2 天",
            "presentIllness": "受凉后出现发热和咳嗽。",
            "pastHistory": "无",
            "attachments": "blood-test.pdf / chest-xray.png",
        }

        result = standardize_case(raw_case)

        self.assertEqual(
            [attachment["file_name"] for attachment in result["attachments"]],
            ["blood-test.pdf", "chest-xray.png"],
        )
        self.assertTrue(
            all(
                attachment["parse_status"] == "pending"
                for attachment in result["attachments"]
            )
        )


if __name__ == "__main__":
    unittest.main()
