# ObsPy Stream.merge 缓存重叠与缝隙处理逻辑分析

## 一、核心概念

Stream.merge() 是 ObsPy 中用于合并相同ID（net.sta.loc.cha）的Trace对象的方法。当同一条数据流有多个数据段（来自不同文件、不同时间）时，merge可以将它们合并为连续的单个Trace。

---

## 二、时间重叠（Overlap）处理逻辑

### 核心参数：`method`

ObsPy 提供三种内置的重叠处理方法：

| Method | 描述 | 适用场景 |
|--------|------|---------|
| **0** | 丢弃重叠数据（重叠区域mask掉） | 保留原始数据、不需要重叠合并 |
| **1** | 重叠区域取平均值 | 简单平滑过渡，消除跳变 |
| **2** | 线性插值过渡（使用 regression line） | 需要更平滑过渡时 |

---

### Method 0: 丢弃重叠数据（默认）

```
Trace A: AAAAAAAAAAAAAAA
Trace B:         BBBBBBBBBBBBBBBB
合并后:  AAAAAAAA---------BBBBBBBB
```

**实现逻辑：**
1. 识别时间重叠区间
2. 所有重叠样本都标记为 `masked`（无效）
3. 非重叠区域保留原始值
4. 结果是一个 NumPy `MaskedArray`（当 `fill_value=None` 时）

**特点：**
- 重叠区域与 gap 处理方式完全相同
- 数据最保真，但可能丢失有效信息

---

### Method 1: 平均值合并

```
Trace A: AAAAAAAAAAAAAAA  (例如值 0.5, 0.6, 0.7, ...)
Trace B:         BBBBBBBBBBBBBBBB  (例如值 0.3, 0.4, 0.5, ...)
合并后:  AAAAAAAA(0.5*0.5+(0.5+0.3)/2, ...)BBBBBBBB
```

**实现逻辑：**
1. 识别时间重叠区间
2. 对每个重叠样本位置：`merged[i] = (A[i] + B[i]) / 2`
3. `interpolation_samples` 参数可以控制过渡区大小

**特点：**
- 实现简单
- 假设两个数据段质量相同
- 可能引入人工干扰

---

### Method 2: 线性插值过渡

```
          重叠区
        |<--------->|
Trace A: AAAAAAAAAAA
Trace B:         BBBBBBBBB
合并后:  AAAAAA----->BBBBBB
         (平滑过渡)
```

**实现逻辑：**
1. 找到重叠前最后一个有效值（在前面的Trace上）
2. 找到重叠后第一个有效值（在后面的Trace上）
3. 在这两点之间进行线性插值（linear regression）
4. `interpolation_samples` 控制插值样本数

**特点：**
- 过渡更平滑
- 适用于两个数据段有明显偏移的情况

---

## 三、缝隙（Gap）处理逻辑

### 核心参数：`fill_value`

Gap = 两个数据段之间的时间间隔（没有数据的区域）

| fill_value | 结果 | 适用场景 |
|------------|------|---------|
| **None** (默认) | 创建 NumPy MaskedArray | 保留数据真实性，后续需要知道哪里是gap |
| **数值** (如 0, NaN) | 用该数值填充gap | 后续分析需要连续数据 |

---

### Gap 处理流程：

1. **检测 Gap**：`Stream.get_gaps()` 返回所有gap的详细信息
   ```python
   gaps = st.get_gaps()
   # 返回格式: [network, station, location, channel, gap_start, gap_end, gap_duration, samples]
   ```

2. **合并 Gap**：
   ```python
   # 方式1: 创建 MaskedArray
   st.merge(method=0, fill_value=None)
   
   # 方式2: 用0填充
   st.merge(method=0, fill_value=0)
   
   # 方式3: 用NaN填充（后续可以插值）
   st.merge(method=0, fill_value=np.nan)
   ```

3. **拆分 Gap**（将合并后的MaskedArray拆分为多个Trace）：
   ```python
   st.merge(method=0, fill_value=None)
   st_split = st.split()  # 按gap位置拆分为多个Trace
   ```

