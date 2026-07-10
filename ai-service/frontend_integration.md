# CYH 前端对接说明

## 对接基线

- 仓库：`liumumumumu/Medical-Record-System`
- 分支：`CYH`
- 审计提交：`5a996e4a3f9d773079ca2059074b4ee4fed1b5f8`
- 审计日期：2026-07-10
- 前端状态：页面、表单、结果展示和构建已完成，但提交仍使用 `sessionStorage` 模拟数据，没有 Axios 请求。

本服务不改动前端同学代码，而是提供与该提交字段完全兼容的 `POST /nlp/analyze/frontend`。推荐正式调用链仍为 `React -> SpringBoot -> Flask`；课程联调阶段也可由前端直连该端点验证结果结构。

## 输入字段映射

| CYH 前端字段 | AI 内部字段 | 处理方式 |
| --- | --- | --- |
| `patientName` | `name` | 直接映射 |
| `gender` | `gender` | `male/female` 转为病历中的“男/女”，响应保留英文枚举 |
| `age` | `age` | 接受 0–130 整数，与前端校验一致 |
| `department` | `department` | 保留到摘要和病历，不参与模型分类 |
| `visitDate` | `visit_date` | 保留 ISO 日期 |
| `chiefComplaint` | `chief_complaint` | 进入症状抽取、分类和病历 |
| `presentIllness` | `history_present_illness` | 进入症状抽取、分类和病历 |
| `pastHistory` | `past_history` | 进入否定识别和病历 |
| `allergyHistory` | `allergy_history` | 进入术语/否定识别和病历 |
| `vitalSigns` | `vital_signs` | 解析体温、血压、血糖等指标 |
| `physicalExam` | `physical_exam` | 进入症状抽取和病历 |
| `auxiliaryExam` | `lab_results` | 进入数值/术语抽取和病历 |
| `attachments` | `attachments` | 当前只返回文件名元数据，不解析文件内容 |
| `preliminaryDiagnosis` | 人工初步诊断 | 原样保留，不加入模型文本，避免标签泄漏和自证循环 |
| `treatmentTaken` | 人工治疗记录 | 原样保留，不改变 AI 安全建议 |
| `medicationUsage` | 人工用药记录 | 原样保留，不生成或修改处方 |
| `generationNeeds` | 生成需求 | 原样返回，供后端/前端决定展示区域 |

六个必填字段与前端一致：`patientName`、`gender`、`age`、`chiefComplaint`、`presentIllness`、`pastHistory`。

## 输出映射

v2 响应直接分为：

- `summary`：对应结果页病例摘要。
- `structuredRecord`：对应现病史、既往史、过敏史、生命体征、体格检查、辅助检查和完整生成病历。
- `analysis`：保留人工输入，并增加症状、术语、Top-1/Top-3、理由、安全建议、低置信度和免责声明。
- `attachments`：当前只标记 `metadata_only`；真实文件 URL 和解析结果由后端/数据处理成员补充。
- `model`：模型名、版本、融合置信分和低置信标记。

前端当前 `GeneratedRecord` 仍只有 `{id, generatedAt, values}`，接入时应改为 `handoff/frontend-ai-contract.ts` 中的 `FrontendAnalysisResult`，不要再把 AI 数据塞回原始表单字段。

## 同步策略

本地实测单次 AI 推理通常低于 100ms，因此 A 侧提供同步接口，建议 SpringBoot 设置 10 秒超时。若后端加入附件解析或排队任务，可按 CYH 交接文档包装为 `caseId/jobId` 异步生命周期，AI 响应主体无需改变。

## 明确边界

- Flask 不负责登录、权限、病例持久化、文件存储和历史记录。
- 前端不应直接把 `confidence` 显示为医学确诊概率；它只是融合排序分。
- `lowConfidence=true` 或 `diagnosisTop1=暂无法确定` 时，页面应展示补充信息/咨询医生提示。
- 所有页面、下载报告和接口结果必须保留免责声明。

