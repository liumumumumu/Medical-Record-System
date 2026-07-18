"""Runtime acceptance for short colloquial front-end fields.

This complements corpus metrics: every case must stay on the Transformer path,
preserve explicit facts, and remove the listed colloquial expressions.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from time import perf_counter


AI_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AI_ROOT))

os.environ.setdefault("RECORD_GENERATOR_BACKEND", "transformer")
os.environ.setdefault("REQUIRE_RECORD_GENERATOR", "true")
os.environ.setdefault("RECORD_GENERATOR_BEAMS", "4")

from src.config import RECORD_MODEL_VERSION  # noqa: E402
from src.record_generator import RecordGenerator  # noqa: E402
from src.schema import PatientInput  # noqa: E402


CASES = (
    {
        "name": "成人胃肠口语",
        "patient": PatientInput(
            name="验收甲",
            gender="男",
            age=24,
            department="internal",
            chief_complaint="肚子疼还拉肚子两天",
            history_present_illness=(
                "前天晚上吃了烧烤，第二天开始肚子一阵一阵疼，拉了四五次，"
                "都是稀的，有点恶心，但是没吐，也没发烧。自己喝了点热水，"
                "感觉没什么用。"
            ),
            past_history="平时身体正常",
            physical_exam="腹软，脐周轻压痛，无反跳痛",
            lab_results="未提供",
        ),
        "required": (
            "腹痛伴腹泻2天",
            "患者于2天前晚间进食烧烤后",
            "排稀便4-5次",
            "自行饮用热水，效果欠佳",
            "既往体健",
        ),
        "banned": ("肚子疼", "拉肚子", "没吐", "没发烧", "没什么用"),
    },
    {
        "name": "成人呼吸口语",
        "patient": PatientInput(
            name="验收乙",
            gender="女",
            age=46,
            department="internal",
            chief_complaint="咳了一个星期，晚上特别厉害，还有黄痰",
            history_present_illness=(
                "上周淋雨以后就开始咳，晚上咳得睡不好，吐黄色的痰，但是没发烧。"
                "自己喝了止咳糖浆，没什么用。"
            ),
            past_history="以前得过慢性支气管炎",
            physical_exam="双肺呼吸音粗",
            lab_results="血常规白细胞11.2×10^9/L",
        ),
        "required": (
            "咳嗽1周，夜间加重，伴咳黄痰",
            "患者于1周前淋雨后出现咳嗽",
            "自行服用止咳糖浆，效果欠佳",
            "既往有慢性支气管炎病史",
            "11.2×10^9/L",
        ),
        "banned": ("咳了", "特别厉害", "没发烧", "没什么用"),
    },
    {
        "name": "成人神经口语",
        "patient": PatientInput(
            name="验收丙",
            gender="男",
            age=58,
            department="internal",
            chief_complaint="这两天老是头疼头晕",
            history_present_illness=(
                "两天前开始头疼，脑袋发胀，站起来有点晕，没有吐，也没有胸口疼。"
            ),
            past_history="高血压五年",
            physical_exam="血压165/100mmHg，心率88次/分",
            lab_results="未提供",
        ),
        "required": (
            "头痛、头晕2天",
            "患者于2天前出现头痛",
            "站立时头晕",
            "无呕吐，无胸痛",
            "高血压病史5年",
        ),
        "banned": ("头疼", "脑袋", "有点晕", "胸口疼"),
    },
    {
        "name": "成人泌尿口语",
        "patient": PatientInput(
            name="验收丁",
            gender="女",
            age=31,
            department="internal",
            chief_complaint="小便的时候疼，还老想上厕所三天",
            history_present_illness=(
                "三天前开始尿尿疼，一会儿就想去厕所，每次尿得不多，"
                "没有发烧，也没有腰疼。"
            ),
            past_history="平时身体正常",
            physical_exam="下腹部轻压痛",
            lab_results="尿常规白细胞阳性",
        ),
        "required": (
            "尿痛、尿频3天",
            "患者于3天前出现尿痛",
            "每次尿量少",
            "无发热，无腰痛",
            "尿常规白细胞阳性",
        ),
        "banned": ("小便的时候疼", "上厕所", "尿尿疼", "腰疼"),
    },
    {
        "name": "儿科发热口语",
        "patient": PatientInput(
            name="验收戊",
            gender="男",
            age=6,
            department="pediatrics",
            chief_complaint="孩子发烧咳嗽三天了",
            history_present_illness=(
                "三天前开始发烧，最高39度，咳嗽还有痰，吃了退烧药以后能降下来，"
                "但是过几个小时又烧。"
            ),
            past_history="平时身体挺好的",
            physical_exam="咽部充血",
            lab_results="血常规白细胞偏高",
        ),
        "required": (
            "发热、咳嗽3天",
            "患儿于3天前出现发热",
            "最高体温39℃",
            "服用退热药后体温可下降",
            "数小时后体温再次升高",
        ),
        "banned": ("孩子发烧", "还有痰", "退烧药", "又烧"),
    },
)


def main() -> None:
    generator = RecordGenerator()
    results: list[dict[str, object]] = []
    started = perf_counter()
    for case in CASES:
        generated = generator.generate(case["patient"])
        missing = [value for value in case["required"] if value not in generated.text]
        retained = [value for value in case["banned"] if value in generated.text]
        passed = not missing and not retained and not generated.info.fallback_used
        results.append(
            {
                "name": case["name"],
                "passed": passed,
                "backend": generated.info.backend,
                "fallbackUsed": generated.info.fallback_used,
                "missingRequired": missing,
                "retainedColloquial": retained,
                "warnings": list(generated.info.warnings),
            }
        )
    passed_count = sum(bool(result["passed"]) for result in results)
    report = {
        "modelVersion": RECORD_MODEL_VERSION,
        "evaluatedAt": datetime.now(timezone.utc).isoformat(),
        "caseCount": len(results),
        "passedCount": passed_count,
        "passRate": passed_count / max(len(results), 1),
        "seconds": perf_counter() - started,
        "cases": results,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    output = AI_ROOT / "artifacts" / "record-generation-v1" / "oral_formalization_metrics.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    print(text)
    if passed_count != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
