# 医疗病历生成与分析系统 AI 辅助开发总计划

> **历史规划说明（2026-07-16）**：本文保留项目早期设计与原始开发提示，文中“病历生成使用模板”等内容不代表当前实现。当前正式方案为 Randeng-T5 四段生成、事实守卫、十段安全组装，BERT 仅作辅助诊断；以 `docs/project/record-generation-implementation.md`、实际代码和验收指标为准。

## 1. 项目定位

本项目是一个面向小学期课程设计的“医疗病历生成与分析系统”。最终呈现形式为一个可在本地浏览器访问的 Web 系统，不做公网部署。

系统运行目标：

```text
前端 React 页面：http://localhost:5173
Java SpringBoot 后端：http://localhost:8080
Python Flask AI 服务：http://localhost:5000
MongoDB 数据库：localhost:27017
```

用户打开浏览器访问 `http://localhost:5173` 后，可以完成：

1. 用户登录。
2. 录入患者基本信息和病情描述。
3. 生成结构化医疗病历。
4. 查看症状识别、医学术语抽取、诊断辅助分析和治疗建议。
5. 查看历史记录。
6. 编辑已生成病历。
7. 下载病历和分析报告。

项目强调“课程演示可运行”和“答辩可解释”，不追求真实医疗系统级别的准确性和复杂度。

## 2. 核心要求

### 2.1 必须实现

- 患者信息采集。
- 文本清洗和预处理。
- 医学术语和症状识别。
- 结构化病历生成。
- 诊断辅助分析。
- 治疗建议生成。
- 历史记录保存和查询。
- 病历编辑保存。
- 报告下载。
- 本地完整联调运行。

### 2.2 尽量体现

- Python/Java 双后端。
- SpringBoot 作为系统主后端。
- Flask 作为 NLP/AI 服务。
- React 前端。
- MongoDB 数据存储。
- Transformer / BioBERT 思路说明。
- SNOMED CT、HL7 标准化参考说明。

### 2.3 不做或弱化

- 不接入真实医院 HIS/EMR。
- 不使用真实患者隐私数据。
- 不做公网部署。
- 不训练大型生成式模型。
- 不做 OCR、图像、视频处理。
- 不做复杂权限系统。
- 不做真正自动诊疗。

页面和报告中必须写明：

```text
本系统结果仅用于课程演示和辅助分析，不替代医生诊断。
```

## 3. 技术栈

### 3.1 前端

- React
- Vite
- Ant Design
- Axios
- React Router

前端职责：

- 页面展示。
- 表单录入。
- 表单校验。
- 调用 SpringBoot API。
- 展示病历和分析结果。
- 发起编辑保存和报告下载。

### 3.2 Java 后端

- Java 17 或 Java 21
- SpringBoot
- Spring Web
- Spring Data MongoDB
- Lombok，可选
- Maven

Java 后端职责：

- 用户登录。
- API 统一入口。
- 参数校验。
- 调用 Flask AI 服务。
- MongoDB 数据存储。
- 历史记录查询。
- 病历编辑保存。
- 报告导出。
- 统一返回格式。

### 3.3 Python AI 服务

- Python 3.10+
- Flask
- flask-cors
- jieba
- scikit-learn
- pandas
- numpy
- joblib，可选

Python 服务职责：

- 文本清洗。
- 中文分词。
- 停用词过滤。
- 症状识别。
- 医学术语抽取。
- 诊断辅助分析。
- 病历模板生成。
- 治疗建议模板生成。

说明：

- BioBERT / Transformer 可以作为答辩中的模型升级方案或文本编码思路说明。
- 实际代码优先使用规则词典、TF-IDF 和传统机器学习，保证本地能跑通。

### 3.4 数据库

- MongoDB 本地数据库。
- 默认地址：`mongodb://localhost:27017`
- 默认数据库名：`medical_record_system`

主要集合：

- `users`
- `patient_records`
- `analysis_results`
- `report_files`

## 4. 推荐项目目录结构

