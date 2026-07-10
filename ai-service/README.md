# 医疗病历生成与分析系统——AI 服务

本目录是四人分工中 A 负责的完整交付，提供数据准备、模型训练评估、症状识别、医学术语抽取、20 类常见病辅助判断、结构化病历生成、安全建议、Flask 推理服务和跨模块交接包。服务只用于课程演示，不用于真实诊疗。

## 已实现能力

- IMCS-21 官方划分训练的五类监督模型：上呼吸道感染、普通感冒、支气管炎、腹泻、便秘。
- 基于 9,620 条中文疾病知识记录的检索层，以及覆盖 20 类常见病的稳定规则层。
- 5,584 个由 CMeEE-V2 标注数据整理的疾病、药物、检查、操作、设备和科室术语。
- 同义词归一、否定识别、体温/血压/血糖数值识别和危险症状提示。
- `GET /health`、`GET /metadata`、轻量分析接口和 CYH 前端字段兼容接口。
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
python app.py
```

仓库已包含训练好的模型和知识索引，正常演示无需重新训练。服务默认监听 `http://localhost:5000`。

## 从原始数据复现

```powershell
python scripts/download_disease_database.py
python scripts/prepare_resources.py
python scripts/train_model.py
python scripts/evaluate_model.py
python scripts/evaluate_ai_cases.py
python -m pytest
```

下载脚本固定 Hugging Face 数据版本，并在 `dataset/Disease_Database/SOURCE.json` 保存 SHA-256。训练固定随机种子 42，并使用 IMCS-21 原始 train/dev/test 划分。

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

CYH 前端的 17 字段请求应调用 `POST /nlp/analyze/frontend`；CYL 标准化 snake_case 病例应调用 `POST /nlp/analyze/standardized`。两者响应均可直接映射到 `summary`、`structuredRecord`、`analysis` 和 `attachments`。详细映射见 `frontend_integration.md`，TypeScript 类型见 `handoff/frontend-ai-contract.ts`。

## 安全边界

- 不保存、上传或记录请求中的患者数据。
- 不直接使用下载知识库中的治疗文本，不输出具体处方或剂量。
- 信息不足时返回“暂无法确定”；危险信号优先提示急诊或及时就医。
- 页面、报告和建议中必须保留“不替代医生诊断”的免责声明。
