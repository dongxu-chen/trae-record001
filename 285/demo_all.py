import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from edge_detection import EdgeDetection
from deep_edge import DeepEdgeDetector, EdgeGuidedFilter, RealtimeEdgeDetection
from metrics import Metrics


def demo_edge_guided_filtering():
    print("\n" + "=" * 60)
    print("边缘导向滤波应用演示")
    print("=" * 60)

    detector = EdgeDetection()
    egf = EdgeGuidedFilter()

    test_img = np.ones((400, 400, 3), dtype=np.uint8) * 220
    cv2.rectangle(test_img, (80, 80), (180, 180), (50, 120, 200), -1)
    cv2.circle(test_img, (280, 280), 70, (200, 80, 50), -1)
    cv2.putText(test_img, "TEST", (150, 320), cv2.FONT_HERSHEY_SIMPLEX, 1, (50, 50, 50), 2)

    noise = np.random.normal(0, 15, test_img.shape).astype(np.int16)
    test_img = np.clip(test_img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    edges = detector.detect_edges(test_img, method='canny', preprocess='gaussian')

    smoothed = egf.edge_guided_smoothing(test_img, edges, smooth_strength=15, edge_weight=0.8)
    enhanced = egf.edge_enhancement(test_img, edges, strength=2.0)
    bokeh = egf.edge_aware_blur(test_img, edges, blur_kernel=31)

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))

    axes[0, 0].imshow(cv2.cvtColor(test_img, cv2.COLOR_BGR2RGB))
    axes[0, 0].set_title('原图 (带噪声)')
    axes[0, 0].axis('off')

    axes[0, 1].imshow(edges, cmap='gray')
    axes[0, 1].set_title('检测边缘')
    axes[0, 1].axis('off')

    axes[0, 2].imshow(cv2.cvtColor(smoothed, cv2.COLOR_BGR2RGB))
    axes[0, 2].set_title('边缘导向平滑')
    axes[0, 2].axis('off')

    axes[1, 0].imshow(cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB))
    axes[1, 0].set_title('边缘增强')
    axes[1, 0].axis('off')

    axes[1, 1].imshow(cv2.cvtColor(bokeh, cv2.COLOR_BGR2RGB))
    axes[1, 1].set_title('边缘感知虚化 (散景效果)')
    axes[1, 1].axis('off')

    simple_blur = cv2.GaussianBlur(test_img, (31, 31), 0)
    axes[1, 2].imshow(cv2.cvtColor(simple_blur, cv2.COLOR_BGR2RGB))
    axes[1, 2].set_title('普通高斯模糊 (对比)')
    axes[1, 2].axis('off')

    plt.tight_layout()

    output_dir = 'filter_demo'
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(os.path.join(output_dir, 'edge_guided_filtering.png'), dpi=150, bbox_inches='tight')
    print(f"结果已保存到: {output_dir}/")

    cv2.imwrite(os.path.join(output_dir, 'original.png'), test_img)
    cv2.imwrite(os.path.join(output_dir, 'edges.png'), edges)
    cv2.imwrite(os.path.join(output_dir, 'smoothed.png'), smoothed)
    cv2.imwrite(os.path.join(output_dir, 'enhanced.png'), enhanced)
    cv2.imwrite(os.path.join(output_dir, 'bokeh.png'), bokeh)

    plt.show()


