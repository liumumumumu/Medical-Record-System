# A 成员完整交付验收表

## 原始分工交付

- [x] `src/symptom_extractor.py`：症状、同义词、否定和数值指标识别。
- [x] `src/medical_term_extractor.py`：基于 CMeEE-V2 的 5,584 个医学术语。
- [x] `src/diagnosis_analyzer.py`：监督模型、知识检索和规则融合。
- [x] `src/record_generator.py`：九段式结构化病历。
- [x] `config/treatment_rules.json`：20 类安全建议模板。
- [x] `config/diagnosis_labels.json`：20 类标签、别名和关键症状。
- [x] `model_report.md`：数据、方法、指标、限制和升级方向。
- [x] `ai_test_cases.json`：40 条诊断样例和 4 条安全边界样例。

## 模型训练交付

- [x] 固定 IMCS-21 官方 train/dev/test 划分和随机种子 42。
- [x] 提供可重复执行的下载、资源构建、训练和评估脚本。
- [x] 保存 `diagnosis_model.joblib`、指标 JSON、分类报告和混淆矩阵。
- [x] 官方测试集 accuracy 0.8366、macro-F1 0.8491，均超过 0.80。
- [x] 20 类课程样例 Top-3 命中 40/40，并明确不是临床验证指标。
- [x] 保存数据来源、固定 revision、许可和 SHA-256。

## 推理服务交付

- [x] `GET /health`：服务、模型和知识索引状态。
- [x] `GET /metadata`：模型版本、类别、指标和运行限制。
- [x] `POST /nlp/analyze`：兼容原四人计划的轻量接口。
- [x] `POST /nlp/analyze/frontend`：对齐 CYH 分支 17 个字段和分区结果。
- [x] 兼容 camelCase、snake_case 和 CYH 前端命名。
- [x] 低置信度拒答、危险信号、1MB 请求限制和统一 UTF-8 JSON。
- [x] 稳定免责声明，不输出具体药物处方和剂量。

## 交接与答辩交付

- [x] `api_document.md`、`openapi.yaml` 和实际请求/响应示例。
- [x] `frontend_integration.md`：基于 `CYH@5a996e4` 的字段审计与映射。
- [x] `handoff/frontend-ai-contract.ts`：前端可复制的 TypeScript 类型。
- [x] `handoff/springboot_mapping.md`：后端调用、超时和错误映射说明。
- [x] `demo_cases.json`：10 条稳定演示病例。
- [x] `defense_notes.md`：讲稿、演示顺序和常见问题。
- [x] 自动测试、训练复现、真实 HTTP 和 UTF-8 联调验证。

## 不属于 A 的边界

- SpringBoot 业务接口、MongoDB 持久化、登录认证、文件存储与报告下载由后端成员负责。
- React Axios 接入、任务状态 UI 和结果页改造由前端成员负责。
- 数据字段最终治理、附件 OCR/解析和脱敏流水线由数据处理成员负责。