```text
medical-record-system/
  README.md
  docs/
    project_plan.md
    api_document.md
    data_schema.md
    ai_module_report.md
    demo_script.md
  frontend/
    package.json
    vite.config.js
    src/
      main.jsx
      App.jsx
      router/
      api/
      pages/
      components/
      styles/
  backend/
    pom.xml
    src/main/java/
      com/example/medicalrecord/
        MedicalRecordApplication.java
        controller/
        service/
        repository/
        model/
        dto/
        config/
        common/
    src/main/resources/
      application.yml
  ai-service/
    requirements.txt
    app.py
    modules/
      preprocess.py
      symptom_extractor.py
      medical_term_extractor.py
      diagnosis_analyzer.py
      record_generator.py
      treatment_generator.py
    data/
      symptom_dict.txt
      medical_terms.txt
      stopwords.txt
      synonyms.json
      demo_data.csv
      train.csv
      test.csv
  scripts/
    start-frontend.bat
    start-backend.bat
    start-ai.bat
```

## 5. 系统架构

```text
用户浏览器
  |
  | 访问 http://localhost:5173
  v
React 前端
  |
  | Axios 调用 /api
  v
SpringBoot 后端 http://localhost:8080
  |
  | HTTP 调用
  v
Flask AI 服务 http://localhost:5000
  |
  | 返回病历生成和分析结果
  v
SpringBoot 后端
  |
  | 保存数据
  v
MongoDB localhost:27017
```

核心调用链：

```text
前端录入患者信息
-> SpringBoot 接收并校验
-> SpringBoot 调用 Flask AI 服务
-> Flask 完成预处理、病历生成和分析
-> SpringBoot 保存患者记录和分析结果
-> 前端展示病历和分析结果
```

## 6. 核心数据结构

### 6.1 PatientInput

前端提交给后端的患者输入结构。

```json
{
  "name": "张三",
  "gender": "男",
  "age": 45,
  "chiefComplaint": "发热咳嗽3天",
  "historyPresentIllness": "3天前受凉后出现发热、咳嗽、乏力",
  "pastHistory": "无高血压糖尿病史",
  "physicalExam": "体温38.5℃，咽部充血",
  "labResults": "白细胞轻度升高"
}
```

字段说明：

| 字段 | 含义 | 是否必填 |
| --- | --- | --- |
| name | 患者姓名 | 是 |
| gender | 性别 | 是 |
| age | 年龄 | 是 |
| chiefComplaint | 主诉 | 是 |
| historyPresentIllness | 现病史 | 是 |
| pastHistory | 既往史 | 否 |
| physicalExam | 体格检查 | 否 |
| labResults | 检查结果 | 否 |

### 6.2 CleanedPatientData

Flask 预处理后得到的标准化数据。

```json
{
  "name": "张三",
  "gender": "男",
  "age": 45,
  "chiefComplaint": "发热咳嗽3天",
  "historyPresentIllness": "3天前受凉后出现发热、咳嗽、乏力",
  "pastHistory": "无高血压糖尿病史",
  "physicalExam": "体温38.5℃，咽部充血",
  "labResults": "白细胞轻度升高",
  "cleanText": "发热 咳嗽 乏力 咽部充血 白细胞升高",
  "tokens": ["发热", "咳嗽", "乏力", "咽部充血", "白细胞"]
}
```

### 6.3 AnalysisResult

Flask 返回给 SpringBoot 的分析结果。

```json
{
  "generatedRecord": "完整结构化病历文本",
  "symptoms": ["发热", "咳嗽", "乏力"],
  "medicalTerms": ["上呼吸道感染", "白细胞"],
  "diagnosisTop1": "上呼吸道感染",
  "diagnosisCandidates": ["上呼吸道感染", "流感"],
  "diagnosisReason": "患者存在发热、咳嗽、咽部充血等表现，符合上呼吸道感染特征。",
  "treatmentAdvice": "建议休息、多饮水，必要时完善血常规检查。本结果仅用于课程演示，不替代医生诊断。"
}
```

### 6.4 PatientRecord

MongoDB 中保存的病历记录。

```json
{
  "id": "recordId",
  "userId": "userId",
  "patientInput": {},
  "generatedRecord": "原始生成病历",
  "editedRecord": "用户编辑后的病历",
  "analysisResultId": "analysisResultId",
  "createdAt": "2026-07-08T10:00:00",
  "updatedAt": "2026-07-08T10:30:00"
}
```

