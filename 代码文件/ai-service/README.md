# 医疗病历生成与分析系统——AI 服务

本目录是四人分工中 A 负责的完整交付，提供数据准备、模型训练评估、症状识别、医学术语抽取、20 类常见病辅助判断、结构化病历生成、安全建议、Flask 推理服务和跨模块交接包。服务只用于课程演示，不用于真实诊疗。

## 已实现能力

- **Transformer 病历生成（record-gen-t5-v1.2.0）**：基于 `IDEA-CCNL/Randeng-T5-77M-MultiTask-Chinese`，用真实患者自述/医患对话作为输入、规范病历作为目标，生成主诉、现病史、既往史和辅助检查四段。运行时增加口语到临床书面语规范化与原始事实锚定；过敏史、生命体征、体格检查、医生诊断、已接受治疗和用药记录也会在不新增事实的前提下保守书面化，再组装成精简住院病历。正式化字段会随 `formalizedInput` 传给 Spring Boot，结果页不再重复展示口语原文。该链路与 BERT 辅助诊断完全独立，并带事实守卫、受约束重试和显式模板兜底。实现与复现说明见 [`../../docs/project/record-generation-implementation.md`](../../docs/project/record-generation-implementation.md)。
- **正式监督模型（v2.0.0）**：`bert-base-chinese` 微调，覆盖五个核心类（上呼吸道感染、普通感冒、支气管炎、腹泻、便秘），训练集为 IMCS-21 官方划分金标 1,358 条 + 远程监督弱标签 2,500 条，官方测试集 accuracy 0.8499、macro-F1 0.8598，推理时做温度缩放（T=2.5）校准。选型经两轮对比实验（`transformer_comparison.md`、`augmentation_report.md`），综合准确率、最难类改善与扩展空间后正式采用。
- 早期 TF-IDF + 逻辑回归模型（v1.0.0，macro-F1 0.8491）**已弃用**，仅在无 BERT 权重或未装 torch 的环境自动降级兜底（接口契约一致，`/health` 的 `modelBackend` 字段区分）。BERT 权重约 391MB 不入库，答辩演示机已就绪；其他机器可用 `python scripts/train_transformer_augmented.py` 约 3 分钟复训。
- 基于 9,620 条中文疾病知识记录的检索层，以及覆盖 20 类常见病的稳定规则层。
- 5,584 个由 CMeEE-V2 标注数据整理的疾病、药物、检查、操作、设备和科室术语。
- 同义词归一、否定识别、体温/血压/血糖数值识别和危险症状提示。
- `GET /health`、`GET /metadata`、轻量分析接口，以及 CYH/CYL 字段兼容接口。
- 已按 `liumumumumu/Medical-Record-System` 的 `CYH@5a996e4` 审计 17 个表单字段和结果页结构。
- 44 条 AI 样例和完整自动测试；核心模型测试集 accuracy 为 0.8366，macro-F1 为 0.8491。

## 目录说明

```text
ai-service/
├── app.py                         Flask 入口
├── src/                           抽取、诊断、生成和服务模块
├── config/                        诊断标签、同义词、安全建议配置
├── scripts/                       下载、资源构建、训练和评估脚本
├── models/                        模型、指标、报告和混淆矩阵
├── resources/                     医学词典和知识索引
├── tests/                         自动测试
├── handoff/                       前端类型、请求样例和 SpringBoot 映射
├── ai_test_cases.json             44 条验收样例
├── demo_cases.json                10 条稳定演示输入
├── api_document.md                给后端成员的接口文档
├── frontend_integration.md        CYH 分支字段审计与对接说明
├── openapi.yaml                   OpenAPI 3.1 契约
├── A_DELIVERABLES.md              A 成员逐项验收表
├── model_report.md                数据、方法、指标和限制
└── defense_notes.md               A 成员答辩讲稿
```

## 环境与启动

推荐 Python 3.13，项目模型使用 scikit-learn 1.8.0 生成。PowerShell 命令如下：

```powershell
cd "D:\医疗病历生成与分析系统\代码文件\ai-service"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-generation.txt
python app.py
```

