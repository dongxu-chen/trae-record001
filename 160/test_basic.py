import numpy as np
import mne
from mne.preprocessing import ICA

print("=" * 50)
print("脑电信号处理工具箱 - 基本功能测试")
print("=" * 50)

print("\n1. 测试MNE-Python导入...")
print(f"   MNE版本: {mne.__version__}")
print("   ✓ MNE导入成功")

print("\n2. 创建模拟EEG数据...")
sfreq = 250
n_channels = 32
n_times = 10000

ch_names = [f'EEG{i:03d}' for i in range(n_channels)]
ch_types = ['eeg'] * n_channels

info = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types=ch_types)
data = np.random.randn(n_channels, n_times) * 1e-6
raw = mne.io.RawArray(data, info)

print(f"   ✓ 创建成功: {n_channels}通道, {n_times}采样点, {sfreq}Hz")

print("\n3. 测试EEG滤波...")
raw_filtered = raw.copy().filter(l_freq=0.1, h_freq=40)
print("   ✓ 滤波完成 (0.1-40 Hz带通)")

print("\n4. 测试ICA拟合...")
ica = ICA(n_components=10, random_state=42, max_iter=200)
ica.fit(raw_filtered)
print(f"   ✓ ICA拟合完成, 提取了{ica.n_components_}个成分")

print("\n5. 测试事件检测...")
events = np.array([[1000, 0, 1], [2000, 0, 2], [3000, 0, 1]])
print(f"   ✓ 创建了{len(events)}个事件")

print("\n6. 测试Epochs提取...")
epochs = mne.Epochs(raw_filtered, events, tmin=-0.2, tmax=0.5, preload=True)
evoked = epochs.average()
print(f"   ✓ 提取了{len(epochs)}个Epochs, 平均生成Evoked数据")

print("\n7. 测试PyQt5导入...")
try:
    from PyQt5.QtWidgets import QApplication
    print("   ✓ PyQt5导入成功")
except ImportError:
    print("   ✗ PyQt5未安装")

print("\n8. 测试pyqtgraph导入...")
try:
    import pyqtgraph as pg
    print("   ✓ pyqtgraph导入成功")
except ImportError:
    print("   ✗ pyqtgraph未安装")

print("\n" + "=" * 50)
print("所有基本功能测试完成!")
print("=" * 50)
print("\n运行主程序: python eeg_toolbox.py")
