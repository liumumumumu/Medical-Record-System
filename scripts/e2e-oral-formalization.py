"""End-to-end acceptance for colloquial input -> formal record -> DOCX."""

from __future__ import annotations

from datetime import datetime, timezone
import io
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import zipfile
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:8080"


def request(method: str, url: str, payload: object | None = None, token: str = "") -> bytes:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urlopen(Request(url, data=body, headers=headers, method=method), timeout=30) as response:
            return response.read()
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code} {method} {url}: {detail}") from error


def json_request(method: str, url: str, payload: object | None = None, token: str = "") -> dict:
    return json.loads(request(method, url, payload, token).decode("utf-8"))


def docx_text(content: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    return "\n".join(node.text or "" for node in root.iter() if node.tag.endswith("}t"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    session = json_request(
        "POST",
        f"{BASE_URL}/api/v1/auth/login",
        {"username": "demo", "password": "demo123456"},
    )
    token = str(session["token"])
    payload = {
        "patientName": "口语书面化测试患者",
        "gender": "male",
        "age": 24,
        "department": "internal",
        "visitDate": "2026-07-17",
        "chiefComplaint": "肚子疼还拉肚子两天",
        "presentIllness": (
            "前天晚上吃了烧烤，第二天开始肚子一阵一阵疼，拉了四五次，"
            "都是稀的，有点恶心，但是没吐，也没发烧。自己喝了点热水，"
            "感觉没什么用。"
        ),
        "pastHistory": "平时身体正常",
        "allergyHistory": "没发现有什么药过敏",
        "vitalSigns": "体温36.8度，心率78次每分钟",
        "physicalExam": "肚脐周围按着有点疼，无反跳痛",
        "auxiliaryExam": "未提供",
        "preliminaryDiagnosis": "医生考虑急性胃肠炎",
        "treatmentTaken": "门诊补液一次，之后腹泻次数减少",
        "medicationUsage": "吃过蒙脱石散",
        "generationNeeds": ["record", "full-report"],
    }
    created = json_request("POST", f"{BASE_URL}/api/v1/cases", payload, token)
    job: dict = {}
    for _ in range(120):
        job = json_request("GET", f"{BASE_URL}/api/v1/jobs/{created['jobId']}", token=token)
        if job.get("status") in {"completed", "failed"}:
            break
        time.sleep(0.5)
    require(job.get("status") == "completed", f"病例任务未完成：{job}")

    case_id = str(created["caseId"])
    detail = json_request("GET", f"{BASE_URL}/api/v1/cases/{case_id}", token=token)
    result = detail["result"]
    generation = result["recordGeneration"]
    structured = result["structuredRecord"]
    analysis = result["analysis"]
    record = str(structured["generatedContent"])
    required = (
        "腹痛伴腹泻2天",
        "患者于2天前晚间进食烧烤后",
        "排稀便4-5次",
        "自行饮用热水，效果欠佳",
        "既往体健",
        "否认药物过敏史",
        "生命体征：T 36.8℃，P 78次/分",
        "体格检查：脐周轻压痛，无反跳痛",
        "考虑急性胃肠炎",
        "曾于门诊接受补液治疗1次，治疗后腹泻次数减少",
        "曾服用蒙脱石散",
    )
    banned = (
        "肚子疼",
        "拉肚子",
        "没吐",
        "没发烧",
        "没什么用",
        "没发现有什么药过敏",
        "体温36.8度",
        "心率78次每分钟",
        "肚脐周围按着有点疼",
        "门诊补液一次",
        "吃过蒙脱石散",
    )
    missing = [phrase for phrase in required if phrase not in record]
    retained = [phrase for phrase in banned if phrase in record]
    structured_expected = {
        "presentIllness": "患者于2天前晚间进食烧烤后，次日出现阵发性腹痛，排稀便4-5次，伴恶心，无呕吐，无发热。自行饮用热水，效果欠佳。",
        "pastHistory": "既往体健",
        "allergyHistory": "否认药物过敏史",
        "vitalSigns": "T 36.8℃，P 78次/分",
        "physicalExam": "脐周轻压痛，无反跳痛",
        "auxiliaryExam": "未提供",
    }
    structured_mismatches = {
        field: {"expected": expected, "actual": structured.get(field)}
        for field, expected in structured_expected.items()
        if structured.get(field) != expected
    }
    analysis_expected = {
        "preliminaryDiagnosis": "考虑急性胃肠炎",
        "treatmentTaken": "曾于门诊接受补液治疗1次，治疗后腹泻次数减少",
        "medicationUsage": "曾服用蒙脱石散",
    }
    analysis_mismatches = {
        field: {"expected": expected, "actual": analysis.get(field)}
        for field, expected in analysis_expected.items()
        if analysis.get(field) != expected
    }
    require(
        result["summary"]["chiefComplaint"] == "腹痛伴腹泻2天",
        f"结果摘要仍为口语：{result['summary']}",
    )
    require(not structured_mismatches, f"结构化字段未书面化：{structured_mismatches}")
    require(not analysis_mismatches, f"诊断/治疗/用药字段未书面化：{analysis_mismatches}")
    require(generation["backend"] == "transformer", f"生成后端错误：{generation}")
    require(generation["fallbackUsed"] is False, f"发生模板兜底：{generation}")
    require(not missing, f"正式病历缺少必要事实：{missing}\n{record}")
    require(not retained, f"正式病历仍保留口语：{retained}\n{record}")

    report = request("GET", f"{BASE_URL}/api/v1/cases/{case_id}/report", token=token)
    report_text = docx_text(report)
    compact_report = re.sub(r"\s+", "", report_text)
    report_missing = [
        phrase for phrase in required if re.sub(r"\s+", "", phrase) not in compact_report
    ]
    require(not report_missing, f"DOCX 缺少正式化内容：{report_missing}")

    document_path = ROOT / "output" / "doc" / "口语病例-书面化病历-v1.2.docx"
    document_path.parent.mkdir(parents=True, exist_ok=True)
    document_path.write_bytes(report)
    summary = {
        "evaluatedAt": datetime.now(timezone.utc).isoformat(),
        "caseId": case_id,
        "jobStatus": job["status"],
        "backend": generation["backend"],
        "modelVersion": generation["modelVersion"],
        "fallbackUsed": generation["fallbackUsed"],
        "missingRequired": missing,
        "retainedColloquial": retained,
        "structuredFieldMismatches": structured_mismatches,
        "analysisFieldMismatches": analysis_mismatches,
        "docxMissingRequired": report_missing,
        "documentPath": str(document_path),
        "documentBytes": len(report),
        "generatedContent": record,
    }
    metrics_path = ROOT / "output" / "e2e" / "oral-formalization.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