### 6.5 AnalysisResultEntity

MongoDB 中保存的分析结果。

```json
{
  "id": "analysisResultId",
  "recordId": "recordId",
  "symptoms": ["发热", "咳嗽"],
  "medicalTerms": ["上呼吸道感染"],
  "diagnosisTop1": "上呼吸道感染",
  "diagnosisCandidates": ["上呼吸道感染", "流感"],
  "diagnosisReason": "患者存在发热、咳嗽等症状。",
  "treatmentAdvice": "建议休息、多饮水。本结果仅用于课程演示，不替代医生诊断。",
  "createdAt": "2026-07-08T10:00:00"
}
```

## 7. API 设计

### 7.1 统一返回格式

所有 SpringBoot 接口统一返回：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

错误示例：

```json
{
  "code": 400,
  "message": "缺少必填字段 chiefComplaint",
  "data": null
}
```

### 7.2 用户登录

```text
POST /api/auth/login
```

请求：

```json
{
  "username": "admin",
  "password": "123456"
}
```

返回：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "token": "demo-token",
    "user": {
      "id": "u001",
      "username": "admin"
    }
  }
}
```

### 7.3 提交患者信息

```text
POST /api/patients
```

请求：

```json
{
  "name": "张三",
  "gender": "男",
  "age": 45,
  "chiefComplaint": "发热咳嗽3天",
  "historyPresentIllness": "3天前受凉后出现发热、咳嗽、乏力",
  "pastHistory": "无高血压糖尿病史",
  "physicalExam": "体温38.5℃，咽部充血",
  "labResults": "白细胞轻度升高"
}
```

返回：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "recordId": "record001"
  }
}
```

### 7.4 生成病历和分析结果

建议将病历生成和分析合并为一个接口，方便演示。

```text
POST /api/analysis/run
```

请求：

```json
{
  "recordId": "record001"
}
```

返回：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "recordId": "record001",
    "generatedRecord": "完整结构化病历文本",
    "symptoms": ["发热", "咳嗽", "乏力"],
    "medicalTerms": ["上呼吸道感染", "白细胞"],
    "diagnosisTop1": "上呼吸道感染",
    "diagnosisCandidates": ["上呼吸道感染", "流感"],
    "diagnosisReason": "患者存在发热、咳嗽、咽部充血等表现，符合上呼吸道感染特征。",
    "treatmentAdvice": "建议休息、多饮水，必要时完善血常规检查。本结果仅用于课程演示，不替代医生诊断。"
  }
}
```

### 7.5 查询历史记录

```text
GET /api/records
```

返回：

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": "record001",
      "patientName": "张三",
      "gender": "男",
      "age": 45,
      "diagnosisTop1": "上呼吸道感染",
      "createdAt": "2026-07-08 10:00:00"
    }
  ]
}
```

### 7.6 查询单条病历

```text
GET /api/records/{id}
```

返回完整患者输入、生成病历、编辑后病历和分析结果。

### 7.7 编辑保存病历

```text
PUT /api/records/{id}
```

请求：

```json
{
  "editedRecord": "用户修改后的完整病历文本"
}
```

返回：

```json
{
  "code": 200,
  "message": "保存成功",
  "data": {
    "recordId": "record001"
  }
}
```

### 7.8 下载报告

```text
GET /api/reports/{id}/download
```

实现要求：

- 优先导出 `.docx` 或 `.txt`，如果时间允许再导出 PDF。
- 报告内容包括患者信息、生成病历、症状识别、诊断分析、治疗建议和免责声明。
- 如果 PDF 导出困难，可以先用 Word 或纯文本报告保证功能可演示。

## 8. Flask AI 服务接口

### 8.1 健康检查

```text
GET /health
```

返回：

```json
{
  "status": "ok",
  "service": "ai-service"
}
```

### 8.2 分析接口

```text
POST /nlp/analyze
```

请求：

