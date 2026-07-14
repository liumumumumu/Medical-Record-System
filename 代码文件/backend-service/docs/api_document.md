# 后端 API 文档

基础地址：`http://localhost:8080/api/v1`

除注册、登录和健康检查外，业务接口必须携带：

```http
Authorization: Bearer <token>
```

成功响应直接返回业务对象，不套 `data`。所有响应包含 `X-Request-Id` 响应头。

## 统一错误

```json
{
  "code": "VALIDATION_ERROR",
  "message": "提交内容校验失败",
  "fieldErrors": {
    "age": "年龄必须在 0 至 130 之间"
  },
  "requestId": "req_xxx"
}
```

主要错误码：`VALIDATION_ERROR`、`INVALID_JSON`、`UNAUTHORIZED`、`FORBIDDEN`、`CASE_NOT_FOUND`、`JOB_NOT_FOUND`、`RESULT_NOT_READY`、`FILE_TOO_LARGE`、`UNSUPPORTED_FILE_TYPE`、`AI_TIMEOUT`、`AI_PROCESSING_FAILED`、`INTERNAL_ERROR`。

## 1. 注册与登录

`POST /auth/register`

```json
{
  "username": "doctor_demo",
  "password": "demo123456",
  "displayName": "演示医生"
}
```

注册成功后直接返回与登录相同的 Token 响应。用户名已存在时返回 HTTP 409 和 `USERNAME_EXISTS`。

`POST /auth/login`

```json
{
  "username": "demo",
  "password": "demo123456"
}
```

```json
{
  "token": "eyJ...",
  "tokenType": "Bearer",
  "expiresIn": 7200,
  "user": {
    "id": "user_xxx",
    "username": "demo",
    "role": "USER"
  }
}
```

辅助接口：`GET /auth/me` 获取当前用户；`POST /auth/logout` 返回 `204`。注销后端会持久化撤销当前 Token 的哈希，旧 Token 即使尚未自然过期也不能继续使用；前端同时清除会话存储。

## 2. 创建病例

`POST /cases`，成功返回 `202 Accepted`。

无附件时使用 `application/json`，字段示例见 [`demo-case.json`](demo-case.json)。必填字段为：

- `patientName`：最多 30 字。
- `gender`：`male` 或 `female`。
- `age`：0 至 130 的整数。
- `chiefComplaint`：最多 200 字。
- `presentIllness`：最多 1200 字。
- `pastHistory`：选填，最多 800 字；缺省时保存为“未提供”。

可选枚举：

- `department`：`internal`、`surgery`、`pediatrics`、`emergency`、`other`。
- `generationNeeds`：`record`、`symptom`、`diagnosis`、`treatment`、`full-report`。

```bash
curl -X POST http://localhost:8080/api/v1/cases \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  --data @docs/demo-case.json
```

有附件时使用 multipart，其中 `case` 是 `application/json` 类型的 JSON Part，`attachments` 可以重复：

```bash
curl -X POST http://localhost:8080/api/v1/cases \
  -H "Authorization: Bearer $TOKEN" \
  -F 'case=@docs/demo-case.json;type=application/json' \
  -F 'attachments=@/path/to/check.pdf;type=application/pdf'
```

附件支持 PDF、DOC、DOCX、JPG、JPEG、PNG；每个 10 MB，最多 5 个，总计 30 MB。后端同时检查扩展名、声明 MIME 和实际文件头，伪装文件会返回 `UNSUPPORTED_FILE_TYPE`。PDF、DOC、DOCX 正文会被提取并加入 AI 的辅助检查上下文；图片未配置 OCR 时返回 `metadata_only` 和明确原因。附件响应还会返回 `extractedText` 与 `failureReason`。

响应：

```json
{
  "caseId": "case_xxx",
  "jobId": "job_xxx",
  "status": "queued",
  "createdAt": "2026-07-10T08:00:00Z"
}
```

