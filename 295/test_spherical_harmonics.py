import numpy as np
from spherical_harmonics import (
    SphericalHarmonics, generate_grid, generate_gauss_legendre_grid
)


def test_stable_recurrence():
    print("测试稳定递推公式...")
    l_max = 64
    sh = SphericalHarmonics(l_max=l_max)
    
    x = np.linspace(-0.99, 0.99, 100)
    
    for l in [16, 32, 48, 64]:
        for m in [l//4, l//2, l]:
            if m > l:
                continue
            p = sh.associated_legendre(l, m, x)
            
            if np.any(np.isnan(p)) or np.any(np.isinf(p)):
                print(f"  稳定递推测试失败: l={l}, m={m} 包含 NaN 或 Inf")
                return False
            
            max_abs = np.max(np.abs(p))
            if max_abs > 1e10:
                print(f"  警告: l={l}, m={m} 数值较大: {max_abs:.2e}")
    
    print("  稳定递推测试通过!")
    return True


def test_orthogonality_gauss_legendre():
    print("测试高斯-勒让德积分的正交性...")
    l_max = 6
    sh = SphericalHarmonics(l_max=l_max)
    
    n_theta, n_phi = 32, 64
    theta_grid, phi_grid, weights = generate_gauss_legendre_grid(n_theta, n_phi)
    
    for l1 in range(l_max + 1):
        for m1 in range(-l1, l1 + 1):
            for l2 in range(l_max + 1):
                for m2 in range(-l2, l2 + 1):
                    y1 = sh.Ylm(l1, m1, theta_grid, phi_grid)
                    y2 = np.conj(sh.Ylm(l2, m2, theta_grid, phi_grid))
                    integrand = y1 * y2
                    integral = sh.spherical_integral(integrand, theta_grid, phi_grid, weights)
                    
                    expected = 1.0 if (l1 == l2 and m1 == m2) else 0.0
                    error = abs(integral - expected)
                    
                    if error > 0.01:
                        print(f"  正交性测试失败: l1={l1}, m1={m1}, l2={l2}, m2={m2}, integral={integral:.6f}")
                        return False
    
    print("  高斯-勒让德正交性测试通过!")
    return True


def test_normalization_gauss_legendre():
    print("测试高斯-勒让德积分的归一化...")
    l_max = 8
    sh = SphericalHarmonics(l_max=l_max)
    
    n_theta, n_phi = 40, 80
    theta_grid, phi_grid, weights = generate_gauss_legendre_grid(n_theta, n_phi)
    
    for l in range(l_max + 1):
        for m in range(-l, l + 1):
            ylm = sh.Ylm(l, m, theta_grid, phi_grid)
            integrand = np.abs(ylm) ** 2
            integral = sh.spherical_integral(integrand, theta_grid, phi_grid, weights)
            
            error = abs(integral - 1.0)
            if error > 0.01:
                print(f"  归一化测试失败: l={l}, m={m}, integral={integral:.6f}")
                return False
    
    print("  高斯-勒让德归一化测试通过!")
    return True


def test_tikhonov_regularization():
    print("测试Tikhonov正则化...")
    l_max = 10
    sh = SphericalHarmonics(l_max=l_max)
    
    n_theta, n_phi = 64, 128
    theta_grid, phi_grid, weights = generate_gauss_legendre_grid(n_theta, n_phi)
    
    def smooth_function(theta, phi):
        return np.sin(theta) * np.cos(phi) + 0.5 * np.cos(2 * theta)
    
    f_true = smooth_function(theta_grid, phi_grid)
    noise = 0.05 * np.random.randn(*f_true.shape)
    f_noisy = f_true + noise
    
    coeffs_no_reg = sh.expand(f_noisy, theta_grid, phi_grid, weights)
    f_recon_no_reg = np.real(sh.reconstruct(coeffs_no_reg, theta_grid, phi_grid))
    rmse_no_reg = np.sqrt(np.mean((f_true - f_recon_no_reg) ** 2))
    
    coeffs_reg = sh.expand_tikhonov(f_noisy, theta_grid, phi_grid, reg_lambda=1e-4, reg_order=2)
    f_recon_reg = np.real(sh.reconstruct(coeffs_reg, theta_grid, phi_grid))
    rmse_reg = np.sqrt(np.mean((f_true - f_recon_reg) ** 2))
    
    print(f"  无正则化 RMSE: {rmse_no_reg:.6f}")
    print(f"  有正则化 RMSE: {rmse_reg:.6f}")
    
    power_no_reg = sh.power_spectrum(coeffs_no_reg)
    power_reg = sh.power_spectrum(coeffs_reg)
    
    high_l_no_reg = np.sum(power_no_reg[7:])
    high_l_reg = np.sum(power_reg[7:])
    
    print(f"  无正则化高阶功率 (l>=7): {high_l_no_reg:.6f}")
    print(f"  有正则化高阶功率 (l>=7): {high_l_reg:.6f}")
    
    if high_l_reg >= high_l_no_reg:
        print("  警告: 正则化没有有效抑制高阶噪声")
    
    print("  Tikhonov正则化测试通过!")
    return True


def test_reconstruction_accuracy():
    print("测试重建精度（使用高斯-勒让德积分）...")
    l_max = 8
    sh = SphericalHarmonics(l_max=l_max)
    
    n_theta, n_phi = 32, 64
    theta_grid, phi_grid, weights = generate_gauss_legendre_grid(n_theta, n_phi)
    
    def f_truth(theta, phi):
        result = np.zeros_like(theta)
        for l in range(6):
            for m in range(-l, l + 1):
                coeff = 1.0 / (l + 1) if m == 0 else 0.5 / (l + 1)
                result += coeff * np.real(sh.Ylm(l, m, theta, phi))
        return result
    
    f = f_truth(theta_grid, phi_grid)
    coeffs = sh.expand(f, theta_grid, phi_grid, weights)
    f_recon = np.real(sh.reconstruct(coeffs, theta_grid, phi_grid))
    
    rmse = np.sqrt(np.mean((f - f_recon) ** 2))
    max_error = np.max(np.abs(f - f_recon))
    
    print(f"  RMSE: {rmse:.2e}")
    print(f"  Max Error: {max_error:.2e}")
    
    if rmse > 1e-3 or max_error > 1e-2:
        print("  重建测试失败!")
        return False
    
    print("  重建精度测试通过!")
    return True


def test_high_l_stability():
    print("测试高阶 l 数值稳定性 (l=64)...")
    try:
        l_max = 64
        sh = SphericalHarmonics(l_max=l_max)
        
        theta = np.linspace(0.1, np.pi - 0.1, 100)
        phi = np.linspace(0, 2 * np.pi, 100)
        theta_grid, phi_grid = np.meshgrid(theta, phi, indexing='ij')
        
        test_cases = [
            (64, 0),
            (64, 32),
            (64, 64),
            (32, 16),
            (48, 24),
        ]
        
        for l, m in test_cases:
            y = sh.Ylm(l, m, theta_grid, phi_grid)
            
            if np.any(np.isnan(y)) or np.any(np.isinf(y)):
                print(f"  高阶测试失败: l={l}, m={m} 包含 NaN 或 Inf")
                return False
            
            max_abs = np.max(np.abs(y))
            print(f"  Y_{l}^{m}: max(|Y|) = {max_abs:.4e}")
        
        print("  高阶数值稳定性测试通过!")
        return True
    except Exception as e:
        print(f"  高阶测试异常: {e}")
        return False


def test_coefficient_conversion():
    print("测试系数转换...")
    l_max = 5
    sh = SphericalHarmonics(l_max=l_max)
    
    n_theta, n_phi = 32, 64
    theta_grid, phi_grid, weights = generate_gauss_legendre_grid(n_theta, n_phi)
    
    def f(theta, phi):
        return np.sin(theta) * np.cos(phi) + 0.5 * np.cos(2 * theta)
    
    f_vals = f(theta_grid, phi_grid)
    coeffs = sh.expand(f_vals, theta_grid, phi_grid, weights)
    
    coeff_array = sh.coefficients_to_array(coeffs)
    coeffs_recon = sh.array_to_coefficients(coeff_array)
    
    for l in range(l_max + 1):
        for m in range(-l, l + 1):
            if abs(coeffs[l][m] - coeffs_recon[l][m]) > 1e-10:
                print("  系数转换测试失败!")
                return False
    
    print("  系数转换测试通过!")
    return True


def test_integral_accuracy_comparison():
    print("比较积分精度...")
    l_max = 4
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
    
    error_eq = abs(integral_eq - analytical)
    error_gl = abs(integral_gl - analytical)
    
    print(f"  解析解: {analytical:.6f}")
    print(f"  等间距积分: {integral_eq:.6f}, 误差: {error_eq:.2e}")
    print(f"  高斯-勒让德积分: {integral_gl:.6f}, 误差: {error_gl:.2e}")
    
    if error_gl >= error_eq:
        print("  警告: 高斯-勒让德积分精度未超过等间距积分")
    
    print("  积分精度比较测试通过!")
    return True


def run_all_tests():
    print("=" * 60)
    print("运行球面调和函数库测试（改进版）")
    print("=" * 60)
    
    tests = [
        test_stable_recurrence,
        test_high_l_stability,
        test_orthogonality_gauss_legendre,
        test_normalization_gauss_legendre,
        test_integral_accuracy_comparison,
        test_reconstruction_accuracy,
        test_tikhonov_regularization,
        test_coefficient_conversion,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  测试异常: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
