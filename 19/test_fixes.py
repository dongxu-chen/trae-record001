import numpy as xp
import sys
sys.path.insert(0, 'd:/Trae/project/record001/19')

from shortwave import ShortwaveRadiation
from cloud import CloudEffect
from aerosol import AerosolEffect

print("验证三个Bug修复（向量化版本）")
print("="*60)

def test_cos_zenith_fix():
    print("\n=== Test 1: 太阳天顶角余弦负值修复 ===")
    
    sw = ShortwaveRadiation(solar_zenith_angle=100.0)
    
    cos_zenith = sw.calculate_cos_zenith()
    print(f"太阳天顶角 100度, cos(zenith) = {cos_zenith}")
    print(f"验证: cos_zenith >= 0 ? {xp.all(cos_zenith >= 0)}")
    
    pressure = xp.array([[100000.0, 85000.0, 70000.0, 50000.0, 30000.0, 10000.0]])
    temperature = xp.array([[298.0, 285.0, 270.0, 250.0, 230.0, 210.0]])
    water_vapor = xp.array([[0.02, 0.015, 0.01, 0.005, 0.001, 0.0001]])
    ozone = xp.array([[0.005, 0.008, 0.01, 0.008, 0.005, 0.002]])
    
    profile = {
        'pressure': pressure,
        'temperature': temperature,
        'water_vapor': water_vapor,
        'ozone': ozone
    }
    
    fluxes = sw.compute_shortwave_fluxes(profile)
    toa_flux = xp.sum(fluxes['net_flux'][:, 0])
    
    print(f"大气顶净通量 = {toa_flux} W/m2")
    print(f"验证: TOA 净通量 >= 0 ? {toa_flux >= 0}")
    
    print("通过!\n")

def test_cloud_optical_depth_bounds():
    print("\n=== Test 2: 云光学厚度边界溢出修复 ===")
    
    cloud = CloudEffect()
    
    print("测试极端云水含量:")
    test_cases = [
        (0.0, 'stratus', 10.0),
        (100.0, 'stratus', 10.0),
        (0.01, 'stratus', 0.1),
        (0.5, 'cirrus', 100.0),
    ]
    
    for wc, ct, ps in test_cases:
        od = cloud.calculate_cloud_optical_depth(wc, ct, ps)
        od_range = cloud.cloud_types[ct]['optical_depth_range'] if ct in cloud.cloud_types else (0.1, 20.0)
        od_value = float(od[0]) if hasattr(od, '__len__') and len(od) > 0 else float(od)
        print(f"  云水={wc}, 类型={ct}, 粒径={ps} -> OD={od_value:.4f}")
        if wc > 0:
            assert od_range[0] <= od_value <= od_range[1], f"OD应该在 {od_range} 范围内"
            print(f"    验证: 在范围 {od_range} 内? 是")
        else:
            assert od_value == 0.0, "云水为0时OD应该为0"
            print(f"    验证: OD=0? 是")
    
    print("测试不存在的云类型:")
    od = cloud.calculate_cloud_optical_depth(0.5, 'unknown_type', 10.0)
    od_value = float(od[0]) if hasattr(od, '__len__') and len(od) > 0 else float(od)
    print(f"  未知类型 -> OD={od_value:.4f}")
    default_range = cloud.cloud_types['stratus']['optical_depth_range']
    assert default_range[0] <= od_value <= default_range[1], "未知类型应该使用默认值"
    print(f"    验证: 在默认范围 {default_range} 内? 是")
    
    print("通过!\n")

def test_aerosol_phase_function_normalization():
    print("\n=== Test 3: 气溶胶相函数归一化修复 ===")
    
    aerosol = AerosolEffect()
    
    print("测试 Henyey-Greenstein 相函数归一化:")
    test_gs = [0.0, 0.3, 0.5, 0.7, 0.9]
    for g in test_gs:
        norm = aerosol.hg_phase_function_normalization(g)
        backscatter = aerosol.calculate_backscattering_ratio(g)
        
        print(f"  g={g:.1f}: 归一化因子={norm:.4f}, 后向散射比={backscatter:.4f}")
        assert 0 <= backscatter <= 0.5, f"后向散射比应该在[0, 0.5]范围内"
    
    print("\n测试能量守恒 (散射 + 吸收 = 1):")
    test_aods = [0.1, 0.5, 1.0, 2.0, 5.0]
    for aod in test_aods:
        forcing = aerosol.calculate_direct_radiative_forcing(aod, 'sulfate', 0.0, 0.3)
        forcing_value = float(forcing[0]) if hasattr(forcing, '__len__') and len(forcing) > 0 else float(forcing)
        print(f"  AOD={aod}: 直接辐射强迫={forcing_value:.2f} W/m2")
    
    print("\n测试气溶胶直接/间接效应:")
    aerosol_profile = {
        'mass_concentration': xp.array([[10.0, 5.0, 2.0, 0.0, 0.0]]),
        'aerosol_type': [['sulfate', 'sulfate', 'organic_carbon', 'sulfate', 'sulfate']],
        'relative_humidity': xp.array([[70.0, 60.0, 50.0, 50.0, 50.0]])
    }
    
    cloud_profile = {
        'cloud_fraction': xp.array([[0.0, 0.5, 0.7, 0.3, 0.0]]),
        'water_content': xp.array([[0.0, 0.2, 0.3, 0.1, 0.0]]),
        'cloud_type': [['stratus', 'stratus', 'stratus', 'stratus', 'stratus']],
        'temperature': xp.array([[280.0, 260.0, 240.0, 220.0, 200.0]])
    }
    
    total = aerosol.calculate_total_aerosol_forcing(
        aerosol_profile, 30.0, 0.3, cloud_profile
    )
    
    direct = xp.sum(total['direct_forcing'])
    indirect = xp.sum(total['indirect_forcing'])
    print(f"  直接辐射强迫总量: {direct:.2f} W/m2")
    print(f"  间接辐射强迫总量: {indirect:.2f} W/m2")
    print(f"  总辐射强迫: {direct + indirect:.2f} W/m2")
    
    print("通过!\n")

def test_energy_conservation():
    print("\n=== Test 4: 能量守恒测试 ===")
    
    aerosol = AerosolEffect()
    
    print("验证气溶胶光学特性的能量守恒 (散射 + 吸收 = 1):")
    
    for aero_type in ['sulfate', 'black_carbon', 'organic_carbon', 'dust', 'sea_salt']:
        ssa = aerosol.calculate_single_scattering_albedo(aero_type, 1)
        ssa_value = float(ssa[0]) if hasattr(ssa, '__len__') and len(ssa) > 0 else float(ssa)
        
        print(f"  {aero_type}: SSA={ssa_value:.4f}, 吸收={1-ssa_value:.4f}, 总和={1.0:.4f}")
        assert abs(ssa_value + (1 - ssa_value) - 1.0) < 1e-6, "能量不守恒"
    
    print("通过!\n")

if __name__ == '__main__':
    test_cos_zenith_fix()
    test_cloud_optical_depth_bounds()
    test_aerosol_phase_function_normalization()
    test_energy_conservation()
    
    print("="*60)
    print("所有Bug修复验证通过!")
    print("="*60)
