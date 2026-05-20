import obspy
import inspect
import numpy as np
from obspy import Trace, Stream, UTCDateTime

print("=" * 70)
print("ObsPy Stream.merge 重叠与缝隙处理逻辑分析")
print("=" * 70)

print("\n" + "=" * 70)
print("一、Stream.merge 核心参数说明")
print("=" * 70)

# 获取关键参数说明
print("\n关键参数:")
print("  method: 重叠处理方法 (0, 1, 2)")
print("  fill_value: 缝隙填充值 (None=masked array)")
print("  interpolation_samples: 过渡样本数")

print("\n" + "=" * 70)
print("二、Trace.__add__ 方法核心逻辑 (merge基于此实现)")
print("=" * 70)

# 查看add方法签名
print("\nTrace.__add__ 方法实现的核心逻辑:")
print("1. 检查Trace ID是否匹配 (net.sta.loc.cha)")
print("2. 检查采样率是否一致")
print("3. 按时间顺序排列两个Trace")
print("4. 处理三种情况: 无重叠、完全重叠、部分重叠")
print("5. 处理缝隙 (gap) 情况")

print("\n" + "=" * 70)
print("三、实际测试 - 时间重叠的处理")
print("=" * 70)

# 创建测试数据
sampling_rate = 100
npts = 500
data1 = np.sin(np.linspace(0, 10, npts))
data2 = np.cos(np.linspace(0, 10, npts)) * 0.5

# Trace A: 0-5秒
tr1 = Trace(data=data1, header={
    "sampling_rate": sampling_rate,
    "starttime": UTCDateTime("2024-01-01T00:00:00"),
    "network": "XX", "station": "TEST", "location": "00", "channel": "BHZ"
})

# Trace B: 3-8秒 (与Trace A有2秒重叠)
tr2 = Trace(data=data2, header={
    "sampling_rate": sampling_rate,
    "starttime": UTCDateTime("2024-01-01T00:00:03"),
    "network": "XX", "station": "TEST", "location": "00", "channel": "BHZ"
})

print(f"\nTrace A: {tr1.stats.starttime} ~ {tr1.stats.endtime}, npts={tr1.stats.npts}")
print(f"Trace B: {tr2.stats.starttime} ~ {tr2.stats.endtime}, npts={tr2.stats.npts}")
print(f"重叠时间: 3s-5s = 2秒")

# 测试不同method的效果
st0 = Stream(traces=[tr1.copy(), tr2.copy()])
st1 = Stream(traces=[tr1.copy(), tr2.copy()])
st2 = Stream(traces=[tr1.copy(), tr2.copy()])

print("\n----- Method 0: 丢弃重叠数据 (与gap同样处理) -----")
st0.merge(method=0, fill_value=None)
tr_merged0 = st0[0]
print(f"合并后: {tr_merged0.stats.starttime} ~ {tr_merged0.stats.endtime}")
print(f"npts={tr_merged0.stats.npts}")
print(f"是否为masked array: {np.ma.is_masked(tr_merged0.data)}")
if np.ma.is_masked(tr_merged0.data):
    print(f"masked点数: {np.sum(tr_merged0.data.mask)}")

print("\n----- Method 1: 取平均值 (interpolation_samples=0) -----")
st1.merge(method=1, interpolation_samples=0, fill_value=None)
tr_merged1 = st1[0]
print(f"合并后: {tr_merged1.stats.starttime} ~ {tr_merged1.stats.endtime}")
print(f"npts={tr_merged1.stats.npts}")

print("\n重叠区域数据对比:")
overlap_start_idx = int(3 * sampling_rate)  # 重叠开始位置
overlap_end_idx = int(5 * sampling_rate)    # 重叠结束位置
print(f"  重叠位置: 样本 #{overlap_start_idx} - #{overlap_end_idx}")
print(f"  Trace A 数据[:3]: {tr1.data[overlap_start_idx:overlap_start_idx+3]}")
print(f"  Trace B 数据[:3]: {tr2.data[overlap_start_idx-300:overlap_start_idx-300+3]}")  
print(f"  合并后数据[:3]: {tr_merged1.data[overlap_start_idx:overlap_start_idx+3]}")
print(f"  平均值验证: {(tr1.data[overlap_start_idx] + tr2.data[0])/2} = {tr_merged1.data[overlap_start_idx]}")

print("\n----- Method 2: 线性插值过渡 -----")
st2.merge(method=2, interpolation_samples=10, fill_value=None)
tr_merged2 = st2[0]
print(f"合并后: {tr_merged2.stats.starttime} ~ {tr_merged2.stats.endtime}")
print(f"npts={tr_merged2.stats.npts}")

print("\n" + "=" * 70)
print("四、实际测试 - 缝隙 (gap) 处理")
print("=" * 70)

