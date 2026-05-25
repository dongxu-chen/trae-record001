"""
MRI模拟器主程序
演示完整的MRI模拟流程：体模生成 -> 序列模拟 -> K空间采样 -> 图像重建 -> 可视化
"""

import sys
import time
import numpy as np

from mri_simulator.phantom import generate_shepp_logan, generate_brain_phantom
from mri_simulator.bloch import BlochSolver, BlochSolverGPU, GPU_AVAILABLE
from mri_simulator.sequences import SpinEcho, GradientEcho, InversionRecovery, EchoPlanar
from mri_simulator.kspace import KSpace
from mri_simulator.reconstruction import Reconstructor
from mri_simulator.visualization import MRIViewer


def check_gpu_available():
    """检查GPU是否可用"""
    if GPU_AVAILABLE:
        print("[OK] PyCUDA GPU加速可用")
        return True
    else:
        print("[WARN] PyCUDA不可用，将使用CPU版本")
        return False


def demo_spin_echo(use_gpu=False, matrix_size=(64, 64)):
    """
    演示自旋回波序列模拟
    
    Parameters:
        use_gpu: 是否使用GPU加速
        matrix_size: 矩阵大小
    """
    print("\n" + "=" * 60)
    print("自旋回波(Spin Echo)序列模拟")
    print("=" * 60)

    start_time = time.time()

    print("\n1. 生成数字体模...")
    phantom = generate_shepp_logan(size=matrix_size, fov=(0.256, 0.256))
    n_voxels = matrix_size[0] * matrix_size[1]
    print(f"   矩阵大小: {matrix_size}, 体素数: {n_voxels}")

    print("\n2. 初始化Bloch求解器...")
    if use_gpu:
        solver = BlochSolverGPU(n_voxels)
    else:
        solver = BlochSolver(n_voxels)
    print(f"   使用: {'GPU' if use_gpu else 'CPU'}")

    print("\n3. 配置脉冲序列...")
    se_sequence = SpinEcho(tr=1.0, te=0.05, matrix_size=matrix_size, fov=(0.256, 0.256))
    print(f"   TR = {se_sequence.tr}s, TE = {se_sequence.te}s")

    print("\n4. 运行模拟...")
    kspace_data = se_sequence.simulate(solver, phantom, use_gpu=use_gpu)
    sim_time = time.time() - start_time
    print(f"   模拟完成，耗时: {sim_time:.2f}秒")

    print("\n5. 图像重建...")
    reconstructor = Reconstructor(matrix_size=matrix_size, fov=(0.256, 0.256))
    recon_result = reconstructor.reconstruct_cartesian(kspace_data)

    print("\n6. 可视化...")
    viewer = MRIViewer()
    viewer.plot_phantom(phantom)
    viewer.plot_kspace(kspace_data)
    viewer.plot_reconstructed_image(recon_result)
    viewer.plot_profile(recon_result['magnitude'], axis=0, title='自旋回波图像剖面')

    print("\n7. 显示结果（如果支持图形界面）...")
    try:
        viewer.save_all(prefix='spin_echo_')
        print("   图像已保存为 spin_echo_*.png")
        import matplotlib.pyplot as plt
        if sys.platform != 'win32' or 'DISPLAY' in globals():
            viewer.show_all()
    except Exception as e:
        print(f"   显示跳过: {e}")

    viewer.close_all()
    total_time = time.time() - start_time
    print(f"\n总耗时: {total_time:.2f}秒")

    return recon_result


def demo_gradient_echo(use_gpu=False, matrix_size=(64, 64)):
    """
    演示梯度回波序列模拟
    """
    print("\n" + "=" * 60)
    print("梯度回波(Gradient Echo)序列模拟")
    print("=" * 60)

    start_time = time.time()

    phantom = generate_brain_phantom(size=matrix_size, fov=(0.256, 0.256))
    n_voxels = matrix_size[0] * matrix_size[1]

    if use_gpu:
        solver = BlochSolverGPU(n_voxels)
    else:
        solver = BlochSolver(n_voxels)

    gre_sequence = GradientEcho(
        tr=0.05, te=0.01, flip_angle=np.pi / 6,
        matrix_size=matrix_size, fov=(0.256, 0.256)
    )
    print(f"TR = {gre_sequence.tr}s, TE = {gre_sequence.te}s, 翻转角 = {np.rad2deg(gre_sequence.alpha):.1f}°")

    kspace_data = gre_sequence.simulate(solver, phantom, use_gpu=use_gpu)

    reconstructor = Reconstructor(matrix_size=matrix_size, fov=(0.256, 0.256))
    recon_result = reconstructor.reconstruct_cartesian(kspace_data)

    viewer = MRIViewer()
    viewer.plot_phantom(phantom)
    viewer.plot_kspace(kspace_data)
    viewer.plot_reconstructed_image(recon_result)

    try:
        viewer.save_all(prefix='gradient_echo_')
        print("图像已保存为 gradient_echo_*.png")
    except Exception as e:
        print(f"保存跳过: {e}")

    viewer.close_all()
    total_time = time.time() - start_time
    print(f"总耗时: {total_time:.2f}秒")

    return recon_result