## 3. 查询任务

`GET /jobs/{jobId}`

```json
{
  "jobId": "job_xxx",
  "caseId": "case_xxx",
  "status": "processing",
  "progress": 20,
  "message": "正在调用 AI 分析服务",
  "createdAt": "2026-07-10T08:00:00Z",
  "updatedAt": "2026-07-10T08:00:01Z"
}
```

状态只有 `queued`、`processing`、`completed`、`failed`、`cancelled`。失败时额外返回 `errorCode` 和 `errorMessage`。

推荐前端每 1000 ms 轮询一次，最长等待 60 秒；页面刷新后从路由或存储的 `jobId` 恢复轮询。

## 4. 获取结果

`GET /cases/{caseId}/result`

任务未完成时返回 HTTP 409 和 `RESULT_NOT_READY`。完成后结构如下：

```json
{
  "caseId": "case_xxx",
  "generatedAt": "2026-07-10T08:00:02Z",
  "summary": {
    "patientName": "张某",
    "gender": "male",
    "age": 32,
    "department": "internal",
    "visitDate": "2026-07-10",
    "chiefComplaint": "发热、咳嗽 3 天"
  },
  "structuredRecord": {
    "generatedContent": "完整结构化病历文本",
    "presentIllness": "...",
    "pastHistory": "...",
    "allergyHistory": "无",
    "vitalSigns": "...",
    "physicalExam": "...",
    "auxiliaryExam": "..."
  },
  "analysis": {
    "generationNeeds": ["record", "diagnosis"],
    "content": "综合分析",
    "symptoms": ["发热", "咳嗽"],
    "medicalTerms": ["上呼吸道感染"],
    "diagnosisTop1": "上呼吸道感染",
    "diagnosisCandidates": ["上呼吸道感染", "流感"],
    "diagnosisReason": "...",
    "treatmentAdvice": "...",
    "modelVersion": "mock-rules-1.0",
    "confidence": 0.82,
    "lowConfidence": false,
    "lowConfidenceReason": null,
    "disclaimer": "仅供辅助整理与课程演示，不替代执业医师判断。"
  },
  "attachments": []
}
```

## 5. 重试失败任务

`POST /cases/{caseId}/retry`

仅允许当前状态为 `failed` 的病例。返回新的 `jobId` 和 `202`，原失败任务保留。

## 6. 历史与详情

- `GET /cases?keyword=张某&page=0&size=20`：按患者姓名或主诉在 MongoDB 端搜索后分页；空关键字返回全部，`size` 最大 100。
- `GET /cases/{caseId}`：返回输入、当前状态、当前任务、结果、编辑内容和附件。

分页响应固定为：

```json
{
  "content": [],
  "page": 0,
  "size": 20,
  "totalElements": 0,
  "totalPages": 0
}
```

## 7. 编辑病历

`PUT /cases/{caseId}/record`

```json
{
  "editedRecord": "人工审核并修改后的完整病历内容"
}
```

分析完成后才能编辑，最大 20000 字。编辑后结果接口的 `structuredRecord.generatedContent` 使用编辑内容，旧报告缓存立即失效。

## 8. 下载附件和报告

- `GET /cases/{caseId}/attachments/{fileId}`：返回原 MIME 文件流。
- `GET /cases/{caseId}/report`：生成或复用最新版本 DOCX。

响应均使用 `Content-Disposition: attachment`，前端应以 Blob 下载。报告包括患者摘要、原始信息、最新病历、辅助分析和免责声明。

## 前端最小联调顺序

1. 登录并保存 `token`。
2. 提交病例并保存 `caseId/jobId`。
3. 轮询任务，完成后停止定时器。
4. 获取结果并按 `summary/structuredRecord/analysis/attachments` 映射。
5. 失败时根据 `errorCode` 显示原因，并调用重试接口。
6. 历史、编辑和下载在主链路稳定后接入。
