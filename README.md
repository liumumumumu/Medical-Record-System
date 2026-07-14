<div align="center">

# 医疗病历生成与分析系统

### Medical Record Generation and Analysis System

一个贯通病例录入、附件解析、AI 辅助分析、结构化病历生成、历史管理与报告下载的课程项目。

[![React](https://img.shields.io/badge/React-19.1-61DAFB?logo=react&logoColor=white)](代码文件/frontend/frontend/package.json)
[![Spring Boot](https://img.shields.io/badge/Spring_Boot-3.5.16-6DB33F?logo=springboot&logoColor=white)](代码文件/backend-service/pom.xml)
[![Flask](https://img.shields.io/badge/Flask-3.1.2-000000?logo=flask&logoColor=white)](代码文件/ai-service/requirements.txt)
[![MongoDB](https://img.shields.io/badge/MongoDB-8.0-47A248?logo=mongodb&logoColor=white)](代码文件/backend-service/README.md)
[![Java](https://img.shields.io/badge/Java-21-ED8B00?logo=openjdk&logoColor=white)](代码文件/backend-service/pom.xml)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](代码文件/ai-service/README.md)

[快速开始](#-快速开始) · [系统架构](#-系统架构) · [功能说明](#-核心功能) · [项目文档](#-项目文档)

</div>

> [!IMPORTANT]
> 本系统仅用于课程演示与辅助信息整理，不构成医疗诊断或治疗建议。请只使用虚构或脱敏病例数据。

## 📖 项目简介

本项目采用 `React → Spring Boot → Flask AI → MongoDB` 的四层架构，将原本分散的患者信息、检查资料和文本描述组织为清晰的病例处理流程。系统支持用户认证、病例提交、异步 AI 分析、附件解析、结果复核、历史检索和 DOCX 报告下载，并提供独立的数据清洗与质量分析流水线。

在线演示默认调用真实 Flask AI 服务；Mock 仅用于显式的离线测试。仓库已经包含运行演示所需的训练模型、知识索引和脱敏样例，正常使用无需重新训练模型，也无需下载根目录外的 27 GB 原始研究语料。

## ✨ 核心功能

| 模块 | 能力 |
| --- | --- |
| 用户与权限 | 注册、登录、JWT 会话、注销失效、病例所有权校验 |
| 病例录入 | 基本信息、主诉、现病史、既往史、体征、辅助检查等结构化字段 |
| 附件处理 | 支持 PDF、DOC、DOCX 文本提取；图片安全保存并明确标记解析状态 |
| AI 辅助分析 | 症状识别、医学术语抽取、常见病辅助判断、危险信号提示与结构化病历生成 |
| 异步任务 | 病例提交后返回任务 ID，可查询分析进度、完成状态和稳定错误码 |
| 结果管理 | 结果查看、历史分页与搜索、人工复核编辑、附件鉴权下载 |
| 报告导出 | 生成包含结构化信息、分析结果和免责声明的 DOCX 报告 |
| 数据流水线 | NHANES 合并、标准化、数据质量检查以及糖尿病、肾功能、心血管分析子集 |

AI 服务结合监督模型、规则层与知识检索层：监督模型覆盖 5 类高质量训练标签，完整规则与检索能力覆盖 20 类常见疾病；当前核心模型测试集 `accuracy = 0.8366`、`macro-F1 = 0.8491`。详细边界与评估方法见 [AI 模型报告](代码文件/ai-service/model_report.md)。

## 🧭 系统架构

```mermaid
flowchart LR
    U["演示用户"] --> F["React + Vite 前端"]
    F -->|"REST / JWT / Multipart"| B["Spring Boot 后端"]
    B -->|"异步 HTTP"| A["Flask AI 服务"]
    B --> M[("MongoDB")]
    B --> S[("附件与 DOCX 报告")]
    A --> H["监督模型 + 规则 + 知识检索"]

    subgraph Offline["离线数据分析"]
        D["NHANES 与脱敏病例样例"] --> P["清洗 / 标准化 / 质量检查"]
        P --> O["分析数据集与质量报告"]
    end
```

在线请求链与离线数据分析模块职责分离：在线系统负责实时病例处理，数据模块负责可复现的数据准备和分析输出。

## 🧰 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | React 19、TypeScript、Vite 7、Ant Design、Axios、React Router |
| 后端 | Java 21、Spring Boot 3.5、Spring Security、Spring Data MongoDB、WebClient |
| AI 服务 | Python 3.13、Flask、scikit-learn、jieba、NumPy、joblib |
| 数据处理 | pandas、NHANES 2017–2018 公共健康数据、可复现 Python 脚本 |
| 数据库 | MongoDB Community 8.0 |
| 文档与文件 | Apache POI、PDFBox、DOCX 报告、OpenAPI / Postman |
| 测试 | Vitest、JUnit 5、pytest、真实 HTTP 全链路冒烟测试 |

## 📁 目录结构

```text
Medical-Record-System/
├── README.md
├── 启动答辩演示.cmd              # Windows 双击启动
├── 关闭答辩演示.cmd              # Windows 双击安全关闭
├── scripts/
│   ├── start-all.ps1             # 构建、健康检查、启动与自动打开浏览器
│   ├── stop-all.ps1              # 校验进程身份后安全停止
│   ├── run-all-tests.ps1         # 全模块测试与构建
│   └── e2e-smoke.py              # 真实 HTTP 全链路测试
├── docs/
│   ├── assignment/               # 课程要求截图
│   ├── project/                  # 项目规划与分工文档
│   └── reports/                  # 联调与验收报告
└── 代码文件/
    ├── frontend/frontend/        # React 前端
    ├── backend-service/          # Spring Boot 后端
    ├── ai-service/               # Flask AI 推理服务
    └── data-analysis/            # 数据处理与质量分析
```

## 🚀 快速开始

### 1. 环境要求

- Windows 10/11 与 PowerShell 5.1+
- Java 21
- Python 3.13（建议；依赖版本见各模块 `requirements.txt`）
- Node.js 20.19+ 与 npm
- MongoDB Community 8.0
- 首次安装依赖时需要网络

### 2. 克隆并安装依赖

```powershell
git clone https://github.com/liumumumumu/Medical-Record-System.git
cd Medical-Record-System

python -m pip install -r ".\代码文件\ai-service\requirements.txt"
python -m pip install -r ".\代码文件\data-analysis\requirements.txt"

Push-Location ".\代码文件\frontend\frontend"
npm ci
Pop-Location
```

Spring Boot 使用 Maven Wrapper，首次构建时会自动下载 Java 依赖。

### 3. 一键启动

答辩演示时直接双击根目录的：

```text
启动答辩演示.cmd
```

启动器会自动完成环境检查、按需构建、启动 AI/后端/前端、验证固定演示账号并打开浏览器。代码未变化时会复用构建产物。

也可以在 PowerShell 中运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\start-all.ps1" -EnableDemoUser -OpenBrowser
```

默认访问地址：<http://127.0.0.1:5173/>

| 项目 | 默认值 |
| --- | --- |
| 演示账号 | `demo` |
| 演示密码 | `demo123456` |
| 前端 | `http://127.0.0.1:5173` |
| 后端 | `http://127.0.0.1:8080` |
| AI 服务 | `http://127.0.0.1:5000` |
| MongoDB | `mongodb://127.0.0.1:27017/medical_records` |

> 演示账号只用于本地课程展示，不应沿用到公开部署环境。

### 4. 一键关闭

演示结束后双击：

```text
关闭答辩演示.cmd
```

关闭脚本会同时校验 PID、启动时间、可执行文件和命令行，仅结束由本项目启动的前端、后端和 AI 进程；MongoDB 系统服务保持运行。

## ✅ 测试与验证

运行所有模块测试、前端构建和数据流水线：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\run-all-tests.ps1"
```

运行真实 HTTP 全链路测试（会在当前数据库创建 1 条虚构病例）：

```powershell
.\scripts\start-all.ps1 -EnableDemoUser -MongoDatabase medical_records_e2e
python .\scripts\e2e-smoke.py --filler-count 0
.\scripts\stop-all.ps1
```

该测试覆盖 AI/后端健康检查、CORS、注册登录、multipart 附件上传、异步分析、真实 AI 响应、历史搜索、人工编辑、DOCX 报告、附件下载及注销重登。

## ⚙️ 配置说明

主要配置通过环境变量注入，示例见：

- [后端配置模板](代码文件/backend-service/.env.example)
- [前端配置模板](代码文件/frontend/frontend/.env.example)

根目录启动器会在 `.runtime/` 中自动生成本地 JWT 密钥，并将日志、PID 记录和测试产物保存在该目录；这些内容均已从 Git 排除。

## 📚 项目文档

- [初始项目计划](docs/project/initial-project-plan.md)
- [AI 辅助开发总计划](docs/project/ai-development-plan.md)
- [四人分工与交接说明](docs/project/team-collaboration.md)
- [修复后全链路联调报告](docs/reports/e2e-report-fixed-2026-07-13.md)
- [AI 服务说明](代码文件/ai-service/README.md)
- [后端服务说明](代码文件/backend-service/README.md)
- [数据分析说明](代码文件/data-analysis/README.md)
- [前端说明](代码文件/frontend/README.md)

<details>
<summary><strong>查看课程作业要求截图</strong></summary>

<br />

![课程要求一](docs/assignment/requirement-01.png)

![课程要求二](docs/assignment/requirement-02.png)

</details>

## 🔒 数据与安全边界

- 不提交 `.env`、JWT 密钥、运行日志、MongoDB 数据、上传附件或生成报告。
- 大型 `dataset/` 原始研究语料不进入仓库；运行所需模型与脱敏资源已包含。
- 所有病例、附件和报告接口均校验登录用户所有权。
- 图片在未配置 OCR 时只保存并展示元数据，不虚构解析结果。
- 任何公开演示都应使用虚构或充分脱敏的数据。

---

<div align="center">

**仅供辅助整理与课程演示，不替代执业医师判断。**

</div>