def demo_inversion_recovery(use_gpu=False, matrix_size=(64, 64)):
    """
    演示反转恢复序列模拟
    """
    print("\n" + "=" * 60)
    print("反转恢复(Inversion Recovery)序列模拟")
    print("=" * 60)

    start_time = time.time()

    phantom = generate_shepp_logan(size=matrix_size, fov=(0.256, 0.256))
    n_voxels = matrix_size[0] * matrix_size[1]

    if use_gpu:
        solver = BlochSolverGPU(n_voxels)
    else:
        solver = BlochSolver(n_voxels)

    ir_sequence = InversionRecovery(
        tr=2.5, ti=0.5, te=0.05,
        matrix_size=matrix_size, fov=(0.256, 0.256)
    )
    print(f"TR = {ir_sequence.tr}s, TI = {ir_sequence.ti}s, TE = {ir_sequence.te}s")

    kspace_data = ir_sequence.simulate(solver, phantom, use_gpu=use_gpu)

    reconstructor = Reconstructor(matrix_size=matrix_size, fov=(0.256, 0.256))
    recon_result = reconstructor.reconstruct_cartesian(kspace_data)

    viewer = MRIViewer()
    viewer.plot_reconstructed_image(recon_result)

    try:
        viewer.save_all(prefix='inversion_recovery_')
        print("图像已保存为 inversion_recovery_*.png")
    except Exception as e:
        print(f"保存跳过: {e}")

    viewer.close_all()
    total_time = time.time() - start_time
    print(f"总耗时: {total_time:.2f}秒")

    return recon_result


def demo_sequence_comparison(use_gpu=False, matrix_size=(64, 64)):
    """
    比较不同序列的重建结果
    """
    print("\n" + "=" * 60)
    print("多序列结果比较")
    print("=" * 60)

    phantom = generate_shepp_logan(size=matrix_size, fov=(0.256, 0.256))
    n_voxels = matrix_size[0] * matrix_size[1]

    sequences = [
        SpinEcho(tr=1.0, te=0.05, matrix_size=matrix_size, fov=(0.256, 0.256)),
        GradientEcho(tr=0.05, te=0.01, flip_angle=np.pi / 6, matrix_size=matrix_size, fov=(0.256, 0.256)),
        InversionRecovery(tr=2.5, ti=0.5, te=0.05, matrix_size=matrix_size, fov=(0.256, 0.256)),
    ]

    sequence_names = ['自旋回波 (SE)', '梯度回波 (GRE)', '反转恢复 (IR)']

    reconstructor = Reconstructor(matrix_size=matrix_size, fov=(0.256, 0.256))
    recon_results = []

    for seq, name in zip(sequences, sequence_names):
        print(f"\n运行 {name}...")
        if use_gpu:
            solver = BlochSolverGPU(n_voxels)
        else:
            solver = BlochSolver(n_voxels)

        kspace = seq.simulate(solver, phantom, use_gpu=use_gpu)
        recon = reconstructor.reconstruct_cartesian(kspace)
        recon_results.append(recon)

    viewer = MRIViewer()
    viewer.plot_sequence_comparison(recon_results, sequence_names)

    try:
        viewer.save_all(prefix='comparison_')
        print("\n比较图像已保存为 comparison_*.png")
    except Exception as e:
        print(f"\n保存跳过: {e}")

    viewer.close_all()


