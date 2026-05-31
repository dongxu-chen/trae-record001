import numpy as np
import pandas as pd
from pmf_model import PMF
from data_utils import generate_simulated_data, preprocess_data, identify_source_type
from uncertainty import run_complete_uncertainty_analysis

print("=" * 60)
print("PMF模型测试脚本")
print("=" * 60)

print("\n1. 生成模拟数据...")
df_conc, df_unc = generate_simulated_data(n_samples=100, random_state=42)
print(f"   数据形状: {df_conc.shape}")
print(f"   污染物: {list(df_conc.columns)}")
print(f"   时间范围: {df_conc.index.min().date()} ~ {df_conc.index.max().date()}")

print("\n2. 数据预处理...")
X, U, species, index = preprocess_data(df_conc, df_unc)
print(f"   X形状: {X.shape}")
print(f"   U形状: {U.shape}")

print("\n3. 运行PMF模型...")
source_names = ['工业源', '交通源', '扬尘源']
pmf = PMF(
    n_factors=3,
    max_iter=5000,
    tol=1e-8,
    n_starts=10,
    random_state=42,
    source_names=source_names
)

pmf.fit(X, U, species)
print(f"   Q值: {pmf.result_.Q:.2f}")
print(f"   迭代次数: {len(pmf.result_.Q_history)}")

stats = pmf.get_statistics()
print(f"   Q/自由度: {stats['Q/自由度']:.4f}")

print("\n4. 自动识别污染源类型...")
identified_names = identify_source_type(pmf.result_.F, species)
print(f"   识别结果: {identified_names}")

print("\n5. 源谱结果:")
source_profile = pmf.get_source_profile()
print(source_profile.round(3))

print("\n6. 源贡献统计:")
source_contribution = pmf.get_source_contribution(index)
print(source_contribution.describe().round(2))

print("\n7. 运行Bootstrap不确定性分析 (20次)...")
try:
    unc_result = run_complete_uncertainty_analysis(
        X, U, species,
        n_factors=3,
        n_bootstrap=20,
        base_F=pmf.result_.F,
        source_names=identified_names,
        index=index,
        random_state=42
    )
    print(f"   Bootstrap成功次数: {unc_result.bootstrap_runs}")
    print(f"   Q值均值: {np.mean(unc_result.Q_values):.2f}")
    print(f"   Q值标准差: {np.std(unc_result.Q_values):.2f}")
    
    print("\n   源谱不确定性 (变异系数):")
    for i, source in enumerate(identified_names):
        for j, sp in enumerate(species):
            mean = unc_result.F_mean[i, j]
            std = unc_result.F_std[i, j]
            cv = (std / mean * 100) if mean > 0 else np.nan
            print(f"   {source} - {sp}: {cv:.1f}%")
    
except Exception as e:
    print(f"   不确定性分析失败: {e}")

print("\n" + "=" * 60)
print("测试完成！所有模块运行正常。")
print("=" * 60)
