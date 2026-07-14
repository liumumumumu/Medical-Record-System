# 三分支完整联调问题报告

检查日期：2026-07-10

## 固定版本

| 模块 | 本地目录 | 分支与提交 |
| --- | --- | --- |
| 前端 | `代码文件/frontend` | `CYH@5a996e4` |
| 数据分析 | `代码文件/data-analysis` | `CYL@0704aba` |
| AI | `代码文件/ai-service` | 本地 LLY 工作副本，已补 CYL 兼容修复 |
| 后端 | `代码文件/backend-service` | 本地第一版，MongoDB 模式 |

## 已通过项目

- CYH `npm ci` 成功，生产构建成功，3,456 个模块完成打包。
- CYL 12/12 自动化测试通过。
- CYL 病例预处理、关键词特征生成全部成功。
- CYL NHANES 流水线处理 9,254 行、155 个合并字段，并通过 8 项输出校验。
- LLY 20/20 测试通过，模型与知识库均加载，支持 20 类诊断。
- Spring Boot、Flask、MongoDB 的登录、病例、AI、历史、编辑、重启持久化和 DOCX 下载流程通过。
- 后端接受 CYH 的真实字段类型：字符串年龄和附件文件名字符串。

## LLY 已直接修复

### CYL 标准化病例无法调用 AI

复现：将 `data-analysis/data/processed/clinical_cases_standardized.json` 提交到本地 AI 时，`POST /nlp/analyze/standardized` 原先返回 HTTP 404。

处理：

- 新增 `POST /nlp/analyze/standardized`。
- 白名单映射 CYL snake_case 字段。
- 保留附件 `parsed/pending/failed` 元数据。
- 明确忽略 `clean_text`、派生 tokens、人工诊断、治疗和用药字段作为模型证据。
- 新增 3 个 API 回归场景，AI 测试从 17 项增加到 20 项。

实测结果：CYL 标准病例返回 HTTP 200，患者为张某，Top-1 为急性咽炎，Top-3 包含急性咽炎、上呼吸道感染和流行性感冒，附件状态为 `parsed`，免责声明存在。

## CYH 前端必须修改

### P0：没有调用后端，完整 UI 流程实际未联通

证据：

- `frontend/src/App.tsx` 的 `handleGenerate()` 只构造浏览器本地编号并写入 `sessionStorage`。
- `frontend/src/components/upload/upload-module.tsx` 提交时只等待 450ms，然后调用本地回调。
- 源码没有 Axios API 层；Axios 依赖已安装但未使用。
- 浏览器提交“浏览器演示患者”后，MongoDB 历史匹配记录为 0 条。

建议：新增 `services/medical-api.ts`，登录调用 `/api/v1/auth/login`，病例提交调用 `/api/v1/cases`，保存后端返回的 `data.id` 和完整 `data.aiResult`。

### P0：登录是假登录，错误账号也会成功

证据：`frontend/src/components/auth/login-dialog.tsx` 只检查账号密码非空。浏览器输入 `not-a-real-user / wrong-password` 后直接显示登录头像。

同时，刷新页面后登录状态立即丢失，结果页仍从 `sessionStorage` 保留，形成“未登录但能查看病例”的不一致状态。

建议：接真实登录接口，保存 token，启动时调用 `/api/v1/auth/me` 恢复会话；401 时清理会话并跳转登录。

### P0：结果页展示的是人工输入，不是 AI 结果

证据：`frontend/src/pages/results-page.tsx` 只读取 `record.values`。浏览器提交流感病例后，页面显示人工填写的“初步诊断：待查”，没有显示后端真实返回的“流行性感冒”。

缺失展示项：

- `generatedRecord`
- `symptoms`
- `medicalTerms`
- `diagnosisTop1`
- `diagnosisCandidates`
- `diagnosisReason`
- `treatmentAdvice`
- `lowConfidence` 和免责声明

建议：将 `GeneratedRecord` 类型替换为后端 `CaseRecordView`，结果页读取 `data.aiResult.summary`、`structuredRecord`、`analysis` 和 `attachments`。

### P1：历史、编辑和报告下载没有页面或操作

证据：`App.tsx` 只有 `/upload` 与 `/results` 两条业务路由；访问 `/history` 会被重定向到 `/upload`。结果页没有编辑保存和下载按钮。

建议：

- 新增历史页并调用 `GET /api/records`。
- 详情调用 `GET /api/records/{id}`。
- 编辑保存调用 `PUT /api/records/{id}`。
- DOCX 下载调用 `GET /api/reports/{id}/download`，携带 Bearer token。

### P1：附件只保存文件名，没有上传文件内容

证据：文件控件把 `File[]` 转成 `"a.pdf / b.png"` 字符串，真实文件对象随即丢失。

当前后端和 AI 可保留文件名元数据，但无法解析文件内容。前后端需另行约定 multipart 上传、文件存储、大小/类型错误和解析状态；这不应由 AI 猜测文件内容。

## CYL 数据分析建议修改

### P2：Windows 重跑流水线后 14 个生成文件显示为已修改

完整流水线语义结果可复现，`git diff --quiet` 返回 0，但 `git status` 将 14 个 `data/processed/*` 文件标记为 `.M`。原因是仓库要求 LF，而 pandas/文本写入在 Windows 生成 CRLF。

建议所有 CSV 写入显式使用 `lineterminator="\n"`，JSON/文本使用 `open(..., newline="\n", encoding="utf-8")`，保证 Windows 和 CI 重跑后工作树保持干净。

### 协作确认项：CYL 是离线流水线，不在当前在线请求链中

当前真实在线链路是 `React -> Spring Boot -> Flask -> MongoDB`，CYL 的 `preprocess.py` 通过离线脚本运行。若课程只要求展示数据清洗过程，这没有问题；若要求每次用户提交都经过 CYL，则需由 CYL/后端共同确定服务化接口或 Java 等价实现，不能让前端直接调用本地 Python 脚本。

## 当前可用链路

```text
后端 API 脱敏请求
  -> Spring Boot 认证与校验
  -> Flask AI 分析
  -> MongoDB 持久化
  -> 历史查询
  -> 编辑保存
  -> DOCX 下载
```

该链路已通过。当前无法从 CYH 页面走到该链路，阻断点全部位于前端 API 接入层。