仓库包含辅助诊断模型和知识索引。病历生成权重位于本地 `models/record_generator_v1/` 且不进入 Git；该目录存在时无需重新训练，否则应先执行下方病历生成数据准备与训练命令。服务默认监听 `http://localhost:5000`。

## 从原始数据复现

```powershell
python scripts/download_disease_database.py
python scripts/prepare_resources.py
python scripts/train_model.py                 # v1 基线（已弃用，供对比复现）
python scripts/train_transformer_augmented.py # v2 正式模型（需 torch+transformers，约3分钟）
python scripts/evaluate_model.py
python scripts/evaluate_ai_cases.py
python scripts/prepare_record_generation_data.py
python scripts/train_record_generator.py
python scripts/prepare_record_alignment_data.py
python scripts/align_record_generator.py --base-dir models/record_generator_v1 --output-dir models/record_generator_formal_v2 --train-file alignment_real_train.jsonl --learning-rate 1e-5
python scripts/evaluate_record_generator.py --model-dir models/record_generator_v1 --data-file ../../dataset/derived/record-generation-v1/alignment_test.jsonl
python scripts/evaluate_oral_formalization.py
python -m pytest
# 全系统启动后，在仓库根目录运行：python scripts/e2e-oral-formalization.py
```

`prepare_record_alignment_data.py` 会拒绝把“口语输入→口语摘抄”的弱标注用于书面化微调，并检查输入中不存在由参考答案反构造的整段泄露；候选权重通过独立 test 和短口语运行时验收后，再提升到 `models/record_generator_v1/`。更完整的复现说明见 `../../docs/project/record-generation-implementation.md`。训练固定随机种子 42，并保持 IMCS-21 原始 train/dev/test 隔离。

最终 v1.2.0 在 811 条未参与训练的真实对话同构 test 上 BLEU-2 0.3990、ROUGE-L 0.5357、四段解析/完整率 100%、数值一致率 98.40%、关键疾病/药物术语一致率 94.70%。其中 BLEU-2 与数值一致率未达到原先设置的 0.45/99% 门槛，必须如实保留；运行时事实守卫会拒绝新增数值。另有 5 组短口语专项病例（胃肠、呼吸、神经、泌尿、儿科）全部保持 Transformer 路径、无兜底、必需事实完整且不残留指定口语词。真实 HTTP 验收还要求摘要、6 个结构化字段、完整正文和 DOCX 同时书面化；结果保存在 `../../output/e2e/oral-formalization.json`。该结果不代表临床有效性。

## 快速检查

```powershell
Invoke-RestMethod http://localhost:5000/health

$body = @{
  name = "张三"
  gender = "男"
  age = 28
  chiefComplaint = "发热咳嗽3天，伴咽痛和鼻塞"
  historyPresentIllness = "受凉后出现发热、咳嗽、咽痛和鼻塞"
  pastHistory = "无高血压糖尿病史"
  physicalExam = "体温38.5℃，咽部充血"
  labResults = "白细胞轻度升高"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://localhost:5000/nlp/analyze `
  -ContentType "application/json" -Body $body
```

完整字段和错误格式见 `api_document.md`。若模型文件缺失，服务仍可启动并使用知识检索和规则，但 `/health` 会把 `modelLoaded` 标为 `false`。

CYH 前端的 17 字段请求应调用 `POST /nlp/analyze/frontend`；CYL 标准化 snake_case 病例应调用 `POST /nlp/analyze/standardized`。两者响应中的 `summary`、`structuredRecord` 和人工诊断/治疗/用药字段均为书面化结果；原始输入仍由 Spring Boot 保存在 `patientInput` 中供追溯。

## 安全边界

- 不保存、上传或记录请求中的患者数据。
- 不直接使用下载知识库中的治疗文本，不输出具体处方或剂量。
- 信息不足时返回“暂无法确定”；危险信号优先提示急诊或及时就医。
- 页面、报告和建议中必须保留“不替代医生诊断”的免责声明。