```json
{
  "name": "张三",
  "gender": "男",
  "age": 45,
  "chiefComplaint": "发热咳嗽3天",
  "historyPresentIllness": "3天前受凉后出现发热、咳嗽、乏力",
  "pastHistory": "无高血压糖尿病史",
  "physicalExam": "体温38.5℃，咽部充血",
  "labResults": "白细胞轻度升高"
}
```

返回：

```json
{
  "generatedRecord": "完整结构化病历文本",
  "symptoms": ["发热", "咳嗽", "乏力"],
  "medicalTerms": ["上呼吸道感染", "白细胞"],
  "diagnosisTop1": "上呼吸道感染",
  "diagnosisCandidates": ["上呼吸道感染", "流感"],
  "diagnosisReason": "患者存在发热、咳嗽、咽部充血等表现，符合上呼吸道感染特征。",
  "treatmentAdvice": "建议休息、多饮水，必要时完善血常规检查。本结果仅用于课程演示，不替代医生诊断。"
}
```

## 9. AI 模块实现方案

### 9.1 文本预处理

输入：

- 主诉。
- 现病史。
- 既往史。
- 体格检查。
- 检查结果。

处理步骤：

1. 合并文本。
2. 去除 HTML 标签、特殊符号和多余空格。
3. 标准化常见表达。
4. 同义词替换，例如发烧 -> 发热。
5. jieba 分词。
6. 去停用词。
7. 输出 `cleanText` 和 `tokens`。

### 9.2 症状识别

方式：

- 症状词典匹配。
- 同义词映射。
- 简单规则补充。

示例：

```text
发烧 -> 发热
咳痰 -> 咳嗽
拉肚子 -> 腹泻
嗓子疼 -> 咽痛
```

输出：

```json
["发热", "咳嗽", "乏力"]
```

### 9.3 医学术语抽取

方式：

- 医学术语词典匹配。
- 常见检查指标识别。
- 疾病名称识别。

术语示例：

```text
上呼吸道感染
流感
急性胃肠炎
咽炎
白细胞
血常规
体温
血压
```

说明：

- 答辩中可以说明“参考 SNOMED CT 的术语标准化思想，但项目中使用简化词典映射实现”。

### 9.4 诊断辅助分析

优先实现规则打分，保证 demo 稳定。

示例规则：

```text
上呼吸道感染：
  发热 + 咳嗽 + 咽痛 + 咽部充血

流感：
  高热 + 乏力 + 肌肉酸痛 + 咳嗽

急性胃肠炎：
  腹痛 + 腹泻 + 恶心 + 呕吐

咽炎：
  咽痛 + 咽部充血 + 咳嗽

高血压：
  血压升高 + 头痛 + 头晕
```

输出：

- 得分最高疾病作为 `diagnosisTop1`。
- 得分前 2-3 个疾病作为 `diagnosisCandidates`。
- 用命中的症状生成 `diagnosisReason`。

如果时间允许，再加入：

- TF-IDF 特征。
- LogisticRegression / SVM / Naive Bayes 分类模型。
- 输出准确率和混淆矩阵作为答辩材料。

### 9.5 病历生成

采用模板生成。

模板结构：

```text
一、基本信息
姓名：{name}
性别：{gender}
年龄：{age}

二、主诉
{chiefComplaint}

三、现病史
{historyPresentIllness}

四、既往史
{pastHistory}

五、体格检查
{physicalExam}

六、辅助检查
{labResults}

七、初步诊断
{diagnosisTop1}

八、处理建议
{treatmentAdvice}

九、说明
本系统结果仅用于课程演示和辅助分析，不替代医生诊断。
```

### 9.6 治疗建议生成

根据诊断标签从模板中取建议。

示例：

```json
{
  "上呼吸道感染": "建议休息、多饮水，注意体温变化，必要时完善血常规检查。本结果仅用于课程演示，不替代医生诊断。",
  "流感": "建议注意隔离休息，监测体温，必要时到医院进一步检查。本结果仅用于课程演示，不替代医生诊断。",
  "急性胃肠炎": "建议清淡饮食，注意补液，如腹泻或呕吐加重应及时就医。本结果仅用于课程演示，不替代医生诊断。"
}
```

## 10. 前端页面设计

