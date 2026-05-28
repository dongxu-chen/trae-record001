import numpy as np
import cv2
import os
import time
from poisson_editing import PoissonEditing, MultigridSolver


def create_test_images():
    os.makedirs("test_images", exist_ok=True)
    
    src = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.circle(src, (50, 50), 35, (255, 100, 50), -1)
    cv2.circle(src, (40, 40), 8, (255, 255, 255), -1)
    cv2.imwrite("test_images/src_circle.png", src)
    
    dst = np.zeros((200, 300, 3), dtype=np.uint8)
    for y in range(200):
        for x in range(300):
            dst[y, x] = [100 + int(50 * np.sin(y / 15)), 
                         150 + int(50 * np.cos(x / 20)), 
                         200]
    cv2.imwrite("test_images/dst_background.png", dst)
    
    mask = np.zeros((100, 100), dtype=np.uint8)
    cv2.circle(mask, (50, 50), 40, 255, -1)
    cv2.imwrite("test_images/mask_circle.png", mask)
    
    print("测试图像已创建到 test_images/ 目录")
    return src, dst, mask


def test_multigrid_basic():
    print("\n=== 测试1: 多网格法基本融合 ===")
    
    src, dst, mask = create_test_images()
    
    poisson = PoissonEditing(solver_type='multigrid')
    
    start_time = time.time()
    result = poisson.seamless_clone(src, dst, mask, (150, 100), mix_weight=1.0, feather=False)
    elapsed = time.time() - start_time
    
    cv2.imwrite("test_images/result_multigrid_basic.png", result)
    
    naive = dst.copy()
    h, w = src.shape[:2]
    y, x = 100 - h // 2, 150 - w // 2
    naive[y:y+h, x:x+w][mask > 0] = src[mask > 0]
    cv2.imwrite("test_images/result_naive.png", naive)
    
    print(f"多网格法基本融合完成! 耗时: {elapsed:.2f}秒")
    print(f"  源图像尺寸: {src.shape}")
    print(f"  目标图像尺寸: {dst.shape}")
    print("  输出: test_images/result_multigrid_basic.png")
    
    return result


def test_feather_effect():
    print("\n=== 测试2: 边界羽化效果 ===")
    
    src = cv2.imread("test_images/src_circle.png")
    dst = cv2.imread("test_images/dst_background.png")
    mask = cv2.imread("test_images/mask_circle.png", cv2.IMREAD_GRAYSCALE)
    
    if src is None or dst is None or mask is None:
        src, dst, mask = create_test_images()
    
    poisson = PoissonEditing(solver_type='multigrid')
    
    for feather_radius in [0, 3, 5, 10]:
        poisson.feather_radius = feather_radius
        result = poisson.seamless_clone(src, dst, mask, (150, 100), mix_weight=1.0, feather=True)
        cv2.imwrite(f"test_images/result_feather_{feather_radius}.png", result)
        print(f"  羽化半径 {feather_radius}: 完成")
    
    print("羽化效果测试完成!")
    print("  输出: test_images/result_feather_*.png")


def test_gradient_mixing():
    print("\n=== 测试3: 梯度混合 ===")
    
    src = cv2.imread("test_images/src_circle.png")
    dst = cv2.imread("test_images/dst_background.png")
    mask = cv2.imread("test_images/mask_circle.png", cv2.IMREAD_GRAYSCALE)
    
    if src is None or dst is None or mask is None:
        src, dst, mask = create_test_images()
    
    poisson = PoissonEditing(solver_type='multigrid')
    
    for mix_weight in [0.0, 0.5, 1.0]:
        result = poisson.seamless_clone(src, dst, mask, (150, 100), mix_weight=mix_weight, feather=True)
        cv2.imwrite(f"test_images/result_mix_{mix_weight:.1f}.png", result)
        print(f"  混合权重 {mix_weight:.1f}: 完成")
    
    print("梯度混合测试完成!")


def test_memory_advantage():
    print("\n=== 测试4: 内存效率说明 ===")
    print("  多网格法相比稀疏矩阵+共轭梯度法的优势:")
    print("    1. 内存占用: O(N)  vs  稀疏矩阵O(Nz)")
    print("    2. 无需构建大型稀疏矩阵，节省内存")
    print("    3. 每层网格内存按1/4递减")
    print("    4. 大图像时内存优势更明显")
    print("    5. 矢量化操作更快，利用NumPy优化")


def test_offscreen_drawing_info():
    print("\n=== 测试5: 离屏绘制说明 ===")
    print("  GUI笔刷绘制改进:")
    print("    1. OffscreenCanvas类管理离屏缓冲")
    print("    2. 脏区域(dirty region)追踪，只更新变化部分")
    print("    3. 节流更新(throttling): ~60fps，避免频繁重绘")
    print("    4. 增量更新代替全屏重绘")
    print("    5. 笔刷移动时更跟手，延迟更低")


def run_all_tests():
    print("=" * 60)
    print("泊松图像编辑 (多网格法+羽化) - 测试套件")
    print("=" * 60)
    
    test_multigrid_basic()
    test_feather_effect()
    test_gradient_mixing()
    test_memory_advantage()
    test_offscreen_drawing_info()
    
    print("\n" + "=" * 60)
    print("所有测试完成!")
    print("请查看 test_images/ 目录下的结果")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
