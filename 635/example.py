import numpy as np
import cv2
import os
import matplotlib.pyplot as plt
from cs_reconstruction import (
    RandomSampling,
    GaussianSampling,
    BlockSampling,
    VerticalLineSampling,
    HorizontalLineSampling,
    PoissonDiskSampling,
    CSReconstructor,
    FFTReconstructor,
    CSImageProcessor,
    BatchProcessor,
    ResultVisualizer,
    QualityEvaluator,
    ImageHandler,
    get_sampling_patterns
)


def generate_test_image(size=(64, 64)):
    h, w = size
    image = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(image, (w//4, h//4), min(w, h)//6, 200, -1)
    cv2.rectangle(image, (w//2, h//4), (3*w//4, 3*h//4), 150, -1)
    cv2.line(image, (w//4, 3*h//4), (3*w//4, 3*h//4), 255, 3)
    image = cv2.GaussianBlur(image.astype(np.float32), (3, 3), 0.5).astype(np.uint8)
    return image


def example_1_single_image_reconstruction():
    print("=" * 60)
    print("示例 1: 单图像压缩感知重建")
    print("=" * 60)
    original = generate_test_image((64, 64))
    sampling_pattern = RandomSampling()
    reconstructor = FFTReconstructor(tv_weight=0.5, max_iter=100)
    processor = CSImageProcessor(sampling_pattern, reconstructor)
    result = processor.process_image(original, sampling_ratio=0.3)
    print(f"采样率: {result['sampling_ratio']:.2%}")
    print(f"PSNR: {result['quality']['PSNR']:.2f} dB")
    print(f"SSIM: {result['quality']['SSIM']:.4f}")
    ResultVisualizer.plot_single_result(result, save_path='single_result.png')
    return result


def example_2_compare_sampling_patterns():
    print("\n" + "=" * 60)
    print("示例 2: 不同采样模式对比")
    print("=" * 60)
    original = generate_test_image((64, 64))
    patterns = get_sampling_patterns()
    reconstructor = FFTReconstructor(tv_weight=0.5, max_iter=80)
    results = []
    titles = []
    for name, pattern in patterns.items():
        print(f"处理 {name} 采样...")
        processor = CSImageProcessor(pattern, reconstructor)
        result = processor.process_image(original, sampling_ratio=0.25)
        result['pattern_name'] = name
        results.append(result)
        titles.append(name)
        print(f"  PSNR: {result['quality']['PSNR']:.2f} dB, SSIM: {result['quality']['SSIM']:.4f}")
    ResultVisualizer.plot_comparison(results, titles, save_path='pattern_comparison.png')
    ResultVisualizer.plot_quality_comparison(results, save_path='quality_comparison.png')
    return results


def example_3_sampling_ratio_analysis():
    print("\n" + "=" * 60)
    print("示例 3: 采样率影响分析")
    print("=" * 60)
    original = generate_test_image((64, 64))
    pattern = RandomSampling()
    reconstructor = FFTReconstructor(tv_weight=0.5, max_iter=80)
    processor = CSImageProcessor(pattern, reconstructor)
    ratios = [0.1, 0.2, 0.3, 0.4, 0.5, 0.7]
    results = []
    for ratio in ratios:
        result = processor.process_image(original, sampling_ratio=ratio)
        result['pattern_name'] = 'RandomSampling'
        results.append(result)
        print(f"采样率 {ratio:.1%}: PSNR = {result['quality']['PSNR']:.2f} dB, SSIM = {result['quality']['SSIM']:.4f}")
    ResultVisualizer.plot_quality_comparison(results, save_path='ratio_analysis.png')
    return results


def example_4_batch_processing():
    print("\n" + "=" * 60)
    print("示例 4: 批量图像处理")
    print("=" * 60)
    input_dir = 'test_images'
    output_dir = 'results'
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    for i in range(3):
        img = generate_test_image((64, 64))
        cv2.imwrite(f'{input_dir}/test_image_{i}.png', img)
    pattern = RandomSampling()
    reconstructor = FFTReconstructor(tv_weight=0.5, max_iter=80)
    processor = CSImageProcessor(pattern, reconstructor)
    batch_processor = BatchProcessor(input_dir, output_dir, processor)
    sampling_ratios = [0.2, 0.4]
    patterns_list = [RandomSampling(), GaussianSampling()]
    results = batch_processor.process_batch(
        sampling_ratios=sampling_ratios,
        patterns=patterns_list,
        file_pattern='*.png'
    )
    print(f"\n批量处理完成，共处理 {len(results)} 张图像")
    return results


def example_5_tune_tv_weight():
    print("\n" + "=" * 60)
    print("示例 5: TV权重参数调优")
    print("=" * 60)
    original = generate_test_image((64, 64))
    pattern = RandomSampling()
    tv_weights = [0.1, 0.5, 1.0, 2.0, 5.0]
    results = []
    for weight in tv_weights:
        reconstructor = FFTReconstructor(tv_weight=weight, max_iter=80)
        processor = CSImageProcessor(pattern, reconstructor)
        result = processor.process_image(original, sampling_ratio=0.3)
        result['pattern_name'] = f'TV_weight={weight}'
        results.append(result)
        print(f"TV权重 {weight}: PSNR = {result['quality']['PSNR']:.2f} dB, SSIM = {result['quality']['SSIM']:.4f}")
    ResultVisualizer.plot_quality_comparison(results, save_path='tv_weight_tuning.png')
    return results


def example_6_color_image():
    print("\n" + "=" * 60)
    print("示例 6: 彩色图像处理")
    print("=" * 60)
    h, w = 64, 64
    original = np.zeros((h, w, 3), dtype=np.uint8)
    original[:, :, 0] = generate_test_image((h, w))
    original[:, :, 1] = generate_test_image((h, w))
    original[:, :, 2] = generate_test_image((h, w))
    pattern = RandomSampling()
    reconstructor = FFTReconstructor(tv_weight=0.5, max_iter=80)
    processor = CSImageProcessor(pattern, reconstructor)
    result = processor.process_image(original, sampling_ratio=0.3)
    print(f"彩色图像 - 采样率: {result['sampling_ratio']:.2%}")
    print(f"PSNR: {result['quality']['PSNR']:.2f} dB")
    print(f"SSIM: {result['quality']['SSIM']:.4f}")
    return result


def main():
    np.random.seed(42)
    print("压缩感知图像重建系统 - 示例程序")
    print("本程序演示多种压缩感知图像重建功能\n")
    example_1_single_image_reconstruction()
    example_2_compare_sampling_patterns()
    example_3_sampling_ratio_analysis()
    example_4_batch_processing()
    example_5_tune_tv_weight()
    example_6_color_image()
    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("生成的图像已保存到当前目录")
    print("=" * 60)


if __name__ == "__main__":
    main()
