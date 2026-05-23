# 分子生成 VAE 模型

使用变分自编码器（VAE）生成类药分子 SMILES 字符串的 Python 实现。

## 项目结构

```
.
├── data_utils.py       # SMILES 数据预处理和数据集加载
├── mol_utils.py        # 分子有效性检查和评估指标
├── sa_score.py         # SA Score（可合成性分数）计算
├── model.py            # VAE 模型架构定义
├── train.py            # 训练和生成主脚本
├── requirements.txt    # Python 依赖包
└── README.md           # 项目说明文档
```

## 功能特性

1. **变分自编码器 (VAE)**:
   - 双向 GRU 编码器
   - 单向 GRU 解码器
   - 支持教师强制训练
   - 支持温度采样生成

2. **分子有效性约束**:
   - **价键规则检查**: 验证各原子的价电子数符合化学规则
   - **环大小限制**: 限制环大小在 3-8 个原子之间
   - **芳香性检查**: 验证芳香原子类型合理性
   - RDKit 分子验证

3. **评估指标**:
   - **有效性 (Validity)**: 有效分子占生成分子的比例
   - **唯一性 (Uniqueness)**: 有效分子中不重复分子的比例
   - **多样性 (Diversity)**: 基于 Morgan 指纹的 Tanimoto 相似性计算
   - **SA Score**: 可合成性分数（1-10，越低越易合成）

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 训练模型

```bash
python train.py --epochs 50 --batch_size 64 --num_molecules 5000
```

### 仅生成分子（需预训练模型）

```bash
python train.py --generate_only --load_model checkpoints/best_model.pt --num_generate 100
```

### 主要参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--batch_size` | 64 | 批大小 |
| `--epochs` | 50 | 训练轮数 |
| `--lr` | 1e-3 | 学习率 |
| `--embed_size` | 256 | 词嵌入维度 |
| `--hidden_size` | 512 | GRU 隐藏层维度 |
| `--latent_dim` | 256 | 潜在空间维度 |
| `--num_layers` | 2 | GRU 层数 |
| `--num_molecules` | 5000 | 训练集分子数量 |
| `--kl_weight` | 0.1 | KL 散度权重 |
| `--temperature` | 1.0 | 生成时的采样温度 |
| `--num_generate` | 100 | 生成分子数量 |

## 模块说明

### data_utils.py

- `SmilesTokenizer`: SMILES 字符串的分词器，支持原子、化学键、结构符号等
- `ZincDataset`: PyTorch Dataset 封装
- `download_zinc_small`: 下载/生成小型 ZINC 风格数据集

### mol_utils.py

- `check_valency`: 检查价键规则
- `check_ring_sizes`: 检查环大小（默认 3-8）
- `is_valid_molecule`: 综合有效性检查
- `calculate_validity`: 计算有效性比例
- `calculate_uniqueness`: 计算唯一性
- `calculate_diversity`: 基于 Morgan 指纹计算多样性

### sa_score.py

- `calculateSAScore`: 计算单个分子的 SA 分数
- `calculate_average_sa_score`: 计算分子集合的平均 SA 分数

### model.py

- `Encoder`: VAE 编码器（双向 GRU）
- `Decoder`: VAE 解码器（单向 GRU）
- `MoleculeVAE`: 完整 VAE 模型
- `vae_loss`: VAE 损失函数（重构损失 + KL 散度）

## 评估指标说明

1. **有效性 (Validity)**: 
   - 范围: 0-1
   - 越高表示生成的分子中有效分子越多

2. **唯一性 (Uniqueness)**:
   - 范围: 0-1
   - 越高表示有效分子中重复越少

3. **多样性 (Diversity)**:
   - 范围: 0-1
   - 基于 Tanimoto 相似性，1 表示完全不相似

4. **SA Score**:
   - 范围: 1-10
   - 分数越低表示分子越容易合成
   - 通常认为 < 6 的分子具有较好的可合成性

## 参考资料

- [Grammar Variational Autoencoder](https://arxiv.org/abs/1703.01925)
- [Molecular Generation with Recurrent Neural Networks](https://arxiv.org/abs/1701.01329)
- [RDKit Documentation](https://www.rdkit.org/docs/)
- [SA Score Implementation](http://www.jcheminf.com/content/1/1/8)
