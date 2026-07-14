# Flask AI 服务契约

Spring Boot 在 `AI_MODE=remote` 时调用：

```http
POST ${AI_BASE_URL}${AI_ENDPOINT}
Content-Type: application/json
```

默认地址为 `http://127.0.0.1:5000/nlp/analyze`。调用超时为 20 秒；连接错误、超时或 5xx 会自动重试一次。

## 请求

后端负责将前端 `camelCase` 转为 AI 使用的 `snake_case`：

```json
{
  "name": "张某",
  "gender": "男",
  "age": 32,
  "department": "internal",
  "visit_date": "2026-07-10",
  "chief_complaint": "发热、咳嗽 3 天",
  "history_present_illness": "3 天前受凉后出现发热、咳嗽和乏力",
  "past_history": "无慢性病史",
  "allergy_history": "无",
  "vital_signs": "体温 38.2℃",
  "physical_exam": "咽部轻度充血",
  "lab_results": "白细胞轻度升高",
  "preliminary_diagnosis": "上呼吸道感染待查",
  "treatment_taken": "暂未处理",
  "medication_usage": "无",
  "generation_needs": ["record", "symptom", "diagnosis", "treatment", "full-report"]
}
```

可选字段无内容时可以为 `null`。AI 服务不得读取 MongoDB，也不得依赖前端字段名。

## 成功响应

HTTP 状态必须为 2xx，响应必须是结构化 JSON：

```json
{
  "generated_record": "完整结构化病历文本",
  "symptoms": ["发热", "咳嗽", "乏力"],
  "medical_terms": ["上呼吸道感染", "白细胞"],
  "diagnosis_top1": "上呼吸道感染",
  "diagnosis_candidates": ["上呼吸道感染", "流感"],
  "diagnosis_reason": "存在发热、咳嗽等呼吸道表现，需结合检查进一步判断。",
  "treatment_advice": "建议休息、多饮水，必要时由医生完善相关检查。",
  "content": "可选的综合分析文本",
  "model_version": "rules-1.0"
}
```

`generated_record` 和 `diagnosis_top1` 为后端当前要求的必要字段。数组无结果时返回空数组，不返回逗号拼接字符串。

为兼容当前 LLY 服务，后端也接受等价的 camelCase 字段，例如 `generatedRecord`、`medicalTerms`、`diagnosisTop1`、`diagnosisCandidates`、`diagnosisReason` 和 `treatmentAdvice`。

## 失败映射

| Flask 情况 | 后端任务错误码 |
| --- | --- |
| 超过 `AI_TIMEOUT` | `AI_TIMEOUT` |
| 无法连接或返回 5xx | `AI_PROCESSING_FAILED` |
| 返回 4xx | `AI_PROCESSING_FAILED` |
| 缺少必要字段 | `AI_PROCESSING_FAILED` |

失败不会删除病例输入。前端可调用 `POST /api/v1/cases/{caseId}/retry` 创建新任务。