# 创建有缝隙的数据
tr_gap1 = Trace(data=data1[:300], header={
    "sampling_rate": sampling_rate,
    "starttime": UTCDateTime("2024-01-01T00:00:00"),
    "network": "XX", "station": "GAP", "location": "00", "channel": "BHZ"
})

tr_gap2 = Trace(data=data2[:300], header={
    "sampling_rate": sampling_rate,
    "starttime": UTCDateTime("2024-01-01T00:00:05"),  # 2秒 gap
    "network": "XX", "station": "GAP", "location": "00", "channel": "BHZ"
})

print(f"\nTrace 1: {tr_gap1.stats.starttime} ~ {tr_gap1.stats.endtime}")
print(f"Trace 2: {tr_gap2.stats.starttime} ~ {tr_gap2.stats.endtime}")
print(f"Gap大小: {tr_gap2.stats.starttime - tr_gap1.stats.endtime:.2f} 秒 = {int((tr_gap2.stats.starttime - tr_gap1.stats.endtime) * sampling_rate)} 个样本")

# 测试gap处理
st_gap0 = Stream(traces=[tr_gap1.copy(), tr_gap2.copy()])
st_gap1 = Stream(traces=[tr_gap1.copy(), tr_gap2.copy()])

print("\n----- fill_value=None (创建 masked array) -----")
st_gap0.merge(method=0, fill_value=None)
tr_gap_merged0 = st_gap0[0]
print(f"合并后 npts={tr_gap_merged0.stats.npts}")
print(f"是否为masked array: {np.ma.is_masked(tr_gap_merged0.data)}")
if np.ma.is_masked(tr_gap_merged0.data):
    print(f"masked点数 (gap): {np.sum(tr_gap_merged0.data.mask)}")

print("\n----- fill_value=0 (用0填充) -----")
st_gap1.merge(method=0, fill_value=0)
tr_gap_merged1 = st_gap1[0]
print(f"合并后 npts={tr_gap_merged1.stats.npts}")
print(f"gap区域值: {tr_gap_merged1.data[300:320]}")  # 查看gap区域

print("\n" + "=" * 70)
print("五、自定义合并策略")
print("=" * 70)

print("\n1. 检测缝隙分布:")
st_gap = Stream(traces=[tr_gap1.copy(), tr_gap2.copy()])
gaps = st_gap.get_gaps()
print(f"检测到 {len(gaps)} 个缝隙")
for gap in gaps:
    print(f"  {gap[0]}.{gap[1]}.{gap[2]}.{gap[3]}: {gap[4]} ~ {gap[5]}, 长度={gap[6]:.3f}s")

print("\n2. 手动处理重叠 (示例: 取第一个Trace的数据) -----")
tr_a = tr1.copy()
tr_b = tr2.copy()

# 手动合并 - 重叠部分取第一个Trace
overlap_start = max(tr_a.stats.starttime, tr_b.stats.starttime)
overlap_end = min(tr_a.stats.endtime, tr_b.stats.endtime)

# 按时间对齐
if tr_a.stats.starttime < tr_b.stats.starttime:
    tr_first, tr_second = tr_a, tr_b
else:
    tr_first, tr_second = tr_b, tr_a

print(f"第一个Trace: {tr_first.stats.starttime} ~ {tr_first.stats.endtime}")
print(f"第二个Trace: {tr_second.stats.starttime} ~ {tr_second.stats.endtime}")

print("\n3. 自定义策略示例: 保留后到达的Trace (更新的数据)")
print("   或者使用 Stream.select() + 手动处理")

print("\n4. 使用 split() 重新分割有缝隙的数据")
st = Stream(traces=[tr_gap1.copy(), tr_gap2.copy()])
st.merge(method=0, fill_value=None)
print(f"合并后 Trace 数: {len(st)}")
st_split = st.split()
print(f"split后 Trace 数: {len(st_split)}")

print("\n" + "=" * 70)
print("总结")
print("=" * 70)
print("""
【重叠处理】
Method 0: 丢弃重叠数据 → 创建masked array（与gap同样处理）
Method 1: 重叠区域取平均值 → 平滑过渡
Method 2: 线性插值过渡 → 可选interpolation_samples控制过渡范围

【缝隙处理】
fill_value=None → 创建 NumPy masked array，gap位置被mask
fill_value=number → 用指定数值填充gap区域
注意: gap和overlap在method=0时都会产生mask

【自定义策略】
1. 使用 Stream.get_gaps() 检测缝隙/重叠位置
2. 手动循环合并Trace，在重叠处应用自定义逻辑（如加权、丢弃旧数据等）
3. 先merge(method=0)得到masked array，再手动处理mask区域
4. 使用 split() 将合并后的masked array重新分割为多个Trace
""")
