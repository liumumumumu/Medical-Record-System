"""新模型手动验收：8 个用例覆盖双后端切换后的关键路径。

用法：先启动服务（python app.py），另开终端运行 python scripts/manual_test.py。
仅用标准库，显式绕过系统代理，直连 http://127.0.0.1:5000。
"""

import json
import urllib.request

BASE = "http://127.0.0.1:5000"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


CASES = [
    {
        "name": "1-核心类·支气管炎（走 BERT 后端）",
        "payload": {
            "name": "测试一", "gender": "男", "age": 5,
            "chiefComplaint": "咳嗽咳痰5天，夜间加重伴喘息",
            "historyPresentIllness": "5天前受凉后咳嗽，有白痰，昨夜出现喘息和胸闷，精神一般",
        },
        "expect": {"top1": "支气管炎"},
    },
    {
        "name": "2-核心类·腹泻（口语同义词：拉肚子/拉稀→腹泻）",
        "payload": {
            "name": "测试二", "gender": "女", "age": 3,
            "chiefComplaint": "拉肚子两天，一天拉稀六七次",
            "historyPresentIllness": "两天前吃坏东西后开始拉肚子，大便稀，肚子疼，尿量稍减少",
        },
        "expect": {"top1": "腹泻", "symptom_has": "腹泻"},
    },
    {
        "name": "3-核心类·便秘",
        "payload": {
            "name": "测试三", "gender": "女", "age": 6,
            "chiefComplaint": "四五天排不出大便，肚子胀",
            "historyPresentIllness": "近一周排便困难，大便很干，腹胀，食欲下降",
        },
        "expect": {"top1": "便秘"},
    },
    {
        "name": "4-扩展类·流行性感冒（走知识检索+规则，验证融合未被破坏）",
        "payload": {
            "name": "测试四", "gender": "男", "age": 24,
            "chiefComplaint": "高烧39.5度一天，浑身肌肉酸痛",
            "historyPresentIllness": "昨日起高热，头痛乏力明显，肌肉酸痛，干咳，同事有类似症状",
        },
        "expect": {"top3_has": "流行性感冒"},
    },
    {
        "name": "5-否定识别（无发热/否认高血压糖尿病史，不得计入阳性症状）",
        "payload": {
            "name": "测试五", "gender": "男", "age": 45,
            "chiefComplaint": "咳嗽咳痰一周",
            "historyPresentIllness": "咳嗽咳痰一周，无发热，无胸痛",
            "pastHistory": "否认高血压糖尿病史",
        },
        "expect": {"symptom_not": ["发热", "高血压", "糖尿病", "胸痛"], "symptom_has": "咳嗽"},
    },
    {
        "name": "6-数值规则（165/105mmHg→血压升高→高血压进候选）",
        "payload": {
            "name": "测试六", "gender": "女", "age": 58,
            "chiefComplaint": "头晕头痛三天",
            "historyPresentIllness": "近三天反复头晕头痛，偶有心悸耳鸣",
            "physicalExam": "血压165/105mmHg，心率88次/分",
        },
        "expect": {"symptom_has": "血压升高", "top3_has": "高血压"},
    },
    {
        "name": "7-危险信号（持续胸痛→建议必须提示急诊）",
        "payload": {
            "name": "测试七", "gender": "男", "age": 62,
            "chiefComplaint": "胸痛2小时不缓解",
            "historyPresentIllness": "2小时前突发压榨性胸痛，持续胸痛不缓解，出冷汗",
        },
        "expect": {"advice_has": "急诊"},
    },
    {
        "name": "8-信息不足（只有乏力→应返回暂无法确定，不硬猜）",
        "payload": {
            "name": "测试八", "gender": "女", "age": 30,
            "chiefComplaint": "最近没劲",
            "historyPresentIllness": "近来觉得没劲，其他没什么不舒服",
        },
        "expect": {"top1": "暂无法确定", "low_confidence": True},
    },
]


def post(path: str, payload: dict) -> dict:
    request = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with OPENER.open(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def check(case: dict, result: dict) -> list[str]:
    failures = []
    expect = case["expect"]
    top3 = [result["diagnosisTop1"], *result["diagnosisCandidates"]]
    if "top1" in expect and result["diagnosisTop1"] != expect["top1"]:
        failures.append(f"top1 应为 {expect['top1']}，实际 {result['diagnosisTop1']}")
    if "top3_has" in expect and expect["top3_has"] not in top3:
        failures.append(f"Top-3 应包含 {expect['top3_has']}，实际 {top3}")
    if "symptom_has" in expect and expect["symptom_has"] not in result["symptoms"]:
        failures.append(f"症状应包含 {expect['symptom_has']}，实际 {result['symptoms']}")
    for banned in expect.get("symptom_not", []):
        if banned in result["symptoms"]:
            failures.append(f"症状不应包含被否定的 {banned}")
    if "advice_has" in expect and expect["advice_has"] not in result["treatmentAdvice"]:
        failures.append("建议中缺少急诊提示")
    if expect.get("low_confidence") and not result["lowConfidence"]:
        failures.append("应标记 lowConfidence")
    return failures


def main() -> None:
    with OPENER.open(BASE + "/health", timeout=10) as response:
        health = json.loads(response.read().decode("utf-8"))
    print(f"服务状态: {health['status']} | 后端: {health['modelBackend']} | 版本: {health['modelVersion']}\n")

    passed = 0
    for case in CASES:
        result = post("/nlp/analyze", case["payload"])
        failures = check(case, result)
        mark = "PASS" if not failures else "FAIL"
        passed += not failures
        print(f"[{mark}] {case['name']}")
        print(f"       诊断: {result['diagnosisTop1']}  候选: {result['diagnosisCandidates']}  置信度: {result['confidence']}")
        print(f"       症状: {result['symptoms']}")
        if failures:
            for failure in failures:
                print(f"       !! {failure}")
    print(f"\n{passed}/{len(CASES)} 通过")


if __name__ == "__main__":
    main()