def demo_advanced_recon(matrix_size=(64, 64)):
    """
    演示高级重建技术：欠采样 + 压缩传感
    """
    print("\n" + "=" * 60)
    print("高级重建技术演示")
    print("=" * 60)

    phantom = generate_shepp_logan(size=matrix_size, fov=(0.256, 0.256))
    n_voxels = matrix_size[0] * matrix_size[1]

    print("1. 生成完全采样K空间...")
    solver = BlochSolver(n_voxels)
    se_sequence = SpinEcho(tr=1.0, te=0.05, matrix_size=matrix_size, fov=(0.256, 0.256))
    kspace_full = se_sequence.simulate(solver, phantom, use_gpu=False)

    reconstructor = Reconstructor(matrix_size=matrix_size, fov=(0.256, 0.256))

    print("2. 完全采样重建...")
    recon_full = reconstructor.reconstruct_cartesian(kspace_full)

    print("3. 创建欠采样K空间 (R=4)...")
    kspace_obj = KSpace(matrix_size=matrix_size)
    kspace_obj.fill_cartesian(kspace_full)
    mask = kspace_obj.generate_random_mask(acceleration=4, center_fraction=0.1)
    kspace_obj.apply_mask(mask)
    kspace_undersampled = kspace_obj.get_data()

    print("4. 零填充重建...")
    recon_zero = reconstructor.reconstruct_cartesian(kspace_undersampled)

    print("5. 压缩传感重建 (ISTA)...")
    recon_cs_complex = reconstructor.compress_sensing_recon(
        kspace_undersampled, mask, lamda=0.005, num_iter=30
    )
    recon_cs = {
        'complex': recon_cs_complex,
        'magnitude': np.abs(recon_cs_complex),
        'phase': np.angle(recon_cs_complex)
    }

    print("6. 计算PSNR...")
    psnr_zero = reconstructor.calculate_psnr(recon_full['magnitude'], recon_zero['magnitude'])
    psnr_cs = reconstructor.calculate_psnr(recon_full['magnitude'], recon_cs['magnitude'])
    print(f"   零填充PSNR: {psnr_zero:.2f} dB")
    print(f"   压缩传感PSNR: {psnr_cs:.2f} dB")

    viewer = MRIViewer()
    viewer.plot_sampling_mask(mask, title=f'欠采样掩码 (R=4, 采样率={np.sum(mask)/np.prod(mask.shape)*100:.1f}%)')
    viewer.plot_compare_recon_methods(
        [recon_full, recon_zero, recon_cs],
        ['完全采样', f'零填充 (PSNR={psnr_zero:.1f}dB)', f'压缩传感 (PSNR={psnr_cs:.1f}dB)']
    )

    try:
        viewer.save_all(prefix='advanced_recon_')
        print("\n图像已保存为 advanced_recon_*.png")
    except Exception as e:
        print(f"\n保存跳过: {e}")

    viewer.close_all()


def demo_bloch_evolution():
    """
    演示Bloch方程磁化强度演化
    """
    print("\n" + "=" * 60)
    print("Bloch方程磁化强度演化演示")
    print("=" * 60)

    solver = BlochSolver(n_voxels=1)

    pd = np.array([1.0])
    t1 = np.array([1.0])
    t2 = np.array([0.1])
    solver.set_params(pd, t1, t2)

    n_steps = 200
    total_time = 2.0
    dt = total_time / n_steps

    time_points = np.arange(n_steps) * dt
    Mx = np.zeros(n_steps)
    My = np.zeros(n_steps)
    Mz = np.zeros(n_steps)

    x = np.array([0.0])
    y = np.array([0.0])

    for i in range(n_steps):
        t = time_points[i]

        if abs(t - 0.1) < dt / 2:
            solver.apply_excitation(np.pi / 2, 0.0)
        elif abs(t - 0.6) < dt / 2:
            solver.apply_excitation(np.pi, np.pi / 2)

        if i > 0:
            solver.evolve(dt, 0.0, 0.0, x, y)

        Mx[i] = solver.Mx[0]
        My[i] = solver.My[0]
        Mz[i] = solver.Mz[0]

    viewer = MRIViewer()
    viewer.plot_bloch_evolution(time_points, Mx, My, Mz,
                                title='自旋回波序列磁化强度演化')
    viewer.plot_3d_magnetization(Mx, My, Mz,
                                 title='磁化强度矢量在Bloch球上的轨迹')

    try:
        viewer.save_all(prefix='bloch_')
        print("图像已保存为 bloch_*.png")
    except Exception as e:
        print(f"保存跳过: {e}")

    viewer.close_all()