def demo_traditional_vs_deep():
    print("\n" + "=" * 60)
    print("传统算法 vs 深度学习算法对比")
    print("=" * 60)

    detector = EdgeDetection()
    deep_detector = DeepEdgeDetector()
    metrics_calc = Metrics()

    test_img = np.ones((400, 500, 3), dtype=np.uint8) * 230
    cv2.rectangle(test_img, (50, 50), (180, 180), (60, 60, 60), 3)
    cv2.rectangle(test_img, (220, 80), (380, 220), (50, 50, 50), 2)
    cv2.circle(test_img, (120, 320), 60, (70, 70, 70), 3)
    cv2.line(test_img, (250, 280), (450, 380), (55, 55, 55), 2)
    cv2.ellipse(test_img, (350, 120), (50, 30), 30, 0, 360, (65, 65, 65), 2)

    clean_gray = cv2.cvtColor(test_img, cv2.COLOR_BGR2GRAY)
    gt_edges = cv2.Canny(clean_gray, 50, 150)
    gt_boundaries = gt_edges[np.newaxis, ...]

    noise = np.random.normal(0, 12, test_img.shape).astype(np.int16)
    noisy_img = np.clip(test_img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    methods = ['sobel', 'laplacian', 'canny', 'hed', 'rcf']
    results = {}

    for method in methods:
        print(f"  处理 {method.upper()}...", end='')

        if method in ['hed', 'rcf']:
            edges, elapsed = metrics_calc.measure_time(
                deep_detector.detect, noisy_img, method=method
            )
            if edges is None:
                edges = np.zeros_like(noisy_img[:, :, 0])
                print(" (模型未加载, 跳过)")
                continue
        else:
            edges, elapsed = metrics_calc.measure_time(
                detector.detect_edges, noisy_img, method=method, preprocess='gaussian'
            )

        bsds_metric = metrics_calc.compute_all_bsds_metrics(edges, gt_boundaries, tolerance=2)
        results[method] = {
            'edges': edges,
            'time': elapsed,
            'ods_f1': bsds_metric['ods_f1'],
            'ois_f1': bsds_metric['ois_f1']
        }
        print(f" {elapsed*1000:.1f}ms, ODS F1={bsds_metric['ods_f1']:.3f}")

    fig = plt.figure(figsize=(18, 10))
    gs = fig.add_gridspec(2, 4)

    ax = fig.add_subplot(gs[0, 0])
    ax.imshow(cv2.cvtColor(noisy_img, cv2.COLOR_BGR2RGB))
    ax.set_title('输入图像 (带噪声)')
    ax.axis('off')

    ax = fig.add_subplot(gs[0, 1])
    ax.imshow(gt_edges, cmap='gray')
    ax.set_title('Ground Truth')
    ax.axis('off')

    plot_idx = 2
    for method in methods:
        if method not in results:
            continue
        row = plot_idx // 4
        col = plot_idx % 4
        ax = fig.add_subplot(gs[row, col])
        ax.imshow(results[method]['edges'], cmap='gray')
        ax.set_title(f"{method.upper()}\n{results[method]['time']*1000:.1f}ms, F1={results[method]['ods_f1']:.3f}")
        ax.axis('off')
        plot_idx += 1

    plt.tight_layout()

    output_dir = 'method_comparison'
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(os.path.join(output_dir, 'traditional_vs_deep.png'), dpi=150, bbox_inches='tight')
    print(f"\n对比图已保存到: {output_dir}/")

    plt.show()


def run_realtime_demo():
    print("\n" + "=" * 60)
    print("实时边缘检测演示")
    print("=" * 60)
    print("1. Canny (传统算法, 快速)")
    print("2. Sobel (传统算法, 快速)")
    print("3. Laplacian (传统算法, 快速)")
    print("4. HED (深度学习, 高质量)")
    print("5. RCF (深度学习, 高质量)")
    print("\n按 1-5 切换方法, q 退出, s 保存截图")
    print("=" * 60)

    choice = input("\n选择初始方法 (1-5, 默认1): ").strip()
    method_map = {'1': 'canny', '2': 'sobel', '3': 'laplacian', '4': 'hed', '5': 'rcf'}
    initial_method = method_map.get(choice, 'canny')

    rt = RealtimeEdgeDetection(camera_id=0)
    rt.start(method=initial_method)


def main():
    print("=" * 70)
    print("边缘检测算法库 - 完整演示")
    print("=" * 70)
    print("\n请选择演示模式:")
    print("  1. 边缘导向滤波应用演示")
    print("  2. 传统算法 vs 深度学习算法对比")
    print("  3. 实时摄像头边缘检测")
    print("  4. 运行所有演示")

    choice = input("\n输入选择 (1-4): ").strip()

    if choice == '1':
        demo_edge_guided_filtering()
    elif choice == '2':
        demo_traditional_vs_deep()
    elif choice == '3':
        run_realtime_demo()
    elif choice == '4':
        demo_edge_guided_filtering()
        demo_traditional_vs_deep()
        run_realtime_demo()
    else:
        print("无效选择")


if __name__ == "__main__":
    main()