---

### 重要说明：Overlap vs Gap

在 `method=0` 时，**重叠区域和缝隙区域的处理方式完全相同**，都会被标记为mask。

| 情况 | 处理结果（method=0） |
|------|-------------------|
| 时间重叠 (t1 与 t2 有重叠) | 重叠样本被 mask |
| 时间缝隙 (t1结束 < t2开始) | gap样本被 mask |

这意味着，经过 `method=0` 合并后，你无法从结果中区分原始数据是"重叠"还是"缝隙"——两者都是mask。

---

## 四、Trace.__add__ 核心实现流程

`Stream.merge()` 内部是通过多次调用 `Trace.__add__()` 实现的。两个Trace的合并流程：

```
1. 前置检查
   ├─ 检查 ID 是否匹配 (net.sta.loc.cha)
   ├─ 检查采样率是否一致
   └─ 检查数据类型是否兼容

2. 时间对齐
   ├─ 确定哪个Trace更早（按 starttime 排序）
   └─ 计算相对时间偏移量

3. 情况判断
   ├─ 情况A: 完全不重叠，有gap → 插入gap
   ├─ 情况B: 完全包含（一个在另一个内部）→ 处理重叠
   └─ 情况C: 部分重叠 → 处理重叠区域

4. 数据合并
   ├─ 根据 method 参数选择合并策略
   └─ 创建新的 Trace 对象
```

---

## 五、自定义合并策略

当内置的三种方法不满足需求时，可以采用以下几种自定义策略：

### 策略1：使用 get_gaps() 检测 + 手动处理

```python
def custom_merge(stream):
    """自定义合并：重叠区域保留后面的Trace"""
    st_copy = stream.copy()
    
    # 先检测所有gaps/overlaps
    gaps = st_copy.get_gaps()
    
    for gap in gaps:
        net, sta, loc, cha, t_start, t_end, duration, samples = gap
        
        # 重叠是 negative gap（duration < 0）
        if duration < 0:
            print(f"发现重叠: {net}.{sta} - {abs(duration):.2f}s")
            # 这里可以添加自定义逻辑: 保留第一个，丢弃第二个，或者加权...
    
    # 最后用 method=0 合并
    st_copy.merge(method=0, fill_value=None)
    return st_copy
```

---

### 策略2：先合并得到 MaskedArray，再处理 mask

```python
import numpy as np

def process_merged_mask(trace):
    """处理合并后的mask"""
    if not np.ma.is_masked(trace.data):
        return trace
    
    # 获取mask位置
    mask = trace.data.mask
    
    # 示例1: 对mask区域进行线性插值
    from scipy.interpolate import interp1d
    
    valid_indices = np.where(~mask)[0]
    valid_values = trace.data[valid_indices]
    
    if len(valid_indices) > 1:
        f = interp1d(valid_indices, valid_values, 
                    kind='linear', fill_value='extrapolate')
        
        all_indices = np.arange(len(trace.data))
        trace.data = f(all_indices)
    
    return trace
```

---

### 策略3：实现自己的 Trace 加法器

