import cv2
import numpy as np
from underwater_enhancer import (UnderwaterImageEnhancer, WhiteBalancer, DarkChannelPrior, 
                                 AdaptiveParameterEstimator, WaterQualityEstimator,
                                 UnderwaterWhiteBalancer, DepthEstimator, ColorRestorer,
                                 FisheyeCorrector)
from quality_evaluator import NoReferenceEvaluator
from video_enhancer import TemporalSmoother, DehazeStrengthInterpolator, VideoProcessor


def create_test_image():
    img = np.zeros((300, 400, 3), dtype=np.uint8)
    
    img[:, :, 0] = 150
    img[:, :, 1] = 120
    img[:, :, 2] = 60
    
    cv2.rectangle(img, (50, 50), (150, 150), (180, 150, 80), -1)
    cv2.circle(img, (300, 200), 50, (160, 130, 70), -1)
    
    noise = np.random.normal(0, 10, img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    return img


def create_test_image_sequence(num_frames: int = 5):
    frames = []
    for i in range(num_frames):
        img = create_test_image()
        variation = np.random.normal(0, 5 + i * 2, img.shape).astype(np.int16)
        img = np.clip(img.astype(np.int16) + variation, 0, 255).astype(np.uint8)
        frames.append(img)
    return frames


def test_underwater_white_balancer():
    print("Testing UnderwaterWhiteBalancer...")
    img = create_test_image()
    
    wb = UnderwaterWhiteBalancer()
    
    result1, info1 = wb.gray_world_red_compensation(img)
    assert result1.shape == img.shape
    assert result1.dtype == np.uint8
    assert 'red_compensation' in info1
    assert 'blue_attenuation' in info1
    
    result2, info2 = wb.adaptive_red_channel_compensation(img, water_type='deep')
    assert result2.shape == img.shape
    assert 'r_compensation' in info2
    
    print("✓ UnderwaterWhiteBalancer tests passed!")


def test_water_quality_estimator():
    print("Testing WaterQualityEstimator...")
    img = create_test_image()
    
    wqe = WaterQualityEstimator()
    
    turbidity = wqe.estimate_turbidity(img)
    assert 0 <= turbidity <= 1.0
    
    depth = wqe.estimate_water_depth(img)
    assert depth in ['shallow', 'moderate', 'deep', 'very_deep']
    
    water_type = wqe.estimate_water_type(img)
    assert isinstance(water_type, str)
    
    quality = wqe.estimate_water_quality(img)
    assert 'turbidity' in quality
    assert 'haze_level' in quality
    assert 'depth' in quality
    assert 'overall_quality' in quality
    
    params = wqe.get_dynamic_attenuation_params(img)
    assert 'red_boost' in params
    assert 'blue_scale' in params
    assert 'omega' in params
    assert 'water_quality' in params
    
    print("✓ WaterQualityEstimator tests passed!")


def test_white_balancer():
    print("Testing WhiteBalancer...")
    img = create_test_image()
    
    wb = WhiteBalancer()
    
    result1 = wb.gray_world(img)
    assert result1.shape == img.shape
    assert result1.dtype == np.uint8
    
    result2 = wb.simple_white_balance(img)
    assert result2.shape == img.shape
    
    result3 = wb.underwater_color_correction(img)
    assert result3.shape == img.shape
    
    result4, info = wb.gray_world_red_compensation(img)
    assert result4.shape == img.shape
    
    print("✓ WhiteBalancer tests passed!")


def test_depth_estimator():
    print("Testing DepthEstimator...")
    img = create_test_image()
    
    de = DepthEstimator()
    
    depth_map = de.estimate_depth_map(img)
    assert depth_map.shape == img.shape[:2]
    assert depth_map.min() >= 0.0
    assert depth_map.max() <= 1.0
    
    result, info = de.depth_guided_enhance(img, depth_map, near_strength=0.6, far_strength=1.4)
    assert result.shape == img.shape
    assert result.dtype == np.uint8
    assert 'depth_map_stats' in info
    
    weighted_params = de.get_depth_weighted_params(depth_map)
    assert 'omega_map' in weighted_params
    assert 'gamma_map' in weighted_params
    assert 'red_boost_map' in weighted_params
    assert weighted_params['omega_map'].shape == depth_map.shape
    
    print("✓ DepthEstimator tests passed!")


def test_color_restorer():
    print("Testing ColorRestorer...")
    img = create_test_image()
    
    cr = ColorRestorer()
    
    attenuation = cr.estimate_underwater_attenuation(img)
    assert 'r_attenuation' in attenuation
    assert 'g_attenuation' in attenuation
    assert 'b_attenuation' in attenuation
    assert 'ref_values' in attenuation
    
    result1, info1 = cr.inverse_attenuation_correction(img, strength=1.0)
    assert result1.shape == img.shape
    assert result1.dtype == np.uint8
    assert 'r_gain_mean' in info1
    
    result2, info2 = cr.wavelength_compensation(img)
    assert result2.shape == img.shape
    assert result2.dtype == np.uint8
    assert 'r_compensation_mean' in info2
    
    result3, info3 = cr.restore_colors(img, strength=1.0)
    assert result3.shape == img.shape
    assert result3.dtype == np.uint8
    assert 'steps' in info3
    
    depth_map = np.random.rand(*img.shape[:2]).astype(np.float32)
    result4, info4 = cr.restore_colors(img, depth_map=depth_map, strength=0.8)
    assert result4.shape == img.shape
    
    print("✓ ColorRestorer tests passed!")


def test_fisheye_corrector():
    print("Testing FisheyeCorrector...")
    img = create_test_image()
    
    fc = FisheyeCorrector()
    
    fc.auto_calibrate(img, k1=-0.3, k2=0.1)
    assert fc._calibrated == True
    
    result1, info1 = fc.correct(img)
    assert result1.shape[0] == img.shape[0]
    assert result1.shape[1] == img.shape[1]
    assert 'calibrated' in info1
    
    fc2 = FisheyeCorrector()
    result2, info2 = fc2.correct_and_crop(img)
    assert 'cropped' in info2
    
    fc3 = FisheyeCorrector()
    distortion_info = fc3.estimate_distortion(img)
    assert 'estimated_k1' in distortion_info
    assert 'confidence' in distortion_info
    
    camera_matrix = np.array([[400, 0, 200], [0, 400, 150], [0, 0, 1]], dtype=np.float64)
    dist_coeffs = np.array([-0.3, 0.1, 0, 0, 0], dtype=np.float64)
    fc4 = FisheyeCorrector()
    fc4.set_calibration(camera_matrix, dist_coeffs)
    assert fc4._calibrated == True
    result4, info4 = fc4.correct(img)
    assert result4.shape[0] == img.shape[0]
    
    print("✓ FisheyeCorrector tests passed!")


def test_temporal_smoother():
    print("Testing TemporalSmoother...")
    
    smoother = TemporalSmoother(smoothing_factor=0.8, history_size=5)
    
    params1 = {'omega': 0.9, 'red_boost': 1.3, 'gamma': 1.0}
    smoothed1 = smoother.smooth(params1)
    assert smoothed1['omega'] == params1['omega']
    
    params2 = {'omega': 0.95, 'red_boost': 1.5, 'gamma': 0.9}
    smoothed2 = smoother.smooth(params2)
    
    assert smoothed2['omega'] > params1['omega']
    assert smoothed2['omega'] < params2['omega']
    
    smoother.reset()
    assert smoother.current_smoothed is None
    
    print("✓ TemporalSmoother tests passed!")


def test_dehaze_interpolator():
    print("Testing DehazeStrengthInterpolator...")
    
    interpolator = DehazeStrengthInterpolator(max_change=0.05, smoothing_window=3)
    
    omega1 = interpolator.interpolate(0.9)
    assert omega1 == 0.9
    
    omega2 = interpolator.interpolate(1.0)
    assert abs(omega2 - 0.9) <= 0.051
    
    interpolator.reset()
    assert interpolator.last_omega is None
    
    print("✓ DehazeStrengthInterpolator tests passed!")


def test_video_processor_temporal():
    print("Testing VideoProcessor with temporal smoothing...")
    
    processor = VideoProcessor(
        use_adaptive=True,
        use_temporal_smoothing=True,
        smoothing_factor=0.8,
        max_omega_change=0.03
    )
    
    frames = create_test_image_sequence(5)
    
    last_omega = None
    for i, frame in enumerate(frames):
        enhanced, info = processor.process_frame(frame)
        
        assert enhanced.shape == frame.shape
        assert 'temporal_smoothed_params' in info
        
        current_omega = info['temporal_smoothed_params']['omega']
        if last_omega is not None and i > 0:
            assert abs(current_omega - last_omega) <= 0.051
        
        last_omega = current_omega
    
    processor.reset_temporal_state()
    
    print("✓ VideoProcessor temporal tests passed!")


def test_dark_channel_prior():
    print("Testing DarkChannelPrior...")
    img = create_test_image()
    
    dcp = DarkChannelPrior(patch_size=15, omega=0.95)
    
    dark = dcp.get_dark_channel(img.astype(np.float32))
    assert dark.shape == img.shape[:2]
    
    A = dcp.estimate_atmospheric_light(img.astype(np.float32), dark)
    assert A.shape == (3,)
    
    t = dcp.estimate_transmission(img.astype(np.float32), A)
    assert t.shape == img.shape[:2]
    
    result, t_refined, A_final = dcp.enhance(img)
    assert result.shape == img.shape
    assert result.dtype == np.uint8
    
    print("✓ DarkChannelPrior tests passed!")


def test_adaptive_parameter_estimator():
    print("Testing AdaptiveParameterEstimator...")
    img = create_test_image()
    
    ape = AdaptiveParameterEstimator()
    
    r, g, b = ape.estimate_color_cast(img)
    assert 0 <= r <= 1 and 0 <= g <= 1 and 0 <= b <= 1
    
    brightness = ape.estimate_brightness(img)
    assert 0 <= brightness <= 1
    
    contrast = ape.estimate_contrast(img)
    assert contrast >= 0
    
    haze = ape.estimate_haze_level(img)
    assert 0 <= haze <= 1
    
    params = ape.get_adaptive_params(img)
    assert 'red_boost' in params
    assert 'blue_scale' in params
    assert 'gamma' in params
    assert 'omega' in params
    assert 'clahe_clip' in params
    
    print("✓ AdaptiveParameterEstimator tests passed!")


def test_underwater_image_enhancer():
    print("Testing UnderwaterImageEnhancer...")
    img = create_test_image()
    
    enhancer = UnderwaterImageEnhancer(use_adaptive=True)
    result, info = enhancer.enhance(img)
    assert result.shape == img.shape
    assert result.dtype == np.uint8
    assert 'adaptive_params' in info
    assert 'steps' in info
    
    enhancer2 = UnderwaterImageEnhancer(use_adaptive=False, red_boost=1.5)
    result2, info2 = enhancer2.enhance(img)
    assert result2.shape == img.shape
    
    print("✓ UnderwaterImageEnhancer tests passed!")


def test_enhancer_with_depth():
    print("Testing UnderwaterImageEnhancer with depth estimation...")
    img = create_test_image()
    
    enhancer = UnderwaterImageEnhancer(
        use_adaptive=True,
        use_depth_estimation=True,
        use_color_restoration=False,
        use_fisheye_correction=False,
        near_strength=0.5,
        far_strength=1.5
    )
    result, info = enhancer.enhance(img)
    assert result.shape == img.shape
    assert result.dtype == np.uint8
    assert 'depth_info' in info
    assert 'depth_guided' in info['steps']
    
    print("✓ Enhancer with depth estimation tests passed!")


def test_enhancer_with_color_restoration():
    print("Testing UnderwaterImageEnhancer with color restoration...")
    img = create_test_image()
    
    enhancer = UnderwaterImageEnhancer(
        use_adaptive=True,
        use_depth_estimation=True,
        use_color_restoration=True,
        use_fisheye_correction=False,
        color_restoration_strength=1.0
    )
    result, info = enhancer.enhance(img)
    assert result.shape == img.shape
    assert result.dtype == np.uint8
    assert 'color_restoration_info' in info
    assert 'color_restoration' in info['steps']
    
    print("✓ Enhancer with color restoration tests passed!")


def test_enhancer_with_fisheye():
    print("Testing UnderwaterImageEnhancer with fisheye correction...")
    img = create_test_image()
    
    enhancer = UnderwaterImageEnhancer(
        use_adaptive=True,
        use_depth_estimation=False,
        use_color_restoration=False,
        use_fisheye_correction=True
    )
    result, info = enhancer.enhance(img)
    assert result.shape[2] == img.shape[2]
    assert result.dtype == np.uint8
    assert 'fisheye_info' in info
    assert 'fisheye_correction' in info['steps']
    
    print("✓ Enhancer with fisheye correction tests passed!")


def test_enhancer_full_pipeline():
    print("Testing UnderwaterImageEnhancer full pipeline...")
    img = create_test_image()
    
    enhancer = UnderwaterImageEnhancer(
        use_adaptive=True,
        use_depth_estimation=True,
        use_color_restoration=True,
        use_fisheye_correction=True,
        color_restoration_strength=0.8,
        near_strength=0.5,
        far_strength=1.5
    )
    result, info = enhancer.enhance(img)
    assert result.shape[2] == img.shape[2]
    assert result.dtype == np.uint8
    assert 'color_restoration_info' in info
    assert 'depth_info' in info
    assert 'fisheye_info' in info
    assert 'color_restoration' in info['steps']
    assert 'depth_guided' in info['steps']
    assert 'fisheye_correction' in info['steps']
    
    print("✓ Full pipeline tests passed!")


def test_quality_evaluator():
    print("Testing QualityEvaluator...")
    img = create_test_image()
    
    metrics = NoReferenceEvaluator.evaluate(img)
    assert 'contrast' in metrics
    assert 'sharpness' in metrics
    assert 'color_fidelity' in metrics
    assert 'overall_quality' in metrics
    
    enhancer = UnderwaterImageEnhancer(use_adaptive=True)
    enhanced, _ = enhancer.enhance(img)
    
    comparison = NoReferenceEvaluator.compare(img, enhanced)
    assert 'original' in comparison
    assert 'enhanced' in comparison
    assert 'improvement' in comparison
    
    print("✓ QualityEvaluator tests passed!")


def run_all_tests():
    print("=" * 50)
    print("Running all tests...")
    print("=" * 50)
    
    try:
        test_underwater_white_balancer()
        test_white_balancer()
        test_water_quality_estimator()
        test_depth_estimator()
        test_color_restorer()
        test_fisheye_corrector()
        test_temporal_smoother()
        test_dehaze_interpolator()
        test_dark_channel_prior()
        test_adaptive_parameter_estimator()
        test_underwater_image_enhancer()
        test_enhancer_with_depth()
        test_enhancer_with_color_restoration()
        test_enhancer_with_fisheye()
        test_enhancer_full_pipeline()
        test_video_processor_temporal()
        test_quality_evaluator()
        
        print("=" * 50)
        print("All tests passed! ✓")
        print("=" * 50)
        return True
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
