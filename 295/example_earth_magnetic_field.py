import numpy as np
import matplotlib.pyplot as plt
from spherical_harmonics import (
    SphericalHarmonics, generate_grid, generate_gauss_legendre_grid
)


def dipole_magnetic_field(theta, phi, g10=1.0, g11=0.0, h11=0.0):
    l_max = 1
    sh = SphericalHarmonics(l_max=l_max)
    
    B = np.zeros_like(theta, dtype=np.complex128)
    B += g10 * sh.Ylm(1, 0, theta, phi)
    B += g11 * sh.Ylm_real(1, 1, theta, phi)
    B += h11 * sh.Ylm_real(1, -1, theta, phi)
    
    return np.real(B)


def quadrupole_magnetic_field(theta, phi):
    l_max = 2
    sh = SphericalHarmonics(l_max=l_max)
    
    B = np.zeros_like(theta, dtype=np.complex128)
    B += 0.5 * sh.Ylm_real(2, 0, theta, phi)
    B += 0.3 * sh.Ylm_real(2, 1, theta, phi)
    B += 0.2 * sh.Ylm_real(2, -1, theta, phi)
    B += 0.15 * sh.Ylm_real(2, 2, theta, phi)
    B += 0.1 * sh.Ylm_real(2, -2, theta, phi)
    
    return np.real(B)


def earth_like_magnetic_field(theta, phi):
    l_max = 5
    sh = SphericalHarmonics(l_max=l_max)
    
    B = np.zeros_like(theta, dtype=np.complex128)
    
    g_coeffs = {
        (1, 0): 1.0,
        (1, 1): 0.05,
        (2, 0): 0.1,
        (2, 1): 0.08,
        (2, 2): 0.03,
        (3, 0): 0.06,
        (3, 1): 0.04,
        (3, 2): 0.02,
        (3, 3): 0.01,
    }
    
    h_coeffs = {
        (1, -1): 0.03,
        (2, -1): 0.05,
        (2, -2): 0.02,
        (3, -1): 0.03,
        (3, -2): 0.015,
        (3, -3): 0.008,
    }
    
    for (l, m), g in g_coeffs.items():
        B += g * sh.Ylm_real(l, m, theta, phi)
    
    for (l, m), h in h_coeffs.items():
        B += h * sh.Ylm_real(l, m, theta, phi)
    
    return np.real(B)


def example_basic_usage():
    print("=" * 60)
    print("示例1: 基础球面调和函数计算 (稳定递推版)")
    print("=" * 60)
    
    sh = SphericalHarmonics(l_max=4)
    
    theta = np.array([0.0, np.pi/4, np.pi/2, 3*np.pi/4, np.pi])
    phi = np.array([0.0, np.pi/2, np.pi, 3*np.pi/2, 2*np.pi])
    
    print("\nY_0^0 在各点的值:")
    y00 = sh.Ylm(0, 0, theta, phi)
    print(f"  {y00}")
    
    print("\nY_1^0 在各点的值:")
    y10 = sh.Ylm(1, 0, theta, phi)
    print(f"  {y10}")
    
    print("\nY_1^1 在各点的值:")
    y11 = sh.Ylm(1, 1, theta, phi)
    print(f"  {y11}")
    
    print("\n实值球面调和函数 Y_2^2_real:")
    y22_real = sh.Ylm_real(2, 2, theta, phi)
    print(f"  {y22_real}")


def example_gauss_legendre_integration():
    print("\n" + "=" * 60)
    print("示例2: 高斯-勒让德积分精度对比")
    print("=" * 60)
    
    l_max = 6
    sh = SphericalHarmonics(l_max=l_max)
    
    n_theta, n_phi = 16, 32
    
    theta_eq, phi_eq = generate_grid(n_theta, n_phi)
    theta_gl, phi_gl, weights_gl = generate_gauss_legendre_grid(n_theta, n_phi)
    
    def test_func(theta, phi):
        return np.sin(theta) ** 3 * np.cos(phi) ** 2
    
    f_eq = test_func(theta_eq, phi_eq)
    f_gl = test_func(theta_gl, phi_gl)
    
    integral_eq = np.sum(f_eq * np.sin(theta_eq) * (np.pi / n_theta) * (2 * np.pi / n_phi))
    integral_gl = sh.spherical_integral(f_gl, theta_gl, phi_gl, weights_gl)
    
    analytical = 8 * np.pi / 15
    
    print(f"\n解析解: {analytical:.8f}")
    print(f"等间距积分: {integral_eq:.8f}, 误差: {abs(integral_eq - analytical):.2e}")
    print(f"高斯-勒让德积分: {integral_gl:.8f}, 误差: {abs(integral_gl - analytical):.2e}")
    
    print("\n高斯-勒让德积分精度显著提高!")