### 10.1 登录页

路径：

```text
/login
```

功能：

- 输入用户名和密码。
- 调用 `/api/auth/login`。
- 登录成功跳转到患者录入页。

默认账号：

```text
admin / 123456
```

### 10.2 患者录入页

路径：

```text
/patients/new
```

功能：

- 录入患者基本信息。
- 表单校验。
- 提交患者信息。
- 点击“生成病历与分析”后跳转结果页。

字段：

- 姓名。
- 性别。
- 年龄。
- 主诉。
- 现病史。
- 既往史。
- 体格检查。
- 检查结果。

### 10.3 结果页

路径：

```text
/records/:id
```

功能：

- 展示生成病历。
- 展示症状识别结果。
- 展示医学术语。
- 展示初步诊断。
- 展示候选诊断。
- 展示诊断依据。
- 展示治疗建议。
- 支持编辑病历。
- 支持保存。
- 支持下载报告。

### 10.4 历史记录页

路径：

```text
/records
```

功能：

- 展示历史病历列表。
- 按患者姓名、诊断、时间展示。
- 点击查看详情。
- 支持下载报告。

### 10.5 页面导航

建议左侧或顶部导航：

```text
患者录入
历史记录
退出登录
```

## 11. 后端实现重点

### 11.1 Controller 层

建议控制器：

- `AuthController`
- `PatientController`
- `RecordController`
- `AnalysisController`
- `ReportController`

### 11.2 Service 层

建议服务：

- `AuthService`
- `PatientRecordService`
- `AnalysisService`
- `AiClientService`
- `ReportService`

### 11.3 Repository 层

建议仓库：

- `UserRepository`
- `PatientRecordRepository`
- `AnalysisResultRepository`
- `ReportFileRepository`

### 11.4 DTO

建议 DTO：

- `LoginRequest`
- `LoginResponse`
- `PatientInputRequest`
- `AnalysisResponse`
- `RecordListItemResponse`
- `ApiResponse`

### 11.5 Flask 调用失败兜底

如果 Flask 服务没启动，SpringBoot 不应崩溃。返回：

```json
{
  "code": 500,
  "message": "AI 分析服务暂不可用，请确认 Flask 服务已启动",
  "data": null
}
```

## 12. 本地启动方式

### 12.1 启动 MongoDB

如果本机已安装 MongoDB：

```bash
mongod
```

或使用 MongoDB Compass 连接：

```text
mongodb://localhost:27017
```

### 12.2 启动 Flask AI 服务

```bash
cd ai-service
pip install -r requirements.txt
python app.py
```

服务地址：

```text
http://localhost:5000
```

健康检查：

```text
http://localhost:5000/health
```

### 12.3 启动 SpringBoot 后端

```bash
cd backend
mvn spring-boot:run
```

服务地址：

```text
http://localhost:8080
```

### 12.4 启动 React 前端

```bash
cd frontend
npm install
npm run dev
```

访问：

```text
http://localhost:5173
```

## 13. 开发阶段计划

### 阶段一：基础框架

目标：三个服务都能启动。

前端：

- 搭建 React + Vite。
- 配置 Ant Design。
- 配置路由。
- 建立页面空壳。

后端：

- 搭建 SpringBoot。
- 配置 MongoDB。
- 写统一返回结构。
- 写登录接口。

AI 服务：

- 搭建 Flask。
- 写 `/health`。
- 写 `/nlp/analyze` 的假数据返回。

验收：

- `localhost:5173` 能打开页面。
- `localhost:8080/api/auth/login` 能返回登录结果。
- `localhost:5000/health` 能返回 ok。

### 阶段二：患者录入和病历生成

目标：用户录入患者信息后能生成病历文本。

前端：

- 完成患者录入表单。
- 完成表单校验。
- 调用后端提交接口。

后端：

- 保存患者输入到 MongoDB。
- 调用 Flask 分析接口。
- 保存生成病历。

AI 服务：

- 实现病历模板生成。
- 实现基础文本清洗。

验收：

- 输入一条患者信息后，结果页能展示结构化病历。

### 阶段三：症状识别和诊断分析

目标：结果页能展示症状、术语、诊断和建议。

