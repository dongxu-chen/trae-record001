import os
import glob
import cv2
import numpy as np
import matplotlib.pyplot as plt
from edge_detection import EdgeDetection
from metrics import Metrics
from bsds_dataset import BSDS500


class EdgeDetectionBenchmark:
    def __init__(self):
        self.detector = EdgeDetection()
        self.metrics = Metrics()

    def process_single_image(self, image_path, output_dir, methods=None, preprocess=None,
                             save_results=True, show_plots=False):
        if methods is None:
            methods = ['sobel', 'laplacian', 'canny']
        if preprocess is None:
            preprocess = [None, 'gaussian', 'median']

        image = cv2.imread(image_path)
        if image is None:
            print(f"无法读取图片: {image_path}")
            return None

        image_name = os.path.splitext(os.path.basename(image_path))[0]
        results = {}

        for prep in preprocess:
            for method in methods:
                key = f"{prep if prep else 'none'}_{method}"
                
                edges, elapsed = self.metrics.measure_time(
                    self.detector.detect_edges,
                    image, method=method, preprocess=prep,
                    connect_edges=True, min_edge_length=5
                )
                
                density = self.metrics.edge_density(edges)
                results[key] = {
                    'edges': edges,
                    'time': elapsed,
                    'density': density
                }

                if save_results:
                    prep_dir = os.path.join(output_dir, prep if prep else 'none')
                    os.makedirs(prep_dir, exist_ok=True)
                    cv2.imwrite(os.path.join(prep_dir, f"{image_name}_{method}.png"), edges)

        if show_plots:
            self._plot_results(image, results, image_name)

        return results

    def batch_process(self, input_dir, output_dir, image_extensions=['.png', '.jpg', '.jpeg', '.bmp'], **kwargs):
        os.makedirs(output_dir, exist_ok=True)
        image_files = []
        for ext in image_extensions:
            image_files.extend(glob.glob(os.path.join(input_dir, f"*{ext}")))
            image_files.extend(glob.glob(os.path.join(input_dir, f"*{ext.upper()}")))

        if not image_files:
            print(f"在 {input_dir} 中未找到图片文件")
            return

        all_results = {}
        for image_path in image_files:
            print(f"处理: {os.path.basename(image_path)}")
            results = self.process_single_image(image_path, output_dir, **kwargs)
            if results:
                all_results[os.path.basename(image_path)] = results

        self._print_benchmark(all_results)
        self._plot_benchmark(all_results, output_dir)

    def benchmark_with_ground_truth(self, input_dir, gt_dir, output_dir, **kwargs):
        os.makedirs(output_dir, exist_ok=True)
        image_files = glob.glob(os.path.join(input_dir, "*.png")) + \
                      glob.glob(os.path.join(input_dir, "*.jpg"))

        all_metrics = {}

        for image_path in image_files:
            image_name = os.path.splitext(os.path.basename(image_path))[0]
            gt_path = os.path.join(gt_dir, f"{image_name}.png")
            
            if not os.path.exists(gt_path):
                continue

            image = cv2.imread(image_path)
            gt_edges = cv2.imread(gt_path, cv2.IMREAD_GRAYSCALE)

            results = self.process_single_image(image_path, output_dir, save_results=True, **kwargs)
            
            if results:
                for key, data in results.items():
                    metric = self.metrics.precision_recall(data['edges'], gt_edges, tolerance=2)
                    metric['time'] = data['time']
                    if key not in all_metrics:
                        all_metrics[key] = []
                    all_metrics[key].append(metric)

        self._print_gt_benchmark(all_metrics)
        return all_metrics

    def benchmark_bsds500(self, bsds_root='BSDS500', split='val', output_dir='bsds_results',
                          methods=None, preprocess=None, max_images=None):
        if methods is None:
            methods = ['sobel', 'laplacian', 'canny']
        if preprocess is None:
            preprocess = [None, 'gaussian', 'median']

        os.makedirs(output_dir, exist_ok=True)
        bsds = BSDS500(bsds_root)
        
        if not bsds.check_dataset():
            print("\n正在创建合成BSDS500风格数据集用于演示...")
            bsds.create_synthetic_bsds(bsds_root, num_images=20)

        image_ids = bsds.get_image_ids(split)
        if not image_ids:
            print(f"在 {split} 分割中未找到图片")
            return None

        if max_images is not None:
            image_ids = image_ids[:max_images]

        print(f"\n开始BSDS500基准测试 ({split} set, {len(image_ids)} images)")
        print("=" * 80)

        all_results = {}
        all_bsds_metrics = {}

        for img_id in image_ids:
            print(f"  处理图片: {img_id}")
            
            image = bsds.load_image(img_id, split)
            gt_boundaries = bsds.load_ground_truth(img_id, split)
            
            if image is None or gt_boundaries is None:
                continue

            img_results = {}
            for prep in preprocess:
                for method in methods:
                    key = f"{prep if prep else 'none'}_{method}"
                    
                    edges, elapsed = self.metrics.measure_time(
                        self.detector.detect_edges,
                        image, method=method, preprocess=prep,
                        connect_edges=False
                    )
                    
                    bsds_metric = self.metrics.compute_all_bsds_metrics(
                        edges, gt_boundaries, tolerance=2
                    )
                    bsds_metric['time'] = elapsed
                    bsds_metric['density'] = self.metrics.edge_density(edges)
                    
                    img_results[key] = bsds_metric
                    
                    if key not in all_bsds_metrics:
                        all_bsds_metrics[key] = []
                    all_bsds_metrics[key].append(bsds_metric)

                    result_dir = os.path.join(output_dir, split, key)
                    os.makedirs(result_dir, exist_ok=True)
                    cv2.imwrite(os.path.join(result_dir, f"{img_id}.png"), edges)

            all_results[img_id] = img_results

        self._print_bsds_benchmark(all_bsds_metrics)
        self._plot_bsds_benchmark(all_bsds_metrics, output_dir)
        
        return all_bsds_metrics

    def _plot_results(self, original, results, image_name):
        n = len(results) + 1
        cols = 4
        rows = (n + cols - 1) // cols

        plt.figure(figsize=(15, 4 * rows))
        plt.subplot(rows, cols, 1)
        plt.imshow(cv2.cvtColor(original, cv2.COLOR_BGR2RGB))
        plt.title('Original')
        plt.axis('off')

        for i, (key, data) in enumerate(results.items(), 2):
            plt.subplot(rows, cols, i)
            plt.imshow(data['edges'], cmap='gray')
            plt.title(f"{key}\n{data['time']*1000:.2f}ms")
            plt.axis('off')

        plt.tight_layout()
        plt.suptitle(f"Edge Detection: {image_name}", fontsize=16)
        plt.show()

    def _print_benchmark(self, all_results):
        print("\n" + "=" * 60)
        print("性能基准对比")
        print("=" * 60)
        print(f"{'方法':<25} {'平均时间(ms)':<15} {'边缘密度':<15}")
        print("-" * 60)

        aggregated = {}
        for img_results in all_results.values():
            for key, data in img_results.items():
                if key not in aggregated:
                    aggregated[key] = {'times': [], 'densities': []}
                aggregated[key]['times'].append(data['time'])
                aggregated[key]['densities'].append(data['density'])

        for key in sorted(aggregated.keys()):
            avg_time = np.mean(aggregated[key]['times']) * 1000
            avg_density = np.mean(aggregated[key]['densities'])
            print(f"{key:<25} {avg_time:<15.2f} {avg_density:<15.4f}")

    def _print_gt_benchmark(self, all_metrics):
        print("\n" + "=" * 80)
        print("带标注的性能基准对比 (精确率/召回率/F1)")
        print("=" * 80)
        print(f"{'方法':<25} {'精确率':<12} {'召回率':<12} {'F1':<12} {'时间(ms)':<12}")
        print("-" * 80)

        for key in sorted(all_metrics.keys()):
            metrics_list = all_metrics[key]
            precision = np.mean([m['precision'] for m in metrics_list])
            recall = np.mean([m['recall'] for m in metrics_list])
            f1 = np.mean([m['f1'] for m in metrics_list])
            time_ms = np.mean([m['time'] for m in metrics_list]) * 1000
            
            print(f"{key:<25} {precision:<12.4f} {recall:<12.4f} {f1:<12.4f} {time_ms:<12.2f}")

    def _print_bsds_benchmark(self, all_bsds_metrics):
        print("\n" + "=" * 100)
        print("BSDS500 标准化性能基准对比")
        print("=" * 100)
        print(f"{'方法':<25} {'ODS F1':<12} {'ODS P':<10} {'ODS R':<10} {'OIS F1':<12} {'时间(ms)':<12}")
        print("-" * 100)

        for key in sorted(all_bsds_metrics.keys()):
            metrics_list = all_bsds_metrics[key]
            aggregated = self.metrics.aggregate_bsds_metrics(metrics_list)
            avg_time = np.mean([m['time'] for m in metrics_list]) * 1000
            
            print(f"{key:<25} "
                  f"{aggregated['ods_f1']:<12.4f} "
                  f"{aggregated['ods_precision']:<10.4f} "
                  f"{aggregated['ods_recall']:<10.4f} "
                  f"{aggregated['ois_f1']:<12.4f} "
                  f"{avg_time:<12.2f}")
        print("=" * 100)

    def _plot_benchmark(self, all_results, output_dir):
        methods = []
        times = []
        densities = []

        aggregated = {}
        for img_results in all_results.values():
            for key, data in img_results.items():
                if key not in aggregated:
                    aggregated[key] = {'times': [], 'densities': []}
                aggregated[key]['times'].append(data['time'])
                aggregated[key]['densities'].append(data['density'])

        for key in sorted(aggregated.keys()):
            methods.append(key)
            times.append(np.mean(aggregated[key]['times']) * 1000)
            densities.append(np.mean(aggregated[key]['densities']))

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        ax1.barh(methods, times, color='steelblue')
        ax1.set_xlabel('执行时间 (ms)')
        ax1.set_title('各算法执行时间对比')
        ax1.grid(axis='x', alpha=0.3)

        ax2.barh(methods, densities, color='coral')
        ax2.set_xlabel('边缘密度')
        ax2.set_title('各算法边缘密度对比')
        ax2.grid(axis='x', alpha=0.3)

        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'benchmark.png'), dpi=150, bbox_inches='tight')
        plt.close()

    def _plot_bsds_benchmark(self, all_bsds_metrics, output_dir):
        methods = []
        ods_f1_scores = []
        ois_f1_scores = []
        times = []

        for key in sorted(all_bsds_metrics.keys()):
            methods.append(key)
            aggregated = self.metrics.aggregate_bsds_metrics(all_bsds_metrics[key])
            ods_f1_scores.append(aggregated['ods_f1'])
            ois_f1_scores.append(aggregated['ois_f1'])
            times.append(np.mean([m['time'] for m in all_bsds_metrics[key]]) * 1000)

        fig, axes = plt.subplots(1, 3, figsize=(18, 6))

        y_pos = np.arange(len(methods))
        
        axes[0].barh(y_pos, ods_f1_scores, color='steelblue')
        axes[0].set_yticks(y_pos)
        axes[0].set_yticklabels(methods)
        axes[0].set_xlabel('ODS F1 Score')
        axes[0].set_title('ODS F1 分数对比')
        axes[0].set_xlim(0, 1)
        axes[0].grid(axis='x', alpha=0.3)

        axes[1].barh(y_pos, ois_f1_scores, color='coral')
        axes[1].set_yticks(y_pos)
        axes[1].set_yticklabels(methods)
        axes[1].set_xlabel('OIS F1 Score')
        axes[1].set_title('OIS F1 分数对比')
        axes[1].set_xlim(0, 1)
        axes[1].grid(axis='x', alpha=0.3)

        axes[2].barh(y_pos, times, color='mediumseagreen')
        axes[2].set_yticks(y_pos)
        axes[2].set_yticklabels(methods)
        axes[2].set_xlabel('执行时间 (ms)')
        axes[2].set_title('执行时间对比')
        axes[2].grid(axis='x', alpha=0.3)

        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'bsds_benchmark.png'), dpi=150, bbox_inches='tight')
        plt.close()


def main():
    benchmark = EdgeDetectionBenchmark()

    print("=" * 60)
    print("边缘检测基准测试程序")
    print("=" * 60)
    
    mode = 'bsds'
    
    if mode == 'bsds':
        benchmark.benchmark_bsds500(
            bsds_root='BSDS500',
            split='val',
            output_dir='bsds_results',
            methods=['sobel', 'laplacian', 'canny'],
            preprocess=[None, 'gaussian', 'median'],
            max_images=5
        )
    else:
        input_dir = "input_images"
        output_dir = "output_results"

        if not os.path.exists(input_dir):
            os.makedirs(input_dir)
            print(f"创建输入目录: {input_dir}")
            print("请将测试图片放入该目录后再运行程序")
            return

        print("开始批量处理图片...")
        benchmark.batch_process(
            input_dir, output_dir,
            methods=['sobel', 'laplacian', 'canny'],
            preprocess=[None, 'gaussian', 'median'],
            show_plots=False
        )
        print(f"\n结果已保存到: {output_dir}")


if __name__ == "__main__":
    main()
