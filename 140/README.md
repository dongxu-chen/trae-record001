# Bioinformatics Sequence Alignment Toolkit

一个功能完整的生物序列比对Python工具包，提供全局比对、局部比对、相似度矩阵计算和多种可视化功能。

## 核心功能与优化

### ✅ 1. 带状比对 (Banded Alignment) - 内存优化

解决大规模序列比对内存溢出问题：

```python
from seqalign import NeedlemanWunsch, SmithWaterman

# 带状全局比对
nw_banded = NeedlemanWunsch(match=2, mismatch=-1, gap_open=-2, band_width=20)
aligned1, aligned2, score = nw_banded.align(seq1, seq2)

# 带状局部比对
sw_banded = SmithWaterman(match=2, mismatch=-1, gap_open=-2, band_width=20)
aligned1, aligned2, score = sw_banded.align(seq1, seq2)
```

**优化原理：**
- 仅计算对角线附近的带状区域，而非完整矩阵
- 内存复杂度从 O(n*m) 降低到 O(n*band_width)
- 适用于序列长度差异较小的比对场景

### ✅ 2. 线性罚分 vs 仿射罚分

严格区分两种不同的空位罚分模型：

#### 线性罚分 (Linear Gap Penalty)
```python
# 每个空位罚分相同
nw_linear = NeedlemanWunsch(match=2, mismatch=-1, gap_open=-2, use_affine=False)
aligned1, aligned2, score = nw_linear.align(seq1, seq2)
```
- 公式: Gap(n) = n * gap_open

#### 仿射罚分 (Affine Gap Penalty)
```python
# 空位开启和延伸分别罚分
nw_affine = NeedlemanWunsch(match=2, mismatch=-1, gap_open=-5, 
                             gap_extend=-1, use_affine=True)
aligned1, aligned2, score = nw_affine.align(seq1, seq2)
```
- 公式: Gap(n) = gap_open + (n-1) * gap_extend
- 更符合生物学实际：首空位罚分重，后续空位罚分轻

### ✅ 3. 相似度矩阵强制对称

确保相似度矩阵对称性（取最大值）：

```python
from seqalign import SimilarityMatrix

# 强制对称（默认）
sim_symm = SimilarityMatrix(alignment_method="global", enforce_symmetric=True)
matrix = sim_symm.compute_matrix(sequences, names)
print(f"Is symmetric: {sim_symm.is_symmetric()}")  # True

# 非对称模式（用于比较）
sim_asymm = SimilarityMatrix(alignment_method="global", enforce_symmetric=False)
matrix = sim_asymm.compute_matrix(sequences, names)
```

**对称策略：** sim[i,j] = sim[j,i] = max(sim(i→j), sim(j→i))

### ✅ 4. 序列Logo图与热力图可视化

```python
from seqalign import AlignmentVisualizer

visualizer = AlignmentVisualizer(figsize=(12, 8))

# 序列Logo图 (Sequence Logo)
visualizer.plot_sequence_logo(aligned_sequences, title="Sequence Conservation Logo")

# 增强型相似度矩阵热力图
visualizer.plot_similarity_heatmap(similarity_matrix, sequence_names, annot=True)

# 保守性热力图
visualizer.plot_conservation_heatmap(aligned_sequences, window_size=3)

# 点阵图 (Dot Plot)
visualizer.plot_dotplot(seq1, seq2, window_size=2)

# 打分矩阵热力图
visualizer.plot_score_matrix_heatmap(score_matrix, seq1, seq2)

# 带颜色的比对展示
visualizer.plot_alignment_display(aligned1, aligned2, sequence_type='protein')

# 相似度分布直方图
visualizer.plot_similarity_histogram(similarity_matrix, bins=15)
```

## 完整API参考

### NeedlemanWunsch 全局比对
```python
NeedlemanWunsch(match=1, mismatch=-1, gap_open=-2, gap_extend=-1, 
                use_affine=False, substitution_matrix=None, band_width=None)
```
- `match`: 匹配得分 (默认: 1)
- `mismatch`: 错配罚分 (默认: -1)
- `gap_open`: 空位开启罚分 (默认: -2)
- `gap_extend`: 空位延伸罚分（仅仿射模式，默认: -1）
- `use_affine`: 使用仿射罚分（默认: False）
- `substitution_matrix`: 替换矩阵（默认: BLOSUM62）
- `band_width`: 带宽，None表示完整矩阵（默认: None）

