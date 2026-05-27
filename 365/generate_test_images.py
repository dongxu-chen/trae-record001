import numpy as np
import cv2
import os
from typing import List, Tuple


def generate_scene(size: Tuple[int, int] = (600, 800)) -> np.ndarray:
    h, w = size
    scene = np.zeros((h, w, 3), dtype=np.float64)
    
    cx, cy = w // 2, h // 2
    y, x = np.mgrid[0:h, 0:w]
    
    for i, (intensity, radius, color) in enumerate([
        (10000.0, 40, (1.0, 0.9, 0.8)),
        (5000.0, 60, (0.9, 0.95, 1.0)),
        (2000.0, 80, (1.0, 0.8, 0.7)),
        (1000.0, 100, (0.8, 1.0, 0.9)),
        (500.0, 120, (0.9, 0.85, 1.0)),
    ]):
        ox = cx + int(np.cos(i * 2 * np.pi / 5) * 200)
        oy = cy + int(np.sin(i * 2 * np.pi / 5) * 150)
        dist = np.sqrt((x - ox) ** 2 + (y - oy) ** 2)
        mask = dist < radius
        falloff = np.maximum(0, 1 - dist / radius)
        for c in range(3):
            scene[:, :, c] += intensity * color[c] * falloff
    
    scene[:, :, 0] += 50
    scene[:, :, 1] += 60
    scene[:, :, 2] += 80
    
    gradient = np.linspace(0.2, 1.0, h).reshape(-1, 1, 1)
    scene = scene * gradient
    
    return scene


def apply_camera_response(hdr_scene: np.ndarray, 
                          response_curve: np.ndarray,
                          exposure_time: float,
                          gamma: float = 2.2) -> np.ndarray:
    irradiance = hdr_scene * exposure_time
    log_irradiance = np.log(irradiance + 1e-8)
    
    z_vals = np.interp(
        log_irradiance.flatten(),
        response_curve,
        np.arange(256, dtype=np.float64)
    )
    z_vals = z_vals.reshape(hdr_scene.shape)
    z_vals = np.clip(z_vals, 0, 255)
    
    return z_vals.astype(np.uint8)


def create_response_curve() -> np.ndarray:
    z = np.arange(256, dtype=np.float64)
    normalized_z = z / 255.0
    
    g = 1.0 / 2.2
    linear_part = normalized_z ** g
    
    log_x = np.log(0.01 + 100 * linear_part)
    
    return log_x


def generate_test_sequence(output_dir: str = "test_images",
                           num_images: int = 5,
                           exposure_times: List[float] = None) -> Tuple[List[str], np.ndarray]:
    if exposure_times is None:
        exposure_times = [1.0 / 1000, 1.0 / 500, 1.0 / 250, 1.0 / 125, 1.0 / 60]
    
    os.makedirs(output_dir, exist_ok=True)
    
    hdr_scene = generate_scene()
    response_curve = create_response_curve()
    
    image_paths = []
    for i, exp in enumerate(exposure_times):
        ldr = apply_camera_response(hdr_scene, response_curve, exp)
        path = os.path.join(output_dir, f"img_{i:02d}_exp_{exp:.6f}.png")
        cv2.imwrite(path, ldr)
        image_paths.append(path)
        print(f"生成: {path}")
    
    ground_truth_path = os.path.join(output_dir, "ground_truth.hdr")
    cv2.imwrite(ground_truth_path, hdr_scene.astype(np.float32))
    print(f"生成真值 HDR: {ground_truth_path}")
    
    return image_paths, np.array(exposure_times, dtype=np.float64)


def main():
    import matplotlib
    matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    matplotlib.rcParams['axes.unicode_minus'] = False
    import matplotlib.pyplot as plt
    
    print("生成测试 HDR 图像序列...")
    output_dir = "test_images"
    
    exposure_times = [1.0 / 2000, 1.0 / 1000, 1.0 / 500, 1.0 / 250, 1.0 / 125, 1.0 / 60]
    
    image_paths, exposures = generate_test_sequence(output_dir, exposure_times=exposure_times)
    
    print(f"\n生成了 {len(image_paths)} 张测试图像")
    print("曝光时间 (秒):")
    for exp in exposures:
        print(f"  {exp:.6f} (1/{1/exp:.0f})")
    
    response_curve = create_response_curve()
    plt.figure(figsize=(8, 5))
    plt.plot(np.arange(256), response_curve, 'b-', linewidth=2)
    plt.xlabel('像素值 Z')
    plt.ylabel('log 曝光量 X')
    plt.title('相机响应曲线 (用于生成测试图像)')
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(output_dir, "response_curve_truth.png"), dpi=150)
    plt.close()
    
    print(f"\n响应曲线图已保存到: {os.path.join(output_dir, 'response_curve_truth.png')}")
    print(f"所有文件保存在: {os.path.abspath(output_dir)}")


if __name__ == "__main__":
    main()