前端：

- 完成分析结果展示组件。
- 展示症状标签、医学术语、诊断、建议。

后端：

- 保存分析结果。
- 查询单条记录时返回完整分析内容。

AI 服务：

- 实现症状词典匹配。
- 实现医学术语抽取。
- 实现规则诊断。
- 实现治疗建议模板。

验收：

- 发热咳嗽样例能识别出发热、咳嗽。
- 腹痛腹泻样例能识别出腹痛、腹泻。
- 不同样例能输出不同诊断建议。

### 阶段四：历史记录、编辑和下载

目标：系统完整可演示。

前端：

- 完成历史记录页。
- 完成病历编辑保存。
- 完成下载按钮。

后端：

- 实现历史记录接口。
- 实现编辑保存接口。
- 实现报告下载接口。

AI 服务：

- 补充 demo 数据对应的规则。

验收：

- 可查看历史病历。
- 可编辑保存病历。
- 可下载报告。

### 阶段五：答辩准备

目标：项目能稳定演示。

需要准备：

- 5-10 条 demo 患者数据。
- 一份演示脚本。
- 一份系统架构图。
- 一份模块分工说明。
- 一份 AI 模块说明。
- 一份备用录屏。

## 14. 测试计划

### 14.1 前端测试

- 登录页账号密码为空时提示。
- 患者姓名为空时提示。
- 年龄不是数字时提示。
- 主诉为空时提示。
- 现病史为空时提示。
- 提交成功后跳转结果页。
- 后端失败时展示错误信息。

### 14.2 后端测试

- 登录接口返回 token。
- 提交患者信息后 MongoDB 有记录。
- 调用 Flask 成功后保存分析结果。
- 查询历史记录能返回列表。
- 查询单条记录能返回完整内容。
- 编辑保存后再次查询能看到修改内容。
- Flask 未启动时返回明确错误。

### 14.3 AI 服务测试

样例一：

```text
发热咳嗽3天，伴乏力，咽部充血，白细胞轻度升高
```

预期：

```text
症状：发热、咳嗽、乏力
诊断：上呼吸道感染 或 流感
```

样例二：

```text
腹痛腹泻1天，伴恶心呕吐
```

预期：

```text
症状：腹痛、腹泻、恶心、呕吐
诊断：急性胃肠炎
```

样例三：

```text
咽痛2天，咳嗽，咽部充血
```

预期：

```text
症状：咽痛、咳嗽
诊断：咽炎 或 上呼吸道感染
```

### 14.4 联调测试

完整流程：

```text
启动 MongoDB
启动 Flask AI 服务
启动 SpringBoot 后端
启动 React 前端
登录
录入患者信息
生成病历
查看分析结果
编辑病历
保存病历
查看历史记录
下载报告
```

## 15. Demo 数据建议

至少准备 10 条数据，覆盖以下疾病：

1. 上呼吸道感染。
2. 流感。
3. 急性胃肠炎。
4. 咽炎。
5. 高血压。

每条数据包括：

- 姓名。
- 性别。
- 年龄。
- 主诉。
- 现病史。
- 既往史。
- 体格检查。
- 检查结果。
- 预期症状。
- 预期诊断。

## 16. 答辩讲解重点

### 16.1 系统整体

- 系统采用前后端分离。
- React 负责用户交互。
- SpringBoot 负责业务接口和数据存储。
- Flask 负责 NLP 和 AI 分析。
- MongoDB 保存患者病历和分析结果。

### 16.2 数据处理

- 先对输入文本做清洗。
- 再做分词和停用词过滤。
- 使用医学词典进行术语抽取。
- 使用症状词典识别症状。

### 16.3 AI 分析

- 采用规则词典和传统机器学习思路。
- 规则诊断保证演示稳定。
- TF-IDF 和分类模型可作为扩展。
- BioBERT / Transformer 作为医学文本理解的参考方向。

### 16.4 医疗标准

- SNOMED CT 用作医学术语标准化思想参考。
- HL7 用作医疗信息交换结构参考。
- 本项目实现简化字段映射，适合课程 demo。

### 16.5 安全说明

