import numpy as np
from ase import Atoms
import sys
sys.path.insert(0, '.')
from phonon_calculator import PhononCalculator
from phonon_advanced import (
    QuasiHarmonicApproximation,
    PhononLifetime,
    ThermodynamicProperties
)

print("=" * 70)
print("Testing Advanced Phonon Features")
print("=" * 70)

a = 5.431
atoms = Atoms(
    symbols=['Si', 'Si'],
    cell=[[a, 0, 0], [0, a, 0], [0, 0, a]],
    scaled_positions=[[0, 0, 0], [0.25, 0.25, 0.25]],
    pbc=True
)

supercell_matrix = np.eye(3, dtype=int) * 2
calculator = PhononCalculator(atoms, supercell_matrix=supercell_matrix)

force_constants = PhononCalculator.generate_example_force_constants(atoms, supercell_matrix)
calculator.set_force_constants(force_constants, check_stability=False)

simple_path = [
    (np.array([0, 0, 0]), np.array([0.5, 0, 0]), 20),
    (np.array([0.5, 0, 0]), np.array([0.5, 0.5, 0]), 20),
]
simple_labels = ['Γ', 'X', 'M']

calculator.calculate_band_structure(path=simple_path, labels=simple_labels, npoints=20, use_seekpath=False)
calculator.calculate_dos(mesh=(8, 8, 8))
print("✅ 基础声子计算完成")

print("\n" + "=" * 70)
print("测试 1: Grüneisen 参数计算")
print("=" * 70)

try:
    qha = QuasiHarmonicApproximation(calculator, volume_scales=[0.99, 1.00, 1.01])
    qha.calculate_frequencies_at_volumes(npoints=11, use_seekpath=False)
    qha.calculate_gruneisen_parameters()
    
    temperatures = np.linspace(0, 500, 51)
    alpha, Cv = qha.calculate_thermal_expansion(temperatures, bulk_modulus=100.0)
    
    print(f"✅ Grüneisen参数计算完成")
    avg_gamma = np.mean([np.mean(g) for g in qha.gruneisen_parameters])
    print(f"   平均Grüneisen参数: {avg_gamma:.3f}")
    print(f"   300K热膨胀系数: {alpha[np.argmin(np.abs(temperatures-300))]*1e6:.2f}e-6 K⁻¹")
    
    qha.plot_gruneisen_band_structure(save_path='test_gruneisen.png', show=False)
    print("   Grüneisen图已保存: test_gruneisen.png")
except Exception as e:
    print(f"❌ Grüneisen计算失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("测试 2: 声子寿命与热导率")
print("=" * 70)

try:
    lifetime_calc = PhononLifetime(calculator, gruneisen_params=qha.gruneisen_parameters, average_gamma=1.5)
    lifetime_calc.calculate_lifetimes(temperature=300.0)
    
    kappa, cumulative_kappa = lifetime_calc.calculate_thermal_conductivity(
        temperatures, vsound=6400.0)
    
    print(f"✅ 热导率计算完成")
    print(f"   300K热导率: {kappa[np.argmin(np.abs(temperatures-300))]:.2f} W/mK")
    
    lifetime_calc.plot_lifetimes(temperature=300, save_path='test_lifetimes.png', show=False)
    print("   寿命图已保存: test_lifetimes.png")
    
    lifetime_calc.plot_thermal_conductivity(
        temperatures, cumulative_kappa,
        save_path='test_kappa.png', show=False
    )
    print("   热导率图已保存: test_kappa.png")
    
except Exception as e:
    print(f"❌ 热导率计算失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("测试 3: 热力学性质")
print("=" * 70)

try:
    thermo = ThermodynamicProperties(calculator)
    thermo.calculate_thermodynamic_properties(temperatures)
    thermo.plot_thermodynamic_properties(save_path='test_thermodynamic.png', show=False)
    print("✅ 热力学性质计算完成")
    print("   热力学性质图已保存: test_thermodynamic.png")
except Exception as e:
    print(f"❌ 热力学计算失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("📊 结果摘要")
print("=" * 70)
print(f"材料: 简单立方硅 (Si)")
print(f"晶格常数: {a:.3f} Å")
print(f"温度范围: 0 - 500 K")
print(f"\n300K时的性质:")
idx_300 = np.argmin(np.abs(temperatures - 300))
print(f"  热膨胀系数 α = {alpha[idx_300]*1e6:.2f} × 10⁻⁶ K⁻¹")
print(f"  热容 Cv = {Cv[idx_300]:.2f} J/mol·K")
print(f"  热导率 κ = {kappa[idx_300]:.2f} W/mK")
print(f"  平均Grüneisen参数 γ = {np.mean([np.mean(g) for g in qha.gruneisen_parameters]):.3f}")

print("\n✅ 所有测试完成！")
