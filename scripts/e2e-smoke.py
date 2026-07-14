"""Run a real HTTP smoke test against the four-service local stack.

Only Python's standard library is used so this can run on a freshly prepared
course-project machine after the normal service dependencies are installed.
"""

from __future__ import annotations

import argparse
import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree


DISCLAIMER = "仅供辅助整理与课程演示，不替代执业医师判断。"


def request(
    method: str,
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 30,
) -> tuple[int, dict[str, str], bytes]:
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, dict(response.headers.items()), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers.items()), error.read()


def json_request(
    method: str,
    url: str,
    payload: object | None = None,
    token: str | None = None,
) -> tuple[int, dict[str, str], object]:
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    status, response_headers, body = request(method, url, data=data, headers=headers)
    parsed = json.loads(body.decode("utf-8")) if body else None
    return status, response_headers, parsed


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def minimal_docx(text: str) -> bytes:
    escaped = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
    relationships = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    document = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>{escaped}</w:t></w:r></w:p><w:sectPr/></w:body>
</w:document>"""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/document.xml", document)
    return output.getvalue()


def multipart(case_payload: dict[str, object], attachment: bytes) -> tuple[str, bytes]:
    boundary = "----medical-record-e2e-boundary"
    chunks = [
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="case"; filename="case.json"\r\n',
        b"Content-Type: application/json; charset=utf-8\r\n\r\n",
        json.dumps(case_payload, ensure_ascii=False).encode("utf-8"),
        b"\r\n",
        f"--{boundary}\r\n".encode(),
        'Content-Disposition: form-data; name="attachments"; filename="联调检查结果.docx"\r\n'.encode("utf-8"),
        b"Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n",
        attachment,
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    return boundary, b"".join(chunks)


def wait_for_job(base_url: str, job_id: str, token: str, timeout: float = 60) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status, _, payload = json_request("GET", f"{base_url}/api/v1/jobs/{job_id}", token=token)
        require(status == 200 and isinstance(payload, dict), "任务状态接口不可用")
        if payload["status"] == "completed":
            return payload
        if payload["status"] in {"failed", "cancelled"}:
            raise AssertionError(f"病例分析失败：{payload}")
        time.sleep(0.3)
    raise AssertionError("等待病例分析完成超时")


def docx_text(content: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    return "\n".join(node.text or "" for node in root.iter() if node.tag.endswith("}t"))


def run(base_url: str, ai_url: str, artifact_dir: Path, filler_count: int) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    username = f"e2e_{stamp}"
    patient_name = f"联调目标患者{stamp[-8:]}"

    status, _, ai_health = json_request("GET", f"{ai_url}/health")
    require(status == 200 and isinstance(ai_health, dict) and ai_health.get("status") == "ok", "AI 健康检查失败")
    status, _, backend_health = json_request("GET", f"{base_url}/actuator/health")
    require(status == 200 and isinstance(backend_health, dict) and backend_health.get("status") == "UP", "后端聚合健康检查失败")
    status, cors_headers, _ = request(
        "OPTIONS",
        f"{base_url}/api/v1/auth/login",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    allow_origin = next(
        (value for key, value in cors_headers.items() if key.lower() == "access-control-allow-origin"),
        "",
    )
    require(status == 200 and allow_origin == "http://127.0.0.1:5173", "127.0.0.1 前端来源未通过 CORS 预检")

    invalid_password = "密" * 30
    status, _, invalid = json_request(
        "POST",
        f"{base_url}/api/v1/auth/register",
        {"username": f"invalid_{stamp}", "password": invalid_password, "displayName": "无效密码测试"},
    )
    require(status == 400, f"超出 bcrypt 字节上限的密码未被校验：{invalid}")

    status, _, session = json_request(
        "POST",
        f"{base_url}/api/v1/auth/register",
        {"username": username, "password": "SafePassword123!", "displayName": "全链路测试"},
    )
    require(status in {200, 201} and isinstance(session, dict), f"注册失败：{session}")
    token = str(session["token"])

    case_payload: dict[str, object] = {
        "patientName": patient_name,
        "gender": "female",
        "age": 0,
        "department": "internal",
        "visitDate": "2026-07-13",
        "chiefComplaint": "发热、咳嗽三天",
        "presentIllness": "受凉后发热、咳嗽，伴咽痛和乏力。",
        "pastHistory": "无特殊病史",
        "allergyHistory": "无",
        "vitalSigns": "体温 38.5℃",
        "physicalExam": "咽部充血",
        "auxiliaryExam": "待结合附件",
        "generationNeeds": ["record", "symptom", "diagnosis", "treatment", "full-report"],
    }
    attachment_text = "附件检查提示白细胞轻度升高，C反应蛋白升高。"
    attachment_bytes = minimal_docx(attachment_text)
    boundary, body = multipart(case_payload, attachment_bytes)
    status, _, created_body = request(
        "POST",
        f"{base_url}/api/v1/cases",
        data=body,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    created = json.loads(created_body.decode("utf-8"))
    require(status == 202, f"multipart 病例创建失败：{created}")
    case_id = str(created["caseId"])

    for index in range(filler_count):
        filler = dict(case_payload)
        filler.update(
            {
                "patientName": f"分页填充患者{index:02d}_{stamp[-5:]}",
                "chiefComplaint": f"分页联调填充症状 {index:02d}",
                "generationNeeds": ["record"],
            }
        )
        filler_status, _, filler_result = json_request(
            "POST", f"{base_url}/api/v1/cases", filler, token
        )
        require(filler_status == 202, f"分页填充病例创建失败：{filler_result}")

    wait_for_job(base_url, str(created["jobId"]), token)
    status, _, detail = json_request("GET", f"{base_url}/api/v1/cases/{case_id}", token=token)
    require(status == 200 and isinstance(detail, dict), "病例详情读取失败")
    result = detail["result"]
    analysis = result["analysis"]
    attachments = result["attachments"]
    require(detail["status"] == "completed", "病例未进入完成状态")
    require(analysis["modelVersion"] != "unknown", "后端未使用真实 AI 服务")
    require(0.0 <= float(analysis["confidence"]) <= 1.0, "动态置信度超出有效范围")
    require(attachments and attachments[0]["parseStatus"] == "parsed", "DOCX 附件未解析")
    require("白细胞轻度升高" in attachments[0]["extractedText"], "附件提取文本不正确")
    require("白细胞轻度升高" in result["structuredRecord"]["generatedContent"], "附件文本未进入 AI 上下文")
    require(result["summary"]["age"] == 0, "年龄 0 在接口链路中丢失")

    status, _, first_page = json_request(
        "GET", f"{base_url}/api/v1/cases?page=0&size=20", token=token
    )
    require(status == 200 and isinstance(first_page, dict), "历史分页接口失败")
    if filler_count >= 20:
        require(case_id not in {item["caseId"] for item in first_page["content"]}, "分页测试前提未满足")
    query = urllib.parse.urlencode({"keyword": patient_name, "page": 0, "size": 20})
    status, _, search_page = json_request(
        "GET", f"{base_url}/api/v1/cases?{query}", token=token
    )
    require(status == 200 and isinstance(search_page, dict), "历史搜索接口失败")
    require(case_id in {item["caseId"] for item in search_page["content"]}, "服务端搜索未找到分页外病例")

    edited_record = "人工复核病历第一行\n人工复核病历第二行"
    status, _, edited = json_request(
        "PUT",
        f"{base_url}/api/v1/cases/{case_id}/record",
        {"editedRecord": edited_record},
        token,
    )
    require(status == 200 and isinstance(edited, dict) and edited.get("editedRecord") == edited_record, "病历编辑保存失败")

    auth_headers = {"Authorization": f"Bearer {token}"}
    status, _, report = request("GET", f"{base_url}/api/v1/cases/{case_id}/report", headers=auth_headers)
    require(status == 200 and report.startswith(b"PK"), "DOCX 报告下载失败")
    report_text = docx_text(report)
    require("人工复核病历第一行" in report_text and "人工复核病历第二行" in report_text, "报告未使用编辑后的病历")
    require("科室：内科" in report_text, "报告科室未本地化")
    require(report_text.count(DISCLAIMER) == 1, "报告免责声明不是恰好一次")

    attachment_url = str(attachments[0]["url"])
    status, _, downloaded_attachment = request("GET", f"{base_url}{attachment_url}", headers=auth_headers)
    require(status == 200 and downloaded_attachment == attachment_bytes, "附件鉴权下载内容不一致")

    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "e2e-report.docx").write_bytes(report)
    (artifact_dir / "e2e-attachment.docx").write_bytes(downloaded_attachment)

    status, _, _ = json_request("POST", f"{base_url}/api/v1/auth/logout", token=token)
    require(status == 204, "注销接口失败")
    status, _, _ = json_request("GET", f"{base_url}/api/v1/auth/me", token=token)
    require(status == 401, "注销后的旧令牌仍然有效")

    status, _, second_session = json_request(
        "POST",
        f"{base_url}/api/v1/auth/login",
        {"username": username, "password": "SafePassword123!"},
    )
    require(status == 200 and isinstance(second_session, dict), "注销后重新登录失败")
    require(second_session["token"] != token, "重新登录没有签发新令牌")
    status, _, current_user = json_request(
        "GET", f"{base_url}/api/v1/auth/me", token=str(second_session["token"])
    )
    require(status == 200 and isinstance(current_user, dict) and current_user["username"] == username, "新令牌不可用")

    status, _, _ = request("GET", f"{base_url}/v3/api-docs", headers={"Accept": "application/json"})
    require(status != 200, "Swagger 在默认安全配置下仍公开")

    print(json.dumps({
        "status": "passed",
        "caseId": case_id,
        "jobId": created["jobId"],
        "modelVersion": analysis["modelVersion"],
        "confidence": analysis["confidence"],
        "attachmentStatus": attachments[0]["parseStatus"],
        "searchTotal": search_page["totalElements"],
        "artifacts": str(artifact_dir.resolve()),
    }, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--ai-url", default="http://127.0.0.1:5000")
    parser.add_argument("--artifact-dir", type=Path, default=Path(".runtime/e2e-artifacts"))
    parser.add_argument("--filler-count", type=int, default=21)
    args = parser.parse_args()
    run(args.base_url.rstrip("/"), args.ai_url.rstrip("/"), args.artifact_dir, args.filler_count)


if __name__ == "__main__":
    main()
