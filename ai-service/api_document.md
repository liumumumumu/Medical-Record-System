# Flask AI 服务接口文档

服务地址：`http://localhost:5000`。SpringBoot 只需调用本服务，不需要读取模型文件或数据库。

## 健康检查

`GET /health`

成功响应：

```json
{
  "status": "ok",
  "service": "ai-service",
  "modelLoaded": true,
  "knowledgeLoaded": true,
  "supportedDiagnoses": 20
}
```

联调前应确认 `modelLoaded` 和 `knowledgeLoaded` 均为 `true`。

## CYH 前端兼容分析（推荐联调）

`POST /nlp/analyze/frontend`

该端点按 `Medical-Record-System` 的 `CYH@5a996e4` 字段契约接收 `patientName`、`presentIllness`、`auxiliaryExam` 等 17 个字段。完整请求见 `handoff/frontend_request.example.json`，完整响应见 `handoff/frontend_response.example.json`。

成功响应分区如下：

```json
{
  "status": "completed",
  "generatedAt": "2026-07-10T12:00:00+00:00",
  "processingTimeMs": 6.4,
  "model": {
    "name": "medical-record-hybrid-diagnosis",
    "version": "1.0.0",
    "confidence": 0.72,
    "lowConfidence": false
  },
  "summary": {},
  "structuredRecord": {},
  "analysis": {},
  "attachments": [],
  "failureReason": null
}
```

六个必填字段为 `patientName`、`gender`、`age`、`chiefComplaint`、`presentIllness`、`pastHistory`。校验错误使用 CYH 交接规范要求的结构：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "缺少必填字段: presentIllness",
  "fieldErrors": {"presentIllness": "该字段为必填项"},
  "requestId": "req_123456789abc"
}
```

## CYL 标准化病例分析

`POST /nlp/analyze/standardized`

该端点接收 CYL 分支输出的 snake_case 病例，完整示例见 `handoff/standardized_request.example.json`。成功响应与 `/nlp/analyze/frontend` 相同，标准化附件对象会保留文件名、MIME 类型、解析状态、失败原因和置信度。

服务只从 `chief_complaint`、`present_illness`、`past_history`、`allergy_history`、`vital_signs`、`physical_exam` 和 `auxiliary_exam` 读取模型证据。为避免标签泄漏，输入中的 `clean_text`、`symptoms`、`medical_terms`、`tokens`、`preliminary_diagnosis`、`treatment_taken` 和 `medication_usage` 不参与推理；后三项仅在响应中原样保留。

## 轻量病历分析（原计划兼容）

`POST /nlp/analyze`

请求头：`Content-Type: application/json`

请求示例：

```json
{
  "name": "张三",
  "gender": "男",
  "age": 28,
  "chiefComplaint": "发热咳嗽3天，伴咽痛和鼻塞",
  "historyPresentIllness": "受凉后出现发热、咳嗽、咽痛和鼻塞",
  "pastHistory": "无高血压糖尿病史",
  "physicalExam": "体温38.5℃，咽部充血",
  "labResults": "白细胞轻度升高"
}
```

`name`、`gender`、`age`、`chiefComplaint`、`historyPresentIllness` 必填；年龄必须为 0–130 的整数。其余字段缺省时按“未提供”处理。服务同时接受 `chief_complaint`、`history_present_illness`、`past_history`、`physical_exam`、`lab_results`。CYL 的完整标准化对象应使用上面的专用端点。

成功响应为原始 `AnalysisResult`，不再额外包一层 `data`：

```json
{
  "generatedRecord": "一、基本信息……",
  "symptoms": ["发热", "咳嗽", "咽痛", "鼻塞", "咽部充血"],
  "medicalTerms": ["上呼吸道感染", "血常规", "白细胞"],
  "diagnosisTop1": "上呼吸道感染",
  "diagnosisCandidates": ["上呼吸道感染", "急性咽炎", "普通感冒"],
  "diagnosisReason": "识别到发热、咳嗽、咽痛等表现……",
  "treatmentAdvice": "建议充分休息……本结果仅用于课程演示和辅助分析，不替代医生诊断。"
}
```

字段说明：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `generatedRecord` | string | 八个部分组成的结构化病历 |
| `symptoms` | string[] | 已标准化且排除否定描述的阳性症状 |
| `medicalTerms` | string[] | 疾病、检查、药物等医学术语，最多 20 个 |
| `diagnosisTop1` | string | 得分最高且证据充足的结果；否则为“暂无法确定” |
| `diagnosisCandidates` | string[] | 最多 3 个候选，不代表确诊 |
| `diagnosisReason` | string | 命中症状、否定信息和融合判断说明 |
| `treatmentAdvice` | string | 安全建议、危险信号提示和免责声明 |

## 错误响应

参数错误返回 HTTP 400：

```json
{
  "code": 400,
  "message": "缺少必填字段: chiefComplaint",
  "data": null
}
```

内部错误返回 HTTP 500：

```json
{
  "code": 500,
  "message": "AI 分析服务内部错误",
  "data": null
}
```

后端联调时应设置连接和读取超时，并在服务不可用时返回“AI 服务暂不可用”的业务提示，不应伪造诊断结果。

## 模型元数据

`GET /metadata` 返回模型名、版本、20 个支持类别、核心测试指标、请求上限、同步超时建议和附件解析能力。前端或后端可在联调启动时检查该端点，但不要把融合 `confidence` 当作临床确诊概率。
