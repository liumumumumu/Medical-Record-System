# A 成员完整交付验收表

## 原始分工交付

- [x] `src/symptom_extractor.py`：症状、同义词、否定和数值指标识别。
- [x] `src/medical_term_extractor.py`：基于 CMeEE-V2 的 5,584 个医学术语。
- [x] `src/diagnosis_analyzer.py`：监督模型、知识检索和规则融合。
- [x] `src/record_generator.py`：T5 四段生成、事实约束、受约束二次生成、十段正式病历组装和显式模板兜底。
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

## 模型升级交付（2026-07-16）

- [x] Transformer 对比实验：同一官方划分微调 `bert-base-chinese`，报告参数量/延迟/体积代价（`transformer_comparison.md`）。
- [x] 数据扩充实验：远程监督弱标签共 9 组对照，验证剂量效应与分布匹配结论（`augmentation_report.md`）。
- [x] 正式模型替换为 BERT 微调 v2.0.0（金标 1,358 + 弱标 2,500，test macro-F1 0.8598），v1 弃用为无 GPU 环境降级兜底。
- [x] softmax 温度缩放校准 T=2.5（`scripts/calibrate_temperature.py`），修复扩展类 top1 被挤占问题。
- [x] 全量回归：44 条样例 Top-3 命中率 1.00、pytest 全绿、Flask 实测单请求约 259ms。

## Transformer 病历生成交付（2026-07-17）

- [x] 固定 `Randeng-T5-77M-MultiTask-Chinese` 基础模型 revision，病历生成与 BERT 辅助诊断完全解耦。
- [x] 原始语料含六科室弱监督 17,083 条和金标 7,405 条；部署版书面化训练按原始病例去重并选择高质量参考，使用 4,933 条真实对话输入、833 条 dev、811 条 test。另构造 2,658 条仅训练集使用的高质量口语扰动做专项实验，但因真实 dev 指标下降未部署；dev/test 从不做目标派生。
- [x] 提供数据准备、基础训练、结构对齐、独立评估和六科室验收脚本。
- [x] 模型生成主诉、现病史、既往史、辅助检查；过敏史、生命体征、体格检查、诊断、既往治疗和用药记录由程序保留输入事实并书面化后组装。
- [x] 新增结构、数值、疾病/药物术语、缺失项、附件事实和文本锚点约束；漏段先由同一 T5 受约束重试，最终失败才返回 `fallbackUsed=true` 的完整安全兜底。
- [x] `/health`、API、MongoDB 结果、前端徽标与 DOCX 报告均可区分真实 Transformer 和模板兜底。
- [x] 最终 v1.2.0：811 条独立 test 的 BLEU-2 0.3990、ROUGE-L 0.5357、四段解析/完整率 100%、数值一致率 98.40%、关键术语一致率 94.70%；BLEU-2 和数值一致率未达到旧门槛，已如实标注。5 组跨场景短口语运行时验收全部走 Transformer、兜底 0、必需事实完整、指定口语残留 0。
- [x] 真实口语 HTTP 全链路验证摘要、6 个结构化字段、完整正文和 DOCX：结构化字段不一致 0、正文事实遗漏 0、口语残留 0、DOCX 缺失 0；通用链路另验证附件解析、MongoDB、人工编辑和编辑前后 DOCX 下载。

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