def demo_noise_analysis(matrix_size=(64, 64)):
    """
    演示噪声对图像质量的影响
    """
    print("\n" + "=" * 60)
    print("噪声分析演示")
    print("=" * 60)

    phantom = generate_shepp_logan(size=matrix_size, fov=(0.256, 0.256))
    n_voxels = matrix_size[0] * matrix_size[1]

    solver = BlochSolver(n_voxels)
    se_sequence = SpinEcho(tr=1.0, te=0.05, matrix_size=matrix_size, fov=(0.256, 0.256))
    kspace_data = se_sequence.simulate(solver, phantom, use_gpu=False)

    reconstructor = Reconstructor(matrix_size=matrix_size, fov=(0.256, 0.256))
    recon_clean = reconstructor.reconstruct_cartesian(kspace_data)

    snr_levels = [40, 30, 20, 10]
    noisy_recons = []
    kspace_obj = KSpace(matrix_size=matrix_size)

    for snr in snr_levels:
        kspace_obj.fill_cartesian(kspace_data.copy())
        kspace_obj.add_noise(snr=snr)
        recon_noisy = reconstructor.reconstruct_cartesian(kspace_obj.get_data())
        noisy_recons.append(recon_noisy['magnitude'])

    viewer = MRIViewer()
    viewer.plot_noise_analysis(recon_clean['magnitude'], noisy_recons, snr_levels)

    try:
        viewer.save_all(prefix='noise_')
        print("图像已保存为 noise_*.png")
    except Exception as e:
        print(f"保存跳过: {e}")

    viewer.close_all()


def demo_kspace_trajectories():
    """
    演示不同的K空间轨迹
    """
    print("\n" + "=" * 60)
    print("K空间轨迹演示")
    print("=" * 60)

    from mri_simulator.kspace import (
        generate_kspace_trajectory_cartesian,
        generate_kspace_trajectory_radial,
        generate_kspace_trajectory_spiral
    )

    matrix_size = (64, 64)
    fov = (0.256, 0.256)

    kx_cart, ky_cart = generate_kspace_trajectory_cartesian(matrix_size, fov)
    kx_rad, ky_rad = generate_kspace_trajectory_radial(num_spokes=32, num_points=64, fov=fov)
    kx_spi, ky_spi = generate_kspace_trajectory_spiral(num_arms=8, num_points=256, fov=fov)

    viewer = MRIViewer()
    viewer.plot_kspace_trajectory(kx_cart, ky_cart, title='笛卡尔采样轨迹')
    viewer.plot_kspace_trajectory(kx_rad, ky_rad, title='放射状采样轨迹')
    viewer.plot_kspace_trajectory(kx_spi, ky_spi, title='螺旋采样轨迹')

    try:
        viewer.save_all(prefix='trajectory_')
        print("图像已保存为 trajectory_*.png")
    except Exception as e:
        print(f"保存跳过: {e}")

    viewer.close_all()


def main():
    """主程序入口"""
    print("=" * 60)
    print("磁共振成像(MRI)模拟器")
    print("基于Bloch方程的完整MRI模拟系统")
    print("=" * 60)

    use_gpu = check_gpu_available()

    import argparse
    parser = argparse.ArgumentParser(description='MRI模拟器')
    parser.add_argument('--demo', type=str, default='all',
                       choices=['all', 'se', 'gre', 'ir', 'comp', 'advanced',
                               'bloch', 'noise', 'trajectory'],
                       help='运行指定的演示 (默认: all)')
    parser.add_argument('--matrix-size', type=int, nargs=2, default=[64, 64],
                       metavar=('NY', 'NX'), help='矩阵大小 (默认: 64 64)')
    parser.add_argument('--no-gpu', action='store_true',
                       help='强制使用CPU')
    parser.add_argument('--no-display', action='store_true',
                       help='不显示图形界面')

    args = parser.parse_args()

    if args.no_gpu:
        use_gpu = False

    matrix_size = tuple(args.matrix_size)

    demos = {
        'se': ('自旋回波序列', lambda: demo_spin_echo(use_gpu, matrix_size)),
        'gre': ('梯度回波序列', lambda: demo_gradient_echo(use_gpu, matrix_size)),
        'ir': ('反转恢复序列', lambda: demo_inversion_recovery(use_gpu, matrix_size)),
        'comp': ('多序列比较', lambda: demo_sequence_comparison(use_gpu, matrix_size)),
        'advanced': ('高级重建技术', lambda: demo_advanced_recon(matrix_size)),
        'bloch': ('Bloch方程演化', demo_bloch_evolution),
        'noise': ('噪声分析', lambda: demo_noise_analysis(matrix_size)),
        'trajectory': ('K空间轨迹', demo_kspace_trajectories),
    }

    try:
        if args.demo == 'all':
            print("\n运行所有演示...")
            for name, func in demos.values():
                try:
                    func()
                except Exception as e:
                    print(f"\n[ERROR] {name} 演示失败: {e}")
                    import traceback
                    traceback.print_exc()
        else:
            name, func = demos[args.demo]
            func()

        print("\n" + "=" * 60)
        print("所有演示完成！")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