- 不使用真实患者数据。
- 不直接连接医院 HIS/EMR。
- 治疗建议仅用于课程演示。
- 系统结果不替代医生诊断。

## 17. 给 AI 工具的开发提示

后续使用 AI 工具辅助编码时，可以直接引用下面这段说明：

```text
请根据项目文档实现一个本地运行的医疗病历生成与分析系统。项目采用 React + Vite + Ant Design 前端，SpringBoot + MongoDB 主后端，Flask Python AI 服务。前端只调用 SpringBoot，SpringBoot 调用 Flask，Flask 返回病历生成和分析结果。系统本地端口为 React 5173、SpringBoot 8080、Flask 5000、MongoDB 27017。请优先保证完整 demo 可运行，不要接入真实医疗系统，不要训练大型模型。AI 分析使用规则词典、jieba、TF-IDF 或传统分类模型实现即可。所有诊断和治疗建议都必须标注仅用于课程演示，不替代医生诊断。
```

如果让 AI 实现前端，可以使用：

```text
请实现 React 前端。页面包括登录页、患者录入页、病历结果页、分析结果展示、历史记录页。使用 Ant Design。所有接口调用 SpringBoot 的 /api 路径。表单字段包括 name、gender、age、chiefComplaint、historyPresentIllness、pastHistory、physicalExam、labResults。结果页展示 generatedRecord、symptoms、medicalTerms、diagnosisTop1、diagnosisCandidates、diagnosisReason、treatmentAdvice，并显示免责声明。
```

如果让 AI 实现 SpringBoot 后端，可以使用：

```text
请实现 SpringBoot 后端。提供 /api/auth/login、/api/patients、/api/analysis/run、/api/records、/api/records/{id}、PUT /api/records/{id}、/api/reports/{id}/download。使用 MongoDB 保存 users、patient_records、analysis_results。后端调用 Flask 的 http://localhost:5000/nlp/analyze 获取 AI 分析结果。所有接口统一返回 {code,message,data}。
```

如果让 AI 实现 Flask AI 服务，可以使用：

```text
请实现 Flask AI 服务。提供 GET /health 和 POST /nlp/analyze。输入患者信息，输出 generatedRecord、symptoms、medicalTerms、diagnosisTop1、diagnosisCandidates、diagnosisReason、treatmentAdvice。使用 jieba、症状词典、医学术语词典和规则打分实现分析。病历生成使用模板。治疗建议使用诊断标签到建议模板的映射。所有结果仅用于课程演示，不替代医生诊断。
```

## 18. 最终交付清单

最终项目目录中应包含：

- React 前端代码。
- SpringBoot 后端代码。
- Flask AI 服务代码。
- MongoDB 使用说明。
- README 启动说明。
- API 文档。
- 数据字段说明。
- AI 模块说明。
- Demo 数据。
- 演示脚本。
- 备用演示录屏。

最终演示必须能完成：

```text
登录
-> 录入患者信息
-> 生成病历
-> 查看症状识别和诊断分析
-> 编辑保存病历
-> 查看历史记录
-> 下载报告
```

## 19. 验收标准

项目视为完成需要满足：

- 本地四个服务能启动。
- 前端页面能正常访问。
- 登录功能可用。
- 患者信息能提交。
- 病历能生成。
- 症状和医学术语能识别。
- 能输出候选诊断和治疗建议。
- 记录能保存到 MongoDB。
- 历史记录能查询。
- 病历能编辑保存。
- 报告能下载。
- 至少有 5 条稳定 demo 数据。
- 答辩时能清楚说明分工、架构、数据处理、AI 方法和系统限制。

## 20. 优先级建议

如果时间紧，按以下顺序完成：

1. Flask AI 服务能返回稳定假数据。
2. SpringBoot 能调用 Flask 并保存 MongoDB。
3. React 能录入并展示结果。
4. Flask 替换成真实规则分析。
5. 增加历史记录。
6. 增加编辑保存。
7. 增加报告下载。
8. 补充 BioBERT、Transformer、SNOMED CT、HL7 的说明材料。

最重要的是保证完整流程可演示，不要把时间全部花在模型训练或复杂部署上。