def example_expansion_reconstruction_gl():
    print("\n" + "=" * 60)
    print("示例3: 高斯-勒让德积分的展开与重建")
    print("=" * 60)
    
    l_max = 8
    sh = SphericalHarmonics(l_max=l_max)
    
    n_theta, n_phi = 32, 64
    theta_grid, phi_grid, weights = generate_gauss_legendre_grid(n_theta, n_phi)
    
    def test_function(theta, phi):
        return np.sin(theta) ** 2 * np.cos(2 * phi) + 0.5 * np.cos(theta)
    
    f = test_function(theta_grid, phi_grid)
    
    print("\n展开系数 (l=0 到 3):")
    coeffs = sh.expand(f, theta_grid, phi_grid, weights)
    
    for l in range(4):
        for m in range(-l, l + 1):
            val = coeffs[l][m]
            if abs(val) > 1e-10:
                print(f"  l={l}, m={m}: {val:.6f}")
    
    print("\n重建并计算误差:")
    f_reconstructed = sh.reconstruct(coeffs, theta_grid, phi_grid)
    error = np.max(np.abs(f - np.real(f_reconstructed)))
    print(f"  最大重建误差: {error:.2e}")
    
    print("\n不同 l_max 的重建误差:")
    for l_recon in [2, 4, 6, 8]:
        f_recon = sh.reconstruct(coeffs, theta_grid, phi_grid, l_max_reconstruct=l_recon)
        error = np.max(np.abs(f - np.real(f_recon)))
        print(f"  l_max={l_recon}: 最大误差 = {error:.2e}")


