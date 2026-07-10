# Medical-Record-System

医疗病历生成与分析系统。

当前 `CYL` 分支主要包含数据处理与标准化相关内容，服务于项目中的患者数据整理、检测指标分析、病例字段清洗、AI 输入标准化和组内联调。

## 数据处理模块

本仓库目前包含两部分数据处理工作：

1. **NHANES 检测指标数据处理**：用于公开健康检测数据的合并、标准化、质量检查和分析子集生成。
2. **病例录入字段预处理**：用于对接前端、后端和 AI 模块，将前端表单字段清洗成 AI/NLP 可直接使用的标准结构。

## 1. NHANES 检测指标数据

### 数据位置

NHANES 2017-2018 原始数据位于：

```text
data/raw/nhanes_2017_2018/
```

当前包含人口学信息、身体测量、血压、生化指标、血常规、糖化血红蛋白、尿白蛋白/肌酐等数据表。

### 运行方式

安装依赖：

```bash
pip install -r requirements.txt
```

推荐使用一条命令运行完整流程：

```bash
python scripts/run_pipeline.py
```

该流水线会按依赖顺序执行以下步骤：

1. 按 `SEQN` 合并 NHANES 多张原始表。
2. 生成标准化分析主表。
3. 生成数据质量统计和异常值检查结果。
4. 生成糖尿病、肾功能、心血管三个分析方向的数据子集。
5. 校验关键输出文件的行列数。

也可以单独运行每一步：

```bash
python scripts/merge_nhanes.py
python scripts/standardize_nhanes.py
python scripts/analyze_data_quality.py
python scripts/create_analysis_subsets.py
python scripts/validate_outputs.py
```

### NHANES 输出文件

```text
data/processed/nhanes_merged.csv
data/processed/nhanes_missing_summary.csv
data/processed/nhanes_standardized.csv
data/processed/nhanes_quality_summary.csv
data/processed/nhanes_outlier_summary.csv
data/processed/nhanes_diabetes_analysis.csv
data/processed/nhanes_kidney_analysis.csv
data/processed/nhanes_cardiovascular_analysis.csv
data/processed/nhanes_analysis_subset_summary.csv
data/processed/nhanes_output_validation.csv
docs/data_quality_report.md
docs/data_processing_work_summary_zh.md
```

其中，`nhanes_merged.csv` 保存原始合并字段，`nhanes_standardized.csv` 保存筛选后的标准化分析字段。质量统计和异常值文件用于检查缺失率、分布和可疑检测值，三个分析子集用于后续建模或可视化展示。

## 2. 病例录入字段预处理

病例预处理模块对照《前后端与 AI 交接规范》，负责将前端 lowerCamelCase 字段转换为 Python AI/NLP 模块使用的 snake_case 字段。

例如：

```text
patientName -> patient_name
chiefComplaint -> chief_complaint
presentIllness -> present_illness
generationNeeds -> generation_needs
```

### 运行方式

```bash
python scripts/preprocess.py
python scripts/feature_builder.py
```

`preprocess.py` 负责病例字段校验、文本清洗、同义词替换、附件解析状态标准化和关键词抽取。

`feature_builder.py` 负责根据症状词典和医学术语词典生成关键词特征表。

### 资源和样例数据

```text
data/resources/symptom_dict.txt
data/resources/medical_terms.txt
data/resources/stopwords.txt
data/resources/synonyms.json
data/clinical_cases/demo_cases.json
data/clinical_cases/demo_data.csv
data/clinical_cases/train.csv
data/clinical_cases/test.csv
docs/data_schema.md
docs/clinical_field_dictionary.csv
```

### 病例预处理输出文件

```text
data/processed/clinical_cases_standardized.json
data/processed/train_keyword_features.csv
data/processed/test_keyword_features.csv
data/processed/demo_data_keyword_features.csv
```

## 3. 测试与验证

运行全部测试：

```bash
python -m unittest discover tests
```

检查 Python 文件能否正常编译：

```bash
python -m compileall scripts tests
```

如果需要同时验证 NHANES 主流水线：

```bash
python scripts/run_pipeline.py
```

## 4. 交接说明

数据处理与标准化负责人需要重点交付以下内容：

- `docs/data_schema.md`：病例字段规范，供前端、后端、AI 共同对照。
- `scripts/preprocess.py`：病例输入清洗与标准化脚本。
- `scripts/feature_builder.py`：关键词特征构建脚本。
- `data/resources/`：症状词典、医学术语词典、停用词和同义词表。
- `data/clinical_cases/`：训练、测试和演示样例数据。
- `data/processed/`：脚本生成后的标准化数据和特征数据。

仓库外另有一份面向组员的交接文档：

```text
D:\MF_xian\数据处理与标准化交接文档.md
```

## 5. 注意事项

- 前端和后端请求字段保持 lowerCamelCase，不要随意改名。
- Python 数据处理和 AI 模块内部统一使用 snake_case。
- 所有 demo、train、test 病例数据均为课程演示用脱敏虚构数据。
- 当前附件解析只定义标准化结构和失败状态，暂不真实解析 PDF、图片或 DOCX。
- 诊断和治疗建议仅用于课程演示辅助，不替代医生诊断。
