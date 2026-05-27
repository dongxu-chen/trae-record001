import os
import sys
import numpy as np
import cv2
import matplotlib.pyplot as plt


def create_test_images(output_dir='test_images'):
    os.makedirs(output_dir, exist_ok=True)
    
    h, w = 300, 400
    
    img1 = np.ones((h, w, 3), dtype=np.uint8) * 200
    cv2.circle(img1, (100, 150), 50, (255, 100, 100), -1)
    cv2.rectangle(img1, (250, 100), (350, 200), (100, 255, 100), -1)
    cv2.putText(img1, 'A', (80, 160), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
    cv2.imwrite(os.path.join(output_dir, 'test1.jpg'), img1)
    
    img2 = np.ones((h, w, 3), dtype=np.uint8) * 200
    cv2.circle(img2, (150, 150), 50, (255, 100, 100), -1)
    cv2.rectangle(img2, (300, 100), (380, 200), (100, 100, 255), -1)
    cv2.putText(img2, 'B', (130, 160), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
    cv2.imwrite(os.path.join(output_dir, 'test2.jpg'), img2)
    
    img3 = np.ones((h, w, 3), dtype=np.uint8) * 200
    cv2.circle(img3, (200, 150), 50, (255, 100, 100), -1)
    cv2.rectangle(img3, (50, 100), (150, 200), (100, 100, 255), -1)
    cv2.putText(img3, 'C', (180, 160), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
    cv2.imwrite(os.path.join(output_dir, 'test3.jpg'), img3)
    
    print(f'测试图像已生成到: {output_dir}/')
    return [os.path.join(output_dir, f'test{i}.jpg') for i in range(1, 4)]


def create_large_test_images(output_dir='test_images', size=3000):
    os.makedirs(output_dir, exist_ok=True)
    
    h, w = size, size
    
    img1 = np.ones((h, w, 3), dtype=np.uint8) * 180
    for i in range(0, w//3, 100):
        cv2.rectangle(img1, (i, 0), (i+50, h), (i%255, (i*2)%255, (i*3)%255), -1)
    cv2.putText(img1, 'LEFT', (w//4, h//2), cv2.FONT_HERSHEY_SIMPLEX, 5, (255, 255, 255), 10)
    cv2.imwrite(os.path.join(output_dir, 'large1.jpg'), img1)
    
    img2 = np.ones((h, w, 3), dtype=np.uint8) * 200
    for i in range(0, w//3, 100):
        cv2.rectangle(img2, (i, 0), (i+50, h), ((i+100)%255, (i*2+50)%255, (i*3+100)%255), -1)
    cv2.putText(img2, 'CENTER', (w//4, h//2), cv2.FONT_HERSHEY_SIMPLEX, 5, (255, 255, 255), 10)
    cv2.imwrite(os.path.join(output_dir, 'large2.jpg'), img2)
    
    img3 = np.ones((h, w, 3), dtype=np.uint8) * 220
    for i in range(0, w//3, 100):
        cv2.rectangle(img3, (i, 0), (i+50, h), ((i+200)%255, (i*2+100)%255, (i*3+200)%255), -1)
    cv2.putText(img3, 'RIGHT', (w//4, h//2), cv2.FONT_HERSHEY_SIMPLEX, 5, (255, 255, 255), 10)
    cv2.imwrite(os.path.join(output_dir, 'large3.jpg'), img3)
    
    print(f'大图测试图像已生成到: {output_dir}/')
    return [os.path.join(output_dir, f'large{i}.jpg') for i in range(1, 4)]


def create_360_test_images(output_dir='test_images'):
    os.makedirs(output_dir, exist_ok=True)
    
    h, w = 400, 600
    
    for i in range(6):
        img = np.ones((h, w, 3), dtype=np.uint8) * 100
        angle = i * 60
        
        cv2.putText(img, f'View {i}', (50, h//2), cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 255, 255), 5)
        
        color = np.array([50 + i*30, 100, 150 - i*20])
        img[:h//3, :] = color
        img[h//3:2*h//3, :] = color * 1.2
        img[2*h//3:, :] = color * 0.8
        
        path = os.path.join(output_dir, f'view_{i:02d}.jpg')
        cv2.imwrite(path, img)
    
    print(f'360度测试图像已生成到: {output_dir}/')
    return [os.path.join(output_dir, f'view_{i:02d}.jpg') for i in range(6)]


def test_feature_matcher():
    print('=== 测试 FeatureMatcher ===')
    from feature_matcher import FeatureMatcher
    
    matcher = FeatureMatcher(n_features=2000)
    img1 = cv2.imread('test_images/test1.jpg')
    img2 = cv2.imread('test_images/test2.jpg')
    
    kp1, des1 = matcher.detect_and_compute(img1)
    kp2, des2 = matcher.detect_and_compute(img2)
    
    print(f'图像1特征点数量: {len(kp1)}')
    print(f'图像2特征点数量: {len(kp2)}')
    
    matches = matcher.match_features(des1, des2)
    print(f'匹配点数量: {len(matches)}')
    
    match_img = matcher.draw_matches(img1, img2, kp1, kp2, matches)
    
    plt.figure(figsize=(12, 6))
    plt.imshow(cv2.cvtColor(match_img, cv2.COLOR_BGR2RGB))
    plt.title('Feature Matching')
    plt.axis('off')
    plt.savefig('test_feature_match.png', dpi=100)
    plt.close()
    print('特征匹配可视化已保存: test_feature_match.png')
    print()


def test_homography():
    print('=== 测试 HomographyEstimator (改进版RANSAC) ===')
    from feature_matcher import FeatureMatcher
    from homography import HomographyEstimator
    
    matcher = FeatureMatcher()
    estimator = HomographyEstimator(ransac_threshold=3.0, confidence=0.999, 
                                    max_iters=10000, reproj_threshold=2.0)
    
    img1 = cv2.imread('test_images/test1.jpg')
    img2 = cv2.imread('test_images/test2.jpg')
    
    kp1, des1 = matcher.detect_and_compute(img1)
    kp2, des2 = matcher.detect_and_compute(img2)
    
    matches = matcher.match_features(des1, des2)
    pts1, pts2 = matcher.get_matched_points(kp1, kp2, matches)
    
    H, mask = estimator.estimate_homography(pts1, pts2)
    print(f'单应矩阵:\n{H}')
    print(f'内点比例: {np.sum(mask) / len(mask):.2%}')
    
    h, w = img1.shape[:2]
    warped = estimator.warp_image(img2, H, (w * 2, h))
    
    plt.figure(figsize=(12, 6))
    plt.subplot(1, 2, 1)
    plt.imshow(cv2.cvtColor(img1, cv2.COLOR_BGR2RGB))
    plt.title('Image 1')
    plt.axis('off')
    plt.subplot(1, 2, 2)
    plt.imshow(cv2.cvtColor(warped, cv2.COLOR_BGR2RGB))
    plt.title('Warped Image 2')
    plt.axis('off')
    plt.savefig('test_homography.png', dpi=100)
    plt.close()
    print('单应变换可视化已保存: test_homography.png')
    print()


def test_projection():
    print('=== 测试 ImageProjector ===')
    from projection import ImageProjector
    
    projector = ImageProjector(focal_length=500)
    img = cv2.imread('test_images/test1.jpg')
    
    cyl_img = projector.cylindrical_projection(img)
    sph_img = projector.spherical_projection(img)
    
    plt.figure(figsize=(15, 5))
    plt.subplot(1, 3, 1)
    plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    plt.title('Original')
    plt.axis('off')
    plt.subplot(1, 3, 2)
    plt.imshow(cv2.cvtColor(cyl_img, cv2.COLOR_BGR2RGB))
    plt.title('Cylindrical')
    plt.axis('off')
    plt.subplot(1, 3, 3)
    plt.imshow(cv2.cvtColor(sph_img, cv2.COLOR_BGR2RGB))
    plt.title('Spherical')
    plt.axis('off')
    plt.savefig('test_projection.png', dpi=100)
    plt.close()
    print('投影变换可视化已保存: test_projection.png')
    print()


def test_adaptive_blending():
    print('=== 测试 Adaptive MultiBandBlender ===')
    from multi_band_blend import MultiBandBlender
    
    blender = MultiBandBlender(num_levels=5, adaptive=True, gain_compensation=True)
    
    img1 = np.zeros((200, 300, 3), dtype=np.uint8)
    img1[:, :150] = [200, 100, 100]
    img1[:, 150:] = [100, 200, 100]
    
    img2 = np.zeros((200, 300, 3), dtype=np.uint8)
    img2[:, :150] = [100, 100, 200]
    img2[:, 150:] = [200, 200, 100]
    
    mask1 = np.ones((200, 300), dtype=np.uint8) * 255
    mask1[:, 200:] = 0
    
    mask2 = np.ones((200, 300), dtype=np.uint8) * 255
    mask2[:, :100] = 0
    
    blended = blender.blend_two_images(img1, img2, mask1, mask2)
    feather = blender.simple_feather_blend(img1, img2, mask1, mask2)
    
    print(f'自适应融合启用: {blender.adaptive}')
    print(f'增益补偿启用: {blender.gain_compensation}')
    
    plt.figure(figsize=(15, 8))
    plt.subplot(2, 2, 1)
    plt.imshow(cv2.cvtColor(img1, cv2.COLOR_BGR2RGB))
    plt.title('Image 1')
    plt.axis('off')
    plt.subplot(2, 2, 2)
    plt.imshow(cv2.cvtColor(img2, cv2.COLOR_BGR2RGB))
    plt.title('Image 2')
    plt.axis('off')
    plt.subplot(2, 2, 3)
    plt.imshow(cv2.cvtColor(blended, cv2.COLOR_BGR2RGB))
    plt.title('Adaptive Multi-band Blend')
    plt.axis('off')
    plt.subplot(2, 2, 4)
    plt.imshow(cv2.cvtColor(feather, cv2.COLOR_BGR2RGB))
    plt.title('Feather Blend')
    plt.axis('off')
    plt.savefig('test_blending.png', dpi=100)
    plt.close()
    print('融合效果可视化已保存: test_blending.png')
    print()


def test_gain_compensation():
    print('=== 测试增益补偿 ===')
    from multi_band_blend import MultiBandBlender
    
    blender = MultiBandBlender(num_levels=5, adaptive=True, gain_compensation=True)
    
    img1 = np.ones((200, 300, 3), dtype=np.uint8) * 100
    img1[:, 100:200] = [200, 150, 100]
    
    img2 = np.ones((200, 300, 3), dtype=np.uint8) * 180
    img2[:, 100:200] = [180, 160, 140]
    
    mask1 = np.ones((200, 300), dtype=np.uint8) * 255
    mask2 = np.ones((200, 300), dtype=np.uint8) * 255
    
    mean1, mean2 = blender._compute_overlap_brightness(img1, img2, mask1, mask2)
    print(f'图像1平均亮度: {mean1:.1f}')
    print(f'图像2平均亮度: {mean2:.1f}')
    
    blended = blender.blend_two_images(img1, img2, mask1, mask2)
    
    plt.figure(figsize=(15, 5))
    plt.subplot(1, 3, 1)
    plt.imshow(cv2.cvtColor(img1, cv2.COLOR_BGR2RGB))
    plt.title(f'Image 1 (mean={mean1:.0f})')
    plt.axis('off')
    plt.subplot(1, 3, 2)
    plt.imshow(cv2.cvtColor(img2, cv2.COLOR_BGR2RGB))
    plt.title(f'Image 2 (mean={mean2:.0f})')
    plt.axis('off')
    plt.subplot(1, 3, 3)
    plt.imshow(cv2.cvtColor(blended, cv2.COLOR_BGR2RGB))
    plt.title('Gain Compensated Blend')
    plt.axis('off')
    plt.savefig('test_gain_compensation.png', dpi=100)
    plt.close()
    print('增益补偿可视化已保存: test_gain_compensation.png')
    print()


def test_full_stitch():
    print('=== 测试完整拼接流程 ===')
    from panorama_stitcher import PanoramaStitcher
    
    image_paths = ['test_images/test1.jpg', 'test_images/test2.jpg']
    
    stitcher = PanoramaStitcher(projection_type='plane', blend_type='multiband')
    
    try:
        panorama = stitcher.stitch(image_paths=image_paths)
        panorama = stitcher.crop_black_borders(panorama)
        
        cv2.imwrite('test_panorama.jpg', panorama)
        print(f'全景图已保存: test_panorama.jpg ({panorama.shape[1]}x{panorama.shape[0]})')
    except Exception as e:
        print(f'拼接可能因测试图像特征不足而失败: {e}')
    print()


def test_block_stitching():
    print('=== 测试大图分块拼接 ===')
    from panorama_stitcher import PanoramaStitcher
    
    print('创建大图测试集...')
    large_paths = create_large_test_images(size=2500)
    
    stitcher = PanoramaStitcher(
        projection_type='plane', 
        blend_type='multiband',
        use_block_stitching=True,
        block_size=1500,
        block_overlap=200
    )
    
    try:
        print('开始分块拼接...')
        panorama = stitcher.stitch(image_paths=large_paths)
        panorama = stitcher.crop_black_borders(panorama)
        
        cv2.imwrite('test_block_panorama.jpg', panorama)
        print(f'分块拼接全景图已保存: test_block_panorama.jpg ({panorama.shape[1]}x{panorama.shape[0]})')
        
        for path in large_paths:
            if os.path.exists(path):
                os.remove(path)
                print(f'已删除临时文件: {path}')
    except Exception as e:
        print(f'分块拼接测试: {e}')
    print()


def test_360_stitch():
    print('=== 测试360度全景拼接 ===')
    from equirectangular import Panorama360Stitcher
    
    print('创建360度测试图像...')
    paths = create_360_test_images()
    
    try:
        images = [cv2.imread(p) for p in paths]
        
        stitcher_360 = Panorama360Stitcher(output_width=2048)
        
        angles = [i * 60.0 for i in range(6)]
        
        print('生成360度全景...')
        panorama = stitcher_360.stitch_360(images, angles=angles, fov=70)
        panorama = stitcher_360.blend_360_seams(panorama, num_views=6)
        
        cv2.imwrite('test_360_panorama.jpg', panorama)
        print(f'360度全景已保存: test_360_panorama.jpg ({panorama.shape[1]}x{panorama.shape[0]})')
        
        preview = stitcher_360.generate_360_preview(panorama, (800, 400))
        cv2.imwrite('test_360_preview.jpg', preview)
        
        plt.figure(figsize=(16, 8))
        plt.imshow(cv2.cvtColor(preview, cv2.COLOR_BGR2RGB))
        plt.title('360° Panorama Preview')
        plt.axis('off')
        plt.savefig('test_360_result.png', dpi=100)
        plt.close()
        
    except Exception as e:
        print(f'360度拼接测试: {e}')
        import traceback
        traceback.print_exc()
    print()


def test_camera_calibration():
    print('=== 测试相机自动标定 ===')
    from camera_calibration import CameraCalibrator
    
    test_images = [cv2.imread('test_images/test1.jpg'), cv2.imread('test_images/test2.jpg')]
    
    calibrator = CameraCalibrator()
    
    try:
        print('从场景特征自动估计相机参数...')
        camera_matrix, dist_coeffs = calibrator.auto_calibrate_from_scene(test_images)
        
        print(f'估计焦距: {camera_matrix[0, 0]:.1f}')
        print(f'相机矩阵:\n{camera_matrix}')
        
        print('测试畸变修正...')
        undistorted = calibrator.undistort_image(test_images[0])
        
        plt.figure(figsize=(15, 5))
        plt.subplot(1, 2, 1)
        plt.imshow(cv2.cvtColor(test_images[0], cv2.COLOR_BGR2RGB))
        plt.title('Original')
        plt.axis('off')
        plt.subplot(1, 2, 2)
        plt.imshow(cv2.cvtColor(undistorted, cv2.COLOR_BGR2RGB))
        plt.title('Undistorted')
        plt.axis('off')
        plt.savefig('test_calibration.png', dpi=100)
        plt.close()
        
        print('相机标定测试完成')
        
    except Exception as e:
        print(f'相机标定测试: {e}')
    print()


def test_equirectangular_projection():
    print('=== 测试等距柱状投影 ===')
    from equirectangular import EquirectangularProjector
    
    img = cv2.imread('test_images/test1.jpg')
    
    projector = EquirectangularProjector(output_width=2048)
    
    try:
        print('测试透视转等距柱状投影...')
        equirect = projector.perspective_to_equirectangular(img, fov_h=90, fov_v=60, yaw=0, pitch=0)
        
        cv2.imwrite('test_equirect.jpg', equirect)
        
        print('测试全景旋转...')
        rotated = projector.rotate_equirectangular(equirect, yaw=45, pitch=10)
        
        cv2.imwrite('test_equirect_rotated.jpg', rotated)
        
        plt.figure(figsize=(16, 4))
        plt.subplot(1, 2, 1)
        plt.imshow(cv2.cvtColor(equirect, cv2.COLOR_BGR2RGB))
        plt.title('Equirectangular')
        plt.axis('off')
        plt.subplot(1, 2, 2)
        plt.imshow(cv2.cvtColor(rotated, cv2.COLOR_BGR2RGB))
        plt.title('Rotated (yaw=45°, pitch=10°)')
        plt.axis('off')
        plt.savefig('test_equirectangular.png', dpi=100)
        plt.close()
        
        print(f'等距柱状投影尺寸: {equirect.shape[1]}x{equirect.shape[0]}')
        
    except Exception as e:
        print(f'等距柱状投影测试: {e}')
        import traceback
        traceback.print_exc()
    print()


def main():
    print('=' * 70)
    print('全景图拼接工具 - 完整功能测试')
    print('=' * 70)
    print()
    
    try:
        create_test_images()
        print()
        
        test_feature_matcher()
        test_homography()
        test_projection()
        test_adaptive_blending()
        test_gain_compensation()
        test_full_stitch()
        test_camera_calibration()
        test_equirectangular_projection()
        test_360_stitch()
        
        print('=' * 70)
        print('执行大图分块拼接测试 (耗时较长)...')
        print('=' * 70)
        test_block_stitching()
        
        print('=' * 70)
        print('所有测试完成!')
        print('=' * 70)
        
    except ImportError as e:
        print(f'导入错误: {e}')
        print('请先安装依赖: pip install -r requirements.txt')
        sys.exit(1)
    except Exception as e:
        print(f'测试失败: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
