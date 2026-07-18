# Transformer 对比实验报告：BERT 微调 vs TF-IDF + 逻辑回归

> 实验日期：2026-07-16。目的：用真实实验回答"为什么线上采用 TF-IDF + 逻辑回归而不是 Transformer"，替代纯口头论证。实验只做对比，不改变线上推理链路。

## 1. 实验设置（严格对齐，保证公平）

两个模型使用**完全相同**的数据与评估协议：

| 项 | 设置 |
| --- | --- |
| 数据 | IMCS-21 官方 train/dev/test 划分（1,358 / 445 / 453），复用 `scripts/train_model.py` 的同一个 `load_split()`，五类标签、文本拼接方式逐字节一致 |
| 类别不均衡处理 | 两者都用平衡类别权重（sklearn `class_weight="balanced"` ↔ PyTorch 加权 CrossEntropyLoss，公式同为 `n_samples / (n_classes × bincount)`） |
| 随机种子 | 均为 42 |
| 模型选择 | BERT 按验证集 macro-F1 选最优 epoch（第 5 轮），最终只在测试集上报告一次 |

BERT 侧配置：`bert-base-chinese`（1.02 亿参数）+ 5 类分类头；max_length 256（覆盖 99% 样本）、batch 16、lr 2e-5、AdamW + 10% 线性 warmup、fp16、5 epochs。复现命令：`python scripts/train_transformer.py`。

## 2. 结果

### 2.1 总体指标（IMCS-21 官方测试集，453 条）

| 指标 | TF-IDF + 逻辑回归（线上） | BERT 微调 | 差异 |
| --- | ---: | ---: | ---: |
| Accuracy | 0.8366 | **0.8433** | +0.67 pt（多判对 3 条 / 453） |
| Macro-F1 | 0.8491 | **0.8522** | +0.31 pt |
| 验证集 Accuracy | 0.8404 | 0.8966 | BERT 验证/测试落差 5.3 pt，小样本方差更大 |

### 2.2 逐类 F1

| 类别 | TF-IDF+LR | BERT | 结论 |
| --- | ---: | ---: | --- |
| 上呼吸道感染 | **0.6772** | 0.6591 | BERT 反而更差 |
| 便秘 | 0.9545 | 0.9545 | 持平 |
| 支气管炎 | 0.7421 | **0.7577** | BERT 略好 |
| 普通感冒 | 0.9271 | **0.9490** | BERT 略好 |
| 腹泻 | **0.9444** | 0.9406 | 基本持平 |

两个模型的混淆结构一致：难点都集中在上呼吸道感染 ↔ 支气管炎（症状高度重叠），**BERT 也没有解决这个任务固有歧义**。混淆矩阵见 `models/transformer_confusion_matrix.png`（对照 `models/confusion_matrix.png`）。

### 2.3 工程成本（同机实测，RTX 4070 Laptop / i7-12800HX）

| 项 | TF-IDF + LR | BERT 微调 | 倍数 |
| --- | ---: | ---: | ---: |
| 可训练参数 | 221,195 | 102,271,493 | **462×** |
| 模型体积 | 3.5 MB | 391 MB | 112× |
| 单条推理（CPU） | 1.08 ms | 71.81 ms | **66×** |
| 单条推理（GPU） | — | 8.9 ms | 需要显卡 |
| 训练耗时 | 数秒 | 68.8 s（GPU） | — |
| 运行时依赖 | scikit-learn | + torch/transformers（约 3 GB） | — |

## 3. 结论

1. 在 1,358 条训练样本的规模下，BERT 相对 TF-IDF+LR 的提升是**边际的**（accuracy +0.67 pt，即 453 条测试样本多判对 3 条），且在最难的"上呼吸道感染"类上反而退步。
2. 这点提升的代价是 462 倍参数、66 倍 CPU 推理延迟、112 倍模型体积和约 3 GB 的额外依赖，同时 BERT 验证集与测试集之间 5.3 pt 的落差提示小样本下泛化方差更大、结果稳定性更差。
3. 因此线上保留 TF-IDF + 逻辑回归是**经过实验验证的工程决策**，而非能力限制。融合架构中模型层可插拔（`diagnosis_analyzer._model_scores` 只要求"文本进、概率字典出"），当标注数据增长一个量级后，可将该层无缝替换为本实验的微调模型。

> **后续实验补充（同日）**：`augmentation_report.md` 用远程监督弱标签把训练集扩到 3,858 条后，BERT 提升到 0.8609 / 0.8698（+2.1 pt），而线性基线几乎不受益——印证"BERT 的优势要靠更多数据兑现"。本报告"边际提升"的结论对应纯 1,358 条金标条件。

## 4. 局限

- 单次训练、单一超参组合，未做多种子/多超参搜索；BERT 上限可能略高于本文数字（如换 MacBERT/MedBERT、加数据增强），但不改变量级结论。
- 该实验只覆盖核心五类；其余 15 个扩展病种没有标注数据，无论哪种模型都必须依赖知识检索 + 规则层。

## 5. 产物清单

```text
scripts/train_transformer.py                    实验脚本（可复现，种子 42）
models/transformer_metrics.json                 指标、训练曲线、延迟实测
models/transformer_classification_report.txt   逐类精确率/召回/F1
models/transformer_confusion_matrix.png         混淆矩阵（答辩可展示）
models/transformer/                             微调权重（391MB，不入库，可重训）
```
