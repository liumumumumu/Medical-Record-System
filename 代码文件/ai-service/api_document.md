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
  "modelBackend": "transformer",
  "recordGeneratorLoaded": true,
  "recordGeneratorBackend": "transformer",
  "recordGeneratorVersion": "record-gen-t5-v1.2.0",
  "knowledgeLoaded": true,
  "supportedDiagnoses": 20
}
```

联调前应确认 `modelLoaded` 和 `knowledgeLoaded` 均为 `true`。`modelBackend` 表示当前诊断模型后端：`transformer` 为**正式模型**（BERT 微调，modelVersion 2.0.0，需本机有 `models/transformer_production/` 权重和 torch，答辩演示机即此配置）；`sklearn` 为已弃用的 v1 模型（modelVersion 1.0.0），仅在缺少权重或 torch 时自动降级兜底。两种后端的请求/响应契约完全一致，SpringBoot 无需感知差异。

病历生成模型与诊断模型是两条独立链路。答辩环境还应确认 `recordGeneratorLoaded=true` 且 `recordGeneratorBackend=transformer`；若为 `template`，说明本次病历采用了输入事实模板兜底，不能宣称由 Transformer 生成。`backend=transformer` 时 `warnings` 仍可能记录缺失字段归一、附件事实补入或受约束二次生成，这些是安全约束，不等同于完整模板兜底；是否完整兜底以 `fallbackUsed` 为准。

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
  "recordGeneration": {
    "backend": "transformer",
    "modelName": "IDEA-CCNL/Randeng-T5-77M-MultiTask-Chinese",
    "modelVersion": "record-gen-t5-v1.2.0",
    "fallbackUsed": false,
    "warnings": []
  },
  "summary": {"chiefComplaint": "腹痛伴腹泻2天"},
  "structuredRecord": {
    "presentIllness": "患者于2天前晚间进食烧烤后……",
    "pastHistory": "既往体健",
    "allergyHistory": "否认药物过敏史",
    "vitalSigns": "T 36.8℃，P 78次/分",
    "physicalExam": "脐周轻压痛，无反跳痛",
    "auxiliaryExam": "未提供"
  },
  "analysis": {},
  "attachments": [],
  "failureReason": null
}
```

`summary`、`structuredRecord` 以及 `analysis` 中的人工诊断/治疗/用药字段均返回临床书面化文本，不再回显口语原文；系统只改写表达，不新增诊断、治疗、药物或数值事实。Spring Boot 的病例详情仍在 `patientInput` 中保存原始请求，便于追溯和人工复核。

五个必填字段为 `patientName`、`gender`、`age`、`chiefComplaint`、`presentIllness`。`pastHistory` 为选填，缺省时按“未提供”处理。校验错误使用 CYH 交接规范要求的结构：

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

该端点接收 CYL `preprocess.py` 输出的 snake_case 病例，完整示例见 `handoff/standardized_request.example.json`。成功响应与 `/nlp/analyze/frontend` 相同，并保留标准化附件的文件名、MIME 类型、解析状态、失败原因和置信度。

辅助诊断只从主诉、现病史、既往史、过敏史、生命体征、体格检查和辅助检查读取模型证据。`clean_text`、`symptoms`、`medical_terms`、`tokens` 以及人工诊断、治疗和用药字段不会进入辅助诊断推理，避免标签泄漏；人工填写的初步诊断、已接受治疗和用药记录会保留事实并转换为临床书面语后进入正式病历，且绝不会被辅助诊断结果覆盖。

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

`name`、`gender`、`age`、`chiefComplaint`、`historyPresentIllness` 必填；年龄必须为 0–130 的整数。其余字段缺省时按“未提供”处理。服务同时接受 `chief_complaint`、`history_present_illness`、`past_history`、`physical_exam`、`lab_results`。

成功响应为原始 `AnalysisResult`，不再额外包一层 `data`：

```json
{
  "generatedRecord": "一、基本信息……",
  "recordGeneration": {
    "backend": "transformer",
    "modelName": "IDEA-CCNL/Randeng-T5-77M-MultiTask-Chinese",
    "modelVersion": "record-gen-t5-v1.2.0",
    "fallbackUsed": false,
    "warnings": []
  },
  "formalizedInput": {
    "chiefComplaint": "发热、咳嗽3天，伴咽痛和鼻塞",
    "presentIllness": "受凉后出现发热、咳嗽、咽痛和鼻塞",
    "pastHistory": "无高血压糖尿病史",
    "allergyHistory": "未提供",
    "vitalSigns": "未提供",
    "physicalExam": "体温38.5℃，咽部充血",
    "auxiliaryExam": "白细胞轻度升高",
    "preliminaryDiagnosis": "未提供",
    "treatmentTaken": "未提供",
    "medicationUsage": "未提供"
  },
  "symptoms": ["发热", "咳嗽", "咽痛", "鼻塞", "咽部充血"],
  "medicalTerms": ["上呼吸道感染", "血常规", "白细胞"],
  "diagnosisTop1": "上呼吸道感染",
  "diagnosisCandidates": ["上呼吸道感染", "急性咽炎", "普通感冒"],
  "diagnosisReason": "识别到发热、咳嗽、咽痛等表现……",
  "treatmentAdvice": "建议充分休息……本结果仅用于课程演示和辅助分析，不替代医生诊断。",
  "content": "识别到发热、咳嗽、咽痛等表现……",
  "modelVersion": "1.0.0"
}
```

字段说明：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `generatedRecord` | string | 十个部分组成的精简住院病历；诊断、既往治疗和用药保留输入事实并书面化 |
| `recordGeneration` | object | 病历生成后端、模型名/版本、是否兜底及安全校验提示 |
| `formalizedInput` | object | 十类字段的书面化结果，供 Spring Boot/前端展示；原始请求另行保留 |
| `symptoms` | string[] | 已标准化且排除否定描述的阳性症状 |
| `medicalTerms` | string[] | 疾病、检查、药物等医学术语，最多 20 个 |
| `diagnosisTop1` | string | 得分最高且证据充足的结果；否则为“暂无法确定” |
| `diagnosisCandidates` | string[] | 最多 3 个候选，不代表确诊 |
| `diagnosisReason` | string | 命中症状、否定信息和融合判断说明 |
| `treatmentAdvice` | string | 安全建议、危险信号提示和免责声明 |
| `content` | string | 综合分析文本，当前与 `diagnosisReason` 一致，供后端 `analysis.content` 展示 |
| `modelVersion` | string | 模型版本号，对应 SpringBoot 契约中的 `model_version`/`modelVersion` |

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
