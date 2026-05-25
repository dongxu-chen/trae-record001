import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from edge_detection import EdgeDetection
from metrics import Metrics


def generate_test_image(size=512):
    image = np.ones((size, size, 3), dtype=np.uint8) * 240
    
    cv2.rectangle(image, (100, 100), (250, 250), (50, 50, 50), 3)
    cv2.rectangle(image, (300, 150), (450, 350), (80, 80, 80), 2)
    cv2.circle(image, (180, 380), 80, (60, 60, 60), 3)
    cv2.line(image, (320, 400), (480, 480), (70, 70, 70), 2)
    
    for i in range(10):
        cv2.line(image, (50 + i*45, 50), (50 + i*45, 80), (100, 100, 100), 1)
    
    return image


def add_noise(image, noise_type='gaussian', sigma=25):
    if noise_type == 'gaussian':
        noise = np.random.normal(0, sigma, image.shape)
        noisy = image.astype(np.float64) + noise
        return np.clip(noisy, 0, 255).astype(np.uint8)
    elif noise_type == 'salt_pepper':
        noisy = image.copy()
        amount = 0.02
        salt = np.random.random(image.shape[:2]) < amount/2
        pepper = np.random.random(image.shape[:2]) < amount/2
        noisy[salt] = 255
        noisy[pepper] = 0
        return noisy
    return image


def compare_canny_optimization():
    print("\n[5] 优化Canny vs 原版Canny 性能对比...")
    detector = EdgeDetection()
    metrics_calc = Metrics()
    
    test_img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    edges_opt, time_opt = metrics_calc.measure_time(
        detector.canny_optimized, test_img, 50, 150
    )
    
    edges_orig, time_orig = metrics_calc.measure_time(
        detector.canny, test_img, 50, 150, use_optimized=False
    )
    
    print(f"  优化版Canny: {time_opt*1000:.2f} ms")
    print(f"  原版Canny:   {time_orig*1000:.2f} ms")
    print(f"  加速比: {time_orig/time_opt:.2f}x")
    
    return time_opt, time_orig


def demo():
    print("=" * 70)
    print("边缘检测算法库 - 优化版演示")
    print("=" * 70)
    print("  - Canny: 分离卷积 + 并行NMS + 完整双阈值边缘连接")
    print("  - 评估: BSDS500 标准化指标 (ODS, OIS)")
    print("=" * 70)
    
    detector = EdgeDetection()
    metrics_calc = Metrics()
    
    print("\n[1] 生成测试图片...")
    clean_img = generate_test_image()
    noisy_img = add_noise(clean_img, 'gaussian', 20)
    
    clean_gray = cv2.cvtColor(clean_img, cv2.COLOR_BGR2GRAY)
    gt_edges = cv2.Canny(clean_gray, 50, 150)
    gt_boundaries = gt_edges[np.newaxis, ...]
    
    print("[2] 执行边缘检测 (优化算法)...")
    methods = ['sobel', 'laplacian', 'canny']
    preprocesses = [None, 'gaussian', 'median']
    
    results = {}
    for prep in preprocesses:
        for method in methods:
            key = f"{prep if prep else 'none'}_{method}"
            edges, elapsed = metrics_calc.measure_time(
                detector.detect_edges,
                noisy_img, method=method, preprocess=prep,
                connect_edges=False, use_optimized_canny=True
            )
            bsds_metric = metrics_calc.compute_all_bsds_metrics(
                edges, gt_boundaries, tolerance=2
            )
            results[key] = {
                'edges': edges,
                'time': elapsed,
                'ods_f1': bsds_metric['ods_f1'],
                'ois_f1': bsds_metric['ois_f1'],
                'ods_precision': bsds_metric['ods_precision'],
                'ods_recall': bsds_metric['ods_recall']
            }
    
    print("\n[3] BSDS500 标准化性能基准:")
    print("-" * 90)
    print(f"{'方法':<22} {'时间(ms)':<10} {'ODS F1':<10} {'OIS F1':<10} {'ODS P':<10} {'ODS R':<10}")
    print("-" * 90)
    for key in sorted(results.keys()):
        r = results[key]
        print(f"{key:<22} {r['time']*1000:<10.2f} {r['ods_f1']:<10.4f} "
              f"{r['ois_f1']:<10.4f} {r['ods_precision']:<10.4f} {r['ods_recall']:<10.4f}")
    
    compare_canny_optimization()
    
    print("\n[4] 生成可视化结果...")
    fig = plt.figure(figsize=(20, 13))
    
    plt.subplot(3, 6, 1)
    plt.imshow(cv2.cvtColor(clean_img, cv2.COLOR_BGR2RGB))
    plt.title('原图', fontsize=9)
    plt.axis('off')
    
    plt.subplot(3, 6, 2)
    plt.imshow(cv2.cvtColor(noisy_img, cv2.COLOR_BGR2RGB))
    plt.title('加噪图', fontsize=9)
    plt.axis('off')
    
    plt.subplot(3, 6, 3)
    plt.imshow(gt_edges, cmap='gray')
    plt.title('Ground Truth', fontsize=9)
    plt.axis('off')
    
    plot_idx = 4
    for key in sorted(results.keys()):
        if plot_idx > 18:
            break
        plt.subplot(3, 6, plot_idx)
        plt.imshow(results[key]['edges'], cmap='gray')
        plt.title(f"{key}\nODS={results[key]['ods_f1']:.3f}", fontsize=7)
        plt.axis('off')
        plot_idx += 1
    
    plt.tight_layout()
    
    output_dir = 'demo_output'
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(os.path.join(output_dir, 'comparison_optimized.png'), dpi=150, bbox_inches='tight')
    print(f"对比图已保存: {os.path.join(output_dir, 'comparison_optimized.png')}")
    
    cv2.imwrite(os.path.join(output_dir, 'clean_image.png'), clean_img)
    cv2.imwrite(os.path.join(output_dir, 'noisy_image.png'), noisy_img)
    cv2.imwrite(os.path.join(output_dir, 'ground_truth.png'), gt_edges)
    
    for key, data in results.items():
        cv2.imwrite(os.path.join(output_dir, f'{key}.png'), data['edges'])
    
    print(f"\n所有结果已保存到: {output_dir}/")
    print("\n[完成] 演示结束!")
    print("\n提示: 运行 'python main.py' 进行完整的BSDS500基准测试")
    plt.show()


if __name__ == "__main__":
    demo()