```python
def weighted_add(tr1, tr2, weight1=0.7, weight2=0.3):
    """加权合并：重叠区按权重合并"""
    # 确保采样率相同
    assert tr1.stats.sampling_rate == tr2.stats.sampling_rate
    
    # 确定时间范围
    sr = tr1.stats.sampling_rate
    total_start = min(tr1.stats.starttime, tr2.stats.starttime)
    total_end = max(tr1.stats.endtime, tr2.stats.endtime)
    total_npts = int((total_end - total_start) * sr) + 1
    
    result_data = np.zeros(total_npts)
    
    # 映射第一个Trace
    offset1 = int((tr1.stats.starttime - total_start) * sr)
    result_data[offset1:offset1+len(tr1.data)] = tr1.data * weight1
    
    # 映射第二个Trace（重叠区域加权）
    offset2 = int((tr2.stats.starttime - total_start) * sr)
    overlap_start = max(offset1, offset2)
    overlap_end = min(offset1+len(tr1.data), offset2+len(tr2.data))
    
    # 非重叠区域直接赋值
    if offset2 > offset1 + len(tr1.data):
        # 有gap
        result_data[offset2:offset2+len(tr2.data)] = tr2.data * weight2
    else:
        # 重叠前的部分
        if overlap_start > offset2:
            result_data[offset2:overlap_start] = tr2.data[:overlap_start-offset2] * weight2
        
        # 重叠区域加权相加
        overlap_len = overlap_end - overlap_start
        tr1_overlap = slice(overlap_start-offset1, overlap_start-offset1+overlap_len)
        tr2_overlap = slice(overlap_start-offset2, overlap_start-offset2+overlap_len)
        result_data[overlap_start:overlap_end] = (
            tr1.data[tr1_overlap] * weight1 + 
            tr2.data[tr2_overlap] * weight2
        )
        
        # 重叠后的部分
        if overlap_end < offset2 + len(tr2.data):
            result_data[overlap_end:offset2+len(tr2.data)] = (
                tr2.data[overlap_end-offset2:] * weight2
            )
    
    result_tr = tr1.copy()
    result_tr.data = result_data
    result_tr.stats.starttime = total_start
    result_tr.stats.npts = total_npts
    
    return result_tr
```

---

### 策略4：按数据质量决定优先级

```python
def quality_based_merge(tr1, tr2, quality_func=None):
    """根据数据质量选择保留哪个Trace的重叠部分"""
    if quality_func is None:
        # 默认质量函数：SNR（信噪比）
        def snr(tr):
            noise = np.std(tr.data[:100])
            signal = np.max(np.abs(tr.data))
            return signal / (noise + 1e-10)
        quality_func = snr
    
    q1 = quality_func(tr1)
    q2 = quality_func(tr2)
    
    # 质量高的获得更高权重
    if q1 > q2:
        return weighted_add(tr1, tr2, weight1=1.0, weight2=0.0)
    else:
        return weighted_add(tr1, tr2, weight1=0.0, weight2=1.0)
```

---

## 六、常见问题与解决方案

### Q1: 合并后出现 unexpected mask？

**原因**：时间重叠或微小gap导致method=0时被mask

**解决方案**：
```python
# 1. 先检测
gaps = st.get_gaps()
print(f"检测到 {len(gaps)} 个gap/overlap")

# 2. 小gap插值（如 < 0.5s）
st.merge(method=1, fill_value=np.nan)
```

---

### Q2: 多段数据反复merge导致数据失真？

**原因**：method=1/2 每次合并都会插值，多次叠加引入误差

**解决方案**：
```python
# 一次性合并，不要分段merge
st = Stream(traces=[tr1, tr2, tr3, tr4])
st.merge(method=1)  # 一次性合并所有Trace
```

---

### Q3: 需要区分 overlap 和 gap 进行不同处理？

**解决方案**：
```python
gaps = st.get_gaps()

# 分离 gap 和 overlap
true_gaps = [g for g in gaps if g[6] > 0]
overlaps = [g for g in gaps if g[6] < 0]

print(f"Gap数: {len(true_gaps)}, 重叠数: {len(overlaps)}")

# 分别处理: gap用插值，overlap取平均值
```

---

## 七、实际应用建议

| 应用场景 | 推荐参数 |
|---------|---------|
| 数据归档（保留原始） | method=0, fill_value=None |
| 连续波形分析（去小gap） | method=1, fill_value=0 或插值 |
| 质量控制（检查数据完整性） | method=0 + get_gaps() |
| 实时数据拼接 | method=1 + 小 interpolation_samples |
| 科研分析（高保真） | method=0 + split() + 手动处理 |

---

## 八、参考资料

1. ObsPy 官方文档: `obspy.core.stream.Stream.merge`
2. ObsPy GitHub Issues: #52, #2622
3. ObsPy 源码: `obspy/core/trace.py` 中 `Trace.__add__` 方法
