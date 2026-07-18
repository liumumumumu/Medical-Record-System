# SpringBoot 调用 Flask 说明

## 推荐调用

- URL：Spring Boot 当前使用 `POST http://localhost:5000/nlp/analyze`；前端直连联调才使用 `/nlp/analyze/frontend`
- Content-Type：`application/json; charset=utf-8`
- 连接超时：2 秒
- 读取超时：20 秒
- 重试：仅连接失败可重试 1 次；参数错误和 AI 返回 4xx 不重试。
- 请求体上限：1 MB。附件文件不发送给 Flask，只发送后端/数据处理模块抽取后的文本或文件名。

后端接收前端 17 个字段后，把字段映射为 AI 请求。`/nlp/analyze` 返回的 `formalizedInput` 必须与 `generatedRecord`、`recordGeneration` 一起保存；病例结果页的 `summary`、`structuredRecord` 和人工诊断/治疗/用药显示值优先取 `formalizedInput`。原始表单继续单独保存在 `patientInput`，不要用口语原文覆盖正式化结果。后端只补充 `caseId`、`jobId`、数据库 ID、真实附件 URL 和权限信息。

## 错误映射

| Flask 错误 | SpringBoot 建议业务码 | HTTP |
| --- | --- | ---: |
| `VALIDATION_ERROR` | `VALIDATION_ERROR` | 400 |
| `FILE_TOO_LARGE` | `FILE_TOO_LARGE` | 413 |
| Flask 连接失败 | `AI_PROCESSING_FAILED` | 502 |
| 读取超过 20 秒 | `AI_TIMEOUT` | 504 |
| `AI_PROCESSING_FAILED` | `AI_PROCESSING_FAILED` | 502 |

SpringBoot 不应在 AI 失败时伪造候选诊断；应保存失败状态和 `requestId`，让前端展示明确的重试入口。

## 同步与异步

A 侧当前为同步接口。Transformer 权重加载完成后，单例推理通常在后端 20 秒读取超时内完成；若后端还要解析文件或排队处理，可在 SpringBoot 外层实现 `queued -> processing -> completed/failed`，Flask 无需感知任务生命周期。
