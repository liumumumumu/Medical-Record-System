# 三分支小联调报告

验证日期：2026-07-10

## 固定基线

| 模块 | 分支与提交 | 验证范围 |
| --- | --- | --- |
| AI 服务 | `LLY@0f5ad3b` | 模型加载、字段校验、推理和响应契约 |
| React 前端 | `CYH@5a996e4` | 生产构建、17 字段表单和附件序列化 |
| 数据分析 | `CYL@a122e9f` | 病例标准化、附件处理和特征文本 |

## 已修复问题

1. LLY 新增 `POST /nlp/analyze/standardized`，支持 CYL 的 `patient_name`、`present_illness`、`auxiliary_exam` 等 snake_case 字段。
2. CYL 现在可把前端实际产生的 `"a.pdf / b.png"` 转为两个待解析附件，不再静默丢失。
3. CYL 的模型特征不再混入人工初步诊断、治疗记录和用药记录，避免标签泄漏。
4. CYL 流水线测试改为比较真实项目根路径，不再依赖目录名必须为 `Medical-Record-System`。

## 实测链路

```text
CYH 17 字段表单对象
  -> CYL standardize_case()
  -> LLY POST /nlp/analyze/standardized
  -> FrontendAnalysisResult 分区响应
```

脱敏流感病例实测结果：

- HTTP 200，`application/json; charset=utf-8`
- 姓名和年龄在标准化及响应阶段保持一致
- 阳性症状包含高热、发热、咳嗽、乏力、头痛和肌肉酸痛
- Top-1 为流行性感冒，Top-3 为流行性感冒、上呼吸道感染、急性咽炎
- 两个附件均保留文件名并标记为 `pending`
- 响应包含“不替代医生诊断”免责声明
- 人工初步诊断不进入模型特征，污染派生字段不会改变推理结果

## 后端大联调契约

- SpringBoot 对前端请求完成鉴权、持久化和文件存储后，可直接调用 `/nlp/analyze/frontend`。
- 若先经过 CYL 标准化，则调用 `/nlp/analyze/standardized`；两个端点返回相同的顶层响应结构。
- 后端应设置 10 秒 AI 调用超时，并把不可用、超时和字段错误映射为统一业务错误。
- 文件 URL、下载权限和附件内容解析由后端负责；AI 当前只消费和返回附件元数据。
- `confidence` 仅用于排序和低置信提示，不应展示为临床确诊概率。
