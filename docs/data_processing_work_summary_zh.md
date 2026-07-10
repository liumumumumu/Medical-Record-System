# 数据处理与标准化工作总结

## 负责内容

本模块负责医疗数据的采集、整理、标准化、质量检查和分析数据集生成。当前使用 NHANES 2017-2018 公开数据作为项目的数据基础，重点围绕患者基本信息、身体测量、血压、生化指标、血常规、糖化血红蛋白、尿白蛋白/肌酐等检测数据展开。

同时，为了对接当前《前后端与 AI 交接规范》，本模块新增了病例录入字段清洗与标准化部分，负责把前端 lowerCamelCase 字段转换为 AI/NLP 模块使用的 snake_case 字段，并提供症状词典、医学术语词典、停用词、同义词、训练/测试/演示样例数据。

## 数据来源

数据来源为 NHANES 2017-2018 公开数据集，使用了 7 张原始表：

| 表名 | 内容 |
| --- | --- |
| `DEMO_J` | 人口学信息，如年龄、性别、种族等 |
| `BMX_J` | 身体测量，如身高、体重、BMI、腰围等 |
| `BPX_J` | 血压和脉搏数据 |
| `BIOPRO_J` | 生化指标，如血糖、肌酐、尿素氮、胆固醇、甘油三酯、肝功能指标等 |
| `CBC_J` | 血常规指标，如白细胞、红细胞、血红蛋白、血小板等 |
| `GHB_J` | 糖化血红蛋白 |
| `ALB_CR_J` | 尿白蛋白、尿肌酐、尿白蛋白肌酐比 |

所有表通过共同字段 `SEQN` 连接，并在处理后统一命名为 `patient_id`。

## 处理流程

当前数据处理流水线可以通过一条命令复现：

```bash
python scripts/run_pipeline.py
```

流水线包含 5 个步骤：

1. `merge_nhanes.py`：按 `SEQN` 合并 7 张 NHANES 原始表。
2. `standardize_nhanes.py`：筛选常用分析字段，统一字段命名，并生成标准化表。
3. `analyze_data_quality.py`：统计缺失率、基础分布和关键指标异常值。
4. `create_analysis_subsets.py`：生成糖尿病、肾功能、心血管三个方向的分析子集。
5. `validate_outputs.py`：校验关键输出文件的行列数是否符合预期。

## 标准化规则

主要标准化操作包括：

1. 将患者编号 `SEQN` 统一改为 `patient_id`。
2. 将原始字段名改为更易理解的英文 snake_case 字段名。
3. 将性别编码 `RIAGENDR` 映射为 `gender`，其中 `1=male`，`2=female`。
4. 将多次血压测量值计算为平均收缩压 `systolic_bp_mean` 和平均舒张压 `diastolic_bp_mean`。
5. 将极小占位值转换为缺失值，避免影响统计分析。
6. 保留完整标准化表，不在主表中直接删除异常值。

## 当前产物

| 文件 | 说明 | 规模 |
| --- | --- | --- |
| `nhanes_merged.csv` | 原始合并总表 | 9254 行，155 列 |
| `nhanes_standardized.csv` | 标准化分析主表 | 9254 行，34 列 |
| `nhanes_quality_summary.csv` | 每列缺失率和基础统计 | 34 行，13 列 |
| `nhanes_outlier_summary.csv` | 关键检测指标异常值统计 | 9 行，9 列 |
| `nhanes_diabetes_analysis.csv` | 糖尿病方向分析子集 | 5804 行，9 列 |
| `nhanes_kidney_analysis.csv` | 肾功能方向分析子集 | 5798 行，11 列 |
| `nhanes_cardiovascular_analysis.csv` | 心血管方向分析子集 | 5525 行，12 列 |
| `nhanes_analysis_subset_summary.csv` | 三个分析子集的行列数汇总 | 3 行，4 列 |
| `nhanes_output_validation.csv` | 输出文件校验结果 | 8 行，4 列 |

## 病例字段清洗交付物

| 文件 | 说明 |
| --- | --- |
| `docs/data_schema.md` | 前端、后端、数据处理、AI 共同使用的病例字段规范 |
| `docs/clinical_field_dictionary.csv` | 前端字段到标准字段的映射字典 |
| `scripts/preprocess.py` | 病例字段校验、清洗、同义词标准化、token 抽取脚本 |
| `scripts/feature_builder.py` | 基于症状词典和医学术语词典生成关键词特征 |
| `data/resources/symptom_dict.txt` | 症状词典 |
| `data/resources/medical_terms.txt` | 医学术语词典 |
| `data/resources/stopwords.txt` | 停用词表 |
| `data/resources/synonyms.json` | 同义词映射表 |
| `data/clinical_cases/demo_cases.json` | 3 条端到端联调样例：正常、字段不全、附件解析失败 |
| `data/clinical_cases/demo_data.csv` | 10 条脱敏演示样例 |
| `data/clinical_cases/train.csv` | 训练样例数据 |
| `data/clinical_cases/test.csv` | 测试样例数据 |

病例预处理可通过以下命令运行：

```bash
python scripts/preprocess.py
python scripts/feature_builder.py
```

## 数据质量结论

当前标准化表保留了 `9254` 名受试者。由于 NHANES 不同检测模块覆盖人群不同，部分检测指标存在缺失，这是该数据集的正常情况。

主要观察：

1. BMI 缺失率约为 13.50%。
2. 血压相关字段缺失率约为 27%-28%。
3. 生化指标缺失率约为 36%。
4. 糖尿病、肾功能、心血管三个分析方向在删除关键字段缺失后，仍保留 5000 条以上记录。
5. 异常值比例整体较低，异常值统计用于人工复核，不自动删除。

## 可汇报亮点

可以在项目汇报中强调以下几点：

1. 数据不是单病种小样本，而是接近一万人的综合健康检测数据。
2. 数据处理流程可复现，组员只需运行 `python scripts/run_pipeline.py`。
3. 已完成从原始多表数据到标准化主表的转换。
4. 已建立字段字典、清洗报告、质量报告和输出校验结果。
5. 已为后续模型或系统展示准备好三个分析方向的数据子集。

## 后续方向

后续可以基于当前数据继续开展：

1. 糖尿病风险分析：使用血糖、糖化血红蛋白、BMI、年龄、血压等指标。
2. 肾功能风险分析：使用肌酐、尿素氮、尿酸、尿白蛋白肌酐比等指标。
3. 心血管风险分析：使用血压、BMI、胆固醇、甘油三酯、血糖等指标。
4. 可视化展示：绘制缺失率、指标分布、异常值数量、相关性热力图等。