### SmithWaterman 局部比对
```python
SmithWaterman(match=2, mismatch=-1, gap_open=-2, gap_extend=-1,
              use_affine=False, substitution_matrix=None, band_width=None)
```
参数同上。

### SimilarityMatrix 相似度矩阵
```python
SimilarityMatrix(alignment_method="global", enforce_symmetric=True, **kwargs)
```
- `alignment_method`: "global" 或 "local"（默认: "global"）
- `enforce_symmetric`: 是否强制对称（默认: True）
- `**kwargs`: 传递给比对算法的参数

**主要方法：**
- `compute_matrix(sequences, names=None)`: 计算相似度矩阵
- `is_symmetric()`: 检查矩阵是否对称
- `get_similarity_stats()`: 获取统计信息
- `find_most_similar(threshold=0.0)`: 查找最相似的序列对
- `print_matrix(decimal_places=3)`: 打印矩阵

### AlignmentVisualizer 可视化
```python
AlignmentVisualizer(figsize=(10, 8))
```
**主要方法：**
- `plot_sequence_logo()`: 序列Logo图
- `plot_conservation_heatmap()`: 保守性热力图
- `plot_similarity_heatmap()`: 相似度矩阵热力图
- `plot_score_matrix_heatmap()`: 打分矩阵热力图
- `plot_alignment_display()`: 彩色比对展示
- `plot_similarity_histogram()`: 相似度分布直方图
- `plot_dotplot()`: 点阵图

## 使用示例

### 基本比对
```python
from seqalign import NeedlemanWunsch, SmithWaterman

seq1 = "HEAGAWGHEE"
seq2 = "PAWHEAE"

# 全局比对 - 仿射罚分
nw = NeedlemanWunsch(match=2, mismatch=-1, gap_open=-5, 
                     gap_extend=-1, use_affine=True)
aligned1, aligned2, score = nw.align(seq1, seq2)
nw.print_alignment()

# 局部比对 - 带状优化
sw = SmithWaterman(match=2, mismatch=-1, gap_open=-2, band_width=10)
aligned1, aligned2, score = sw.align(seq1, seq2)
sw.print_alignment()
```

### 多序列相似度分析
```python
from seqalign import SimilarityMatrix, AlignmentVisualizer

sequences = [
    "MVLSPADKTNVKAAW",
    "MVLSAADKTNVKAAW",
    "MVLSPADKTNVKVVW",
    "MILSPADKTNVKAAW"
]
names = ["HemA", "HemB", "HemC", "HemD"]

# 计算对称相似度矩阵
sim = SimilarityMatrix(alignment_method="global", enforce_symmetric=True)
matrix = sim.compute_matrix(sequences, names)
sim.print_matrix()

# 可视化
visualizer = AlignmentVisualizer()
visualizer.plot_similarity_heatmap(matrix, names, title="Sequence Similarity Matrix")
```

## 项目结构

```
seqalign/
├── __init__.py              # 包入口
├── needleman_wunsch.py      # Needleman-Wunsch全局比对算法
│   ├── 线性罚分实现
│   ├── 仿射罚分实现
│   └── 带状比对优化
├── smith_waterman.py        # Smith-Waterman局部比对算法
│   ├── 线性罚分实现
│   ├── 仿射罚分实现
│   └── 带状比对优化
├── similarity_matrix.py     # 多序列相似度矩阵计算
│   ├── 强制对称（取最大值）
│   └── 统计分析功能
└── visualization.py         # 可视化工具
    ├── 序列Logo图
    ├── 保守性热力图
    ├── 相似度矩阵热力图
    ├── 打分矩阵热力图
    ├── 彩色比对展示
    ├── 相似度分布直方图
    └── 点阵图
```

## 内存优化效果

对于长度为 N 的序列：

| 方法 | 内存复杂度 | 1000长度序列内存 | 说明 |
|------|-----------|----------------|------|
| 标准矩阵 | O(N²) | ~8 MB (float64) | 完整矩阵计算 |
| 带状比对 (w=20) | O(N*w) | ~160 KB | 仅计算对角带 |

**推荐场景：**
- 序列长度相似 → 使用带状比对
- 预期空位较少 → 使用仿射罚分
- 多序列比较 → 使用强制对称相似度矩阵

## 测试

运行测试脚本验证功能：

```bash
python simple_test.py          # 基础功能测试
python test_optimizations.py   # 完整优化测试
python example.py              # 使用示例
```

## 依赖

- Python >= 3.7
- NumPy >= 1.21.0
- Biopython >= 1.79
- Matplotlib >= 3.4.0

## 许可证

MIT License