def example_power_spectrum():
    print("\n" + "=" * 60)
    print("示例4: 功率谱分析")
    print("=" * 60)
    
    l_max = 10
    sh = SphericalHarmonics(l_max=l_max)
    
    n_theta, n_phi = 32, 64
    theta_grid, phi_grid, weights = generate_gauss_legendre_grid(n_theta, n_phi)
    
    f = earth_like_magnetic_field(theta_grid, phi_grid)
    coeffs = sh.expand(f, theta_grid, phi_grid, weights)
    power = sh.power_spectrum(coeffs)
    
    print("\n功率谱 (l=0 到 10):")
    for l in range(l_max + 1):
        print(f"  l={l}: {power[l]:.6f}")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.semilogy(range(l_max + 1), power, 'bo-', linewidth=2)
    ax.set_xlabel('Degree l')
    ax.set_ylabel('Power')
    ax.set_title('Magnetic Field Power Spectrum')
    ax.grid(True)
    plt.savefig('power_spectrum.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("\n功率谱图已保存为 power_spectrum.png")


def example_magnetic_field_analysis():
    print("\n" + "=" * 60)
    print("示例5: 地球磁场模拟与分析")
    print("=" * 60)
    
    l_max = 10
    sh = SphericalHarmonics(l_max=l_max)
    
    n_theta, n_phi = 50, 100
    theta_grid, phi_grid, weights = generate_gauss_legendre_grid(n_theta, n_phi)
    
    B_dipole = dipole_magnetic_field(theta_grid, phi_grid)
    B_quad = quadrupole_magnetic_field(theta_grid, phi_grid)
    B_earth = earth_like_magnetic_field(theta_grid, phi_grid)
    
    print("\n场的统计特性:")
    print(f"  偶极场: 范围 [{B_dipole.min():.3f}, {B_dipole.max():.3f}]")
    print(f"  四极场: 范围 [{B_quad.min():.3f}, {B_quad.max():.3f}]")
    print(f"  类地磁场: 范围 [{B_earth.min():.3f}, {B_earth.max():.3f}]")
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    im1 = axes[0].pcolormesh(phi_grid, theta_grid, B_dipole, cmap='RdBu_r', shading='auto')
    axes[0].set_xlabel('phi')
    axes[0].set_ylabel('theta')
    axes[0].set_title('Dipole Field')
    plt.colorbar(im1, ax=axes[0])
    
    im2 = axes[1].pcolormesh(phi_grid, theta_grid, B_quad, cmap='RdBu_r', shading='auto')
    axes[1].set_xlabel('phi')
    axes[1].set_title('Quadrupole Field')
    plt.colorbar(im2, ax=axes[1])
    
    im3 = axes[2].pcolormesh(phi_grid, theta_grid, B_earth, cmap='RdBu_r', shading='auto')
    axes[2].set_xlabel('phi')
    axes[2].set_title('Earth-like Field')
    plt.colorbar(im3, ax=axes[2])
    
    plt.tight_layout()
    plt.savefig('magnetic_fields.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("\n磁场分布图已保存为 magnetic_fields.png")
    
    coeffs_earth = sh.expand(B_earth, theta_grid, phi_grid, weights)
    
    print("\n前5阶的主导系数:")
    dominant_coeffs = []
    for l in range(6):
        for m in range(-l, l + 1):
            val = coeffs_earth[l][m]
            if abs(val) > 0.01:
                dominant_coeffs.append((l, m, abs(val)))
    
    dominant_coeffs.sort(key=lambda x: -x[2])
    for l, m, mag in dominant_coeffs[:10]:
        print(f"  l={l}, m={m}: |coeff| = {mag:.4f}")


def example_tikhonov_regularization():
    print("\n" + "=" * 60)
    print("示例6: Tikhonov正则化抑制震荡")
    print("=" * 60)
    
    l_max = 12
    sh = SphericalHarmonics(l_max=l_max)
    
    n_theta, n_phi = 64, 128
    theta_grid, phi_grid, weights = generate_gauss_legendre_grid(n_theta, n_phi)
    
    B_true = earth_like_magnetic_field(theta_grid, phi_grid)
    noise = 0.08 * np.random.randn(*B_true.shape)
    B_noisy = B_true + noise
    
    print(f"\n原始场的 RMS: {np.sqrt(np.mean(B_true**2)):.4f}")
    print(f"噪声的 RMS: {np.sqrt(np.mean(noise**2)):.4f}")
    print(f"信噪比: {np.sqrt(np.mean(B_true**2)) / np.sqrt(np.mean(noise**2)):.2f}")
    
    coeffs_no_reg = sh.expand(B_noisy, theta_grid, phi_grid, weights)
    
    lambda_values = [0, 1e-6, 1e-5, 1e-4, 1e-3]
    rmse_values = []
    
    print("\n不同正则化参数的效果:")
    print(f"  {'lambda':>10} {'RMSE':>10} {'高阶功率':>12}")
    print("  " + "-" * 38)
    
    for lam in lambda_values:
        if lam == 0:
            coeffs = coeffs_no_reg
        else:
            coeffs = sh.expand_tikhonov(B_noisy, theta_grid, phi_grid, 
                                        reg_lambda=lam, reg_order=2, weights=weights)
        
        B_recon = np.real(sh.reconstruct(coeffs, theta_grid, phi_grid))
        rmse = np.sqrt(np.mean((B_true - B_recon) ** 2))
        rmse_values.append(rmse)
        
        power = sh.power_spectrum(coeffs)
        high_l_power = np.sum(power[8:])
        
        print(f"  {lam:>10.0e} {rmse:>10.4f} {high_l_power:>12.6f}")
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    im1 = axes[0, 0].pcolormesh(phi_grid, theta_grid, B_true, cmap='RdBu_r', shading='auto')
    axes[0, 0].set_title('True Field')
    plt.colorbar(im1, ax=axes[0, 0])
    
    im2 = axes[0, 1].pcolormesh(phi_grid, theta_grid, B_noisy, cmap='RdBu_r', shading='auto')
    axes[0, 1].set_title('Noisy Field')
    plt.colorbar(im2, ax=axes[0, 1])
    
    B_recon_no_reg = np.real(sh.reconstruct(coeffs_no_reg, theta_grid, phi_grid))
    im3 = axes[1, 0].pcolormesh(phi_grid, theta_grid, B_recon_no_reg, cmap='RdBu_r', shading='auto')
    axes[1, 0].set_title('Reconstructed (No Regularization)')
    plt.colorbar(im3, ax=axes[1, 0])
    
    coeffs_reg = sh.expand_tikhonov(B_noisy, theta_grid, phi_grid, 
                                    reg_lambda=1e-5, reg_order=2, weights=weights)
    B_recon_reg = np.real(sh.reconstruct(coeffs_reg, theta_grid, phi_grid))
    im4 = axes[1, 1].pcolormesh(phi_grid, theta_grid, B_recon_reg, cmap='RdBu_r', shading='auto')
    axes[1, 1].set_title('Reconstructed (Tikhonov λ=1e-5)')
    plt.colorbar(im4, ax=axes[1, 1])
    
    plt.tight_layout()
    plt.savefig('regularization_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("\n正则化对比图已保存为 regularization_comparison.png")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.semilogx(lambda_values[1:], rmse_values[1:], 'bo-', linewidth=2)
    ax.set_xlabel('Regularization Parameter λ')
    ax.set_ylabel('RMSE')
    ax.set_title('Tikhonov Regularization: λ vs RMSE')
    ax.grid(True)
    plt.savefig('regularization_curve.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("正则化曲线已保存为 regularization_curve.png")
    
    power_no_reg = sh.power_spectrum(coeffs_no_reg)
    power_reg = sh.power_spectrum(coeffs_reg)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.semilogy(range(l_max + 1), power_no_reg, 'ro-', linewidth=2, label='No Regularization')
    ax.semilogy(range(l_max + 1), power_reg, 'bo-', linewidth=2, label='Tikhonov λ=1e-5')
    ax.set_xlabel('Degree l')
    ax.set_ylabel('Power')
    ax.set_title('Power Spectrum Comparison')
    ax.legend()
    ax.grid(True)
    plt.savefig('power_spectrum_regularization.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("功率谱对比图已保存为 power_spectrum_regularization.png")


def example_high_l_stability():
    print("\n" + "=" * 60)
    print("示例7: 高阶 l 数值稳定性测试 (l=64)")
    print("=" * 60)
    
    l_max = 64
    sh = SphericalHarmonics(l_max=l_max)
    
    print(f"\n测试 l_max = {l_max} (使用稳定递推公式)...")
    
    theta = np.linspace(0.1, np.pi - 0.1, 200)
    phi = np.array([np.pi/4])
    theta = theta[:, np.newaxis]
    phi = np.broadcast_to(phi, theta.shape)
    
    test_cases = [
        (64, 0),
        (64, 16),
        (64, 32),
        (64, 48),
        (64, 64),
    ]
    
    print("\n各高阶球面调和函数的数值范围:")
    for l, m in test_cases:
        y = sh.Ylm(l, m, theta, phi)
        max_abs = np.max(np.abs(y))
        min_abs = np.min(np.abs(y))
        
        if np.any(np.isnan(y)) or np.any(np.isinf(y)):
            print(f"  Y_{l}^{m}: 包含 NaN 或 Inf!")
        else:
            print(f"  Y_{l}^{m}: |Y| ∈ [{min_abs:.4e}, {max_abs:.4e}]")
    
    print("\n稳定递推公式确保了高阶计算的数值稳定性!")


def example_cross_spectrum():
    print("\n" + "=" * 60)
    print("示例8: 交叉谱分析")
    print("=" * 60)
    
    l_max = 8
    sh = SphericalHarmonics(l_max=l_max)
    
    n_theta, n_phi = 32, 64
    theta_grid, phi_grid, weights = generate_gauss_legendre_grid(n_theta, n_phi)
    
    B1 = earth_like_magnetic_field(theta_grid, phi_grid)
    B2 = dipole_magnetic_field(theta_grid, phi_grid)
    
    coeffs1 = sh.expand(B1, theta_grid, phi_grid, weights)
    coeffs2 = sh.expand(B2, theta_grid, phi_grid, weights)
    
    cross = sh.cross_spectrum(coeffs1, coeffs2)
    
    print("\n交叉谱 (l=0 到 8):")
    for l in range(l_max + 1):
        print(f"  l={l}: {np.real(cross[l]):.6f}")
    
    coherence = np.abs(cross) / np.sqrt(sh.power_spectrum(coeffs1) * sh.power_spectrum(coeffs2) + 1e-10)
    
    print("\n相干度 (l=0 到 8):")
    for l in range(l_max + 1):
        print(f"  l={l}: {coherence[l]:.4f}")
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    axes[0].semilogy(range(l_max + 1), np.abs(cross), 'go-', linewidth=2)
    axes[0].set_xlabel('Degree l')
    axes[0].set_ylabel('|Cross Spectrum|')
    axes[0].set_title('Cross Spectrum')
    axes[0].grid(True)
    
    axes[1].plot(range(l_max + 1), coherence, 'mo-', linewidth=2)
    axes[1].set_xlabel('Degree l')
    axes[1].set_ylabel('Coherence')
    axes[1].set_title('Coherence between Fields')
    axes[1].set_ylim([0, 1.1])
    axes[1].grid(True)
    
    plt.tight_layout()
    plt.savefig('cross_spectrum.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("\n交叉谱分析图已保存为 cross_spectrum.png")


if __name__ == "__main__":
    example_basic_usage()
    example_gauss_legendre_integration()
    example_expansion_reconstruction_gl()
    example_power_spectrum()
    example_magnetic_field_analysis()
    example_tikhonov_regularization()
    example_high_l_stability()
    example_cross_spectrum()
    
    print("\n" + "=" * 60)
    print("所有示例运行完成!")
    print("=" * 60)
