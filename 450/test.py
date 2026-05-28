import os
import sys
import cv2
import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from models import ReflectionSeparationNet, PerceptualLoss
from core import ReflectionRemover, Evaluator
from utils import BatchProcessor, Visualizer
from data import PolarizationProcessor, denormalize, tensor_to_numpy


def generate_test_image(size=(256, 256)):
    h, w = size
    background = np.zeros((h, w, 3), dtype=np.uint8)
    cv2.putText(background, 'BACKGROUND', (w//4, h//2), cv2.FONT_HERSHEY_SIMPLEX, 
                1.5, (0, 255, 0), 3, cv2.LINE_AA)
    cv2.rectangle(background, (50, 50), (100, 100), (255, 0, 0), -1)
    cv2.circle(background, (200, 200), 40, (0, 0, 255), -1)
    
    reflection = np.zeros((h, w, 3), dtype=np.uint8)
    cv2.putText(reflection, 'REFLECTION', (w//4, h//3), cv2.FONT_HERSHEY_SIMPLEX, 
                1, (255, 255, 255), 2, cv2.LINE_AA)
    reflection = cv2.GaussianBlur(reflection, (15, 15), 0)
    
    alpha = 0.7
    blended = cv2.addWeighted(background, alpha, reflection, 1 - alpha, 0)
    
    return blended, background, reflection


def test_model_forward():
    print("Testing model forward pass...")
    config = Config()
    model = ReflectionSeparationNet(
        n_channels=config.model.n_channels,
        bilinear=config.model.bilinear,
        use_polarization=False
    )
    
    x = torch.randn(2, 3, 256, 256)
    with torch.no_grad():
        t, r, alpha = model(x)
    
    assert t.shape == x.shape, f"Transmission shape mismatch: {t.shape} vs {x.shape}"
    assert r.shape == x.shape, f"Reflection shape mismatch: {r.shape} vs {x.shape}"
    assert alpha.shape == (2, 1, 256, 256), f"Alpha shape mismatch: {alpha.shape}"
    print("  [OK] Model forward pass works correctly")


def test_model_with_polarization():
    print("Testing model with polarization...")
    model = ReflectionSeparationNet(use_polarization=True)
    
    x = torch.randn(2, 3, 256, 256)
    pol = torch.randn(2, 3, 256, 256)
    with torch.no_grad():
        t, r, alpha = model(x, pol)
    
    assert t.shape == x.shape
    print("  [OK] Model with polarization works correctly")


def test_perceptual_loss():
    print("Testing perceptual loss...")
    criterion = PerceptualLoss()
    
    pred_t = torch.rand(2, 3, 256, 256, requires_grad=True)
    pred_r = torch.rand(2, 3, 256, 256, requires_grad=True)
    pred_alpha = torch.rand(2, 1, 256, 256, requires_grad=True)
    target_t = torch.rand(2, 3, 256, 256)
    target_r = torch.rand(2, 3, 256, 256)
    input_img = torch.rand(2, 3, 256, 256)
    
    losses = criterion(pred_t, pred_r, pred_alpha, target_t, target_r, input_img)
    
    assert 'total' in losses
    assert 'recon' in losses
    assert 'transmission' in losses
    assert 'reflection' in losses
    assert 'alpha' in losses
    assert 'gradient' in losses
    
    losses['total'].backward()
    print("  [OK] Perceptual loss works correctly")


def test_evaluator():
    print("Testing evaluator...")
    evaluator = Evaluator()
    
    img1 = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
    img2 = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
    input_img = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
    
    metrics = evaluator.evaluate(img1, img2, input_img)
    
    assert 'psnr' in metrics
    assert 'ssim' in metrics
    assert 'rmse' in metrics
    assert 'mae' in metrics
    assert 'psnr_improvement' in metrics
    assert 'ssim_improvement' in metrics
    assert 'reflection_suppression' in metrics
    assert 'niqe' in metrics
    
    psnr = evaluator.compute_psnr(img1, img1)
    assert psnr == float('inf') or psnr > 100
    
    ssim_val = evaluator.compute_ssim(img1, img1)
    assert abs(ssim_val - 1.0) < 1e-3
    
    print("  [OK] Evaluator works correctly")
    print(f"    PSNR: {metrics['psnr']:.2f}")
    print(f"    SSIM: {metrics['ssim']:.4f}")


def test_polarization_processor():
    print("Testing polarization processor...")
    
    images = [np.random.rand(256, 256, 3) for _ in range(4)]
    angles = [0, 45, 90, 135]
    
    stokes = PolarizationProcessor.compute_stokes(images, angles)
    assert stokes.shape == (256, 256, 3)
    
    dolp = PolarizationProcessor.compute_degree_of_polarization(stokes)
    assert dolp.shape == (256, 256)
    assert dolp.min() >= 0 and dolp.max() <= 1
    
    aop = PolarizationProcessor.compute_angle_of_polarization(stokes)
    assert aop.shape == (256, 256)
    
    mask = PolarizationProcessor.extract_reflection_mask(stokes)
    assert mask.shape == (256, 256)
    
    print("  [OK] Polarization processor works correctly")


def test_reflection_remover():
    print("Testing reflection remover...")
    config = Config()
    
    remover = ReflectionRemover(config)
    
    test_img, gt_bg, gt_refl = generate_test_image()
    
    results = remover.remove_reflection(test_img)
    
    assert 'input' in results
    assert 'transmission' in results
    assert 'reflection' in results
    assert 'alpha' in results
    
    assert results['input'].shape == test_img.shape
    assert results['transmission'].shape == test_img.shape
    assert results['reflection'].shape == test_img.shape
    assert results['alpha'].shape == test_img.shape[:2]
    
    print("  [OK] Reflection remover works correctly")
    
    return results, test_img, gt_bg


def test_visualizer():
    print("Testing visualizer...")
    config = Config()
    remover = ReflectionRemover(config)
    visualizer = Visualizer(figsize=(10, 8), dpi=72)
    
    test_img, gt_bg, _ = generate_test_image()
    results = remover.remove_reflection(test_img)
    
    os.makedirs('test_output', exist_ok=True)
    
    visualizer.visualize_results(
        results,
        save_path='test_output/vis_results.png',
        show=False,
        title='Test Visualization'
    )
    
    evaluator = Evaluator()
    metrics = evaluator.evaluate(results['transmission'], gt_bg, results['input'])
    
    visualizer.visualize_comparison(
        results['input'],
        results['transmission'],
        ground_truth=gt_bg,
        reflection=results['reflection'],
        metrics=metrics,
        save_path='test_output/vis_comparison.png',
        show=False
    )
    
    metrics_list = [metrics, {k: v * 0.8 for k, v in metrics.items()}]
    visualizer.plot_metrics_comparison(
        metrics_list=[{k: v for k, v in metrics.items() if isinstance(v, float)} for metrics in metrics_list],
        labels=['Method A', 'Method B'],
        save_path='test_output/metrics_comparison.png',
        show=False
    )
    
    assert os.path.exists('test_output/vis_results.png')
    assert os.path.exists('test_output/vis_comparison.png')
    assert os.path.exists('test_output/metrics_comparison.png')
    
    print("  [OK] Visualizer works correctly")


def test_batch_processor():
    print("Testing batch processor...")
    config = Config()
    
    test_dir = 'test_data'
    output_dir = 'test_output/batch'
    os.makedirs(test_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    for i in range(5):
        img, _, _ = generate_test_image()
        cv2.imwrite(os.path.join(test_dir, f'test_{i}.png'), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    
    processor = BatchProcessor(config)
    results = processor.process_directory(test_dir, output_dir)
    
    assert results['total_processed'] == 5
    assert results['total_failed'] == 0
    
    print("  [OK] Batch processor works correctly")


def test_tensor_utils():
    print("Testing tensor utilities...")
    
    tensor = torch.randn(2, 3, 256, 256)
    denormed = denormalize(tensor)
    
    assert denormed.shape == tensor.shape
    assert denormed.min() >= -1
    
    np_img = tensor_to_numpy(tensor)
    assert np_img.shape == (2, 256, 256, 3)
    assert np_img.dtype == np.uint8
    assert np_img.min() >= 0 and np_img.max() <= 255
    
    print("  [OK] Tensor utilities work correctly")


def test_texture_synthesis():
    print("Testing texture synthesis...")
    from core.texture_synthesis import TextureSynthesizer, InpaintingConfig
    
    config = InpaintingConfig(
        patch_size=9,
        alpha_threshold=0.3,
        max_iterations=100,
        use_telea=True
    )
    synthesizer = TextureSynthesizer(config)
    
    h, w = 256, 256
    image = np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)
    
    mask = np.zeros((h, w), dtype=np.uint8)
    mask[100:150, 100:150] = 255
    
    alpha_mask = np.ones((h, w), dtype=np.uint8) * 200
    alpha_mask[100:150, 100:150] = 50
    
    strong_mask = synthesizer.detect_strong_reflection(image, alpha_mask, None)
    assert strong_mask.shape == (h, w)
    assert strong_mask.dtype == np.uint8
    
    inpainted_telea = synthesizer.inpaint_telea(image, mask)
    assert inpainted_telea.shape == image.shape
    
    inpainted_ns = synthesizer.inpaint_ns(image, mask)
    assert inpainted_ns.shape == image.shape
    
    test_img, gt_bg, gt_refl = generate_test_image((h, w))
    reflection = cv2.GaussianBlur(
        np.random.randint(0, 256, (h, w, 3), dtype=np.uint8), (15, 15), 0
    )
    
    restored, strong_mask = synthesizer.restore_strong_reflection(
        test_img, alpha_mask, reflection, gt_bg
    )
    assert restored.shape == image.shape
    assert strong_mask.shape == (h, w)
    
    print("  [OK] Texture synthesis works correctly")


def test_polarization_estimator():
    print("Testing polarization estimator...")
    from models.polarization_estimator import (
        TraditionalPolarizationEstimator, PolarizationEstimationConfig
    )
    
    estimator = TraditionalPolarizationEstimator()
    
    h, w = 256, 256
    image = np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)
    
    results = estimator.estimate(image)
    
    assert 'dolp' in results
    assert 'aop' in results
    assert 'stokes' in results
    assert 'polarization_mask' in results
    
    assert results['dolp'].shape == (h, w)
    assert results['aop'].shape == (h, w)
    assert results['stokes'].shape == (h, w, 3)
    assert results['polarization_mask'].shape == (h, w)
    
    assert results['dolp'].min() >= 0 and results['dolp'].max() <= 1
    assert results['aop'].min() >= 0 and results['aop'].max() <= np.pi
    
    results_color = estimator.estimate_from_color(image)
    assert results_color['dolp'].shape == (h, w)
    assert results_color['polarization_mask'].shape == (h, w)
    
    config = PolarizationEstimationConfig()
    assert config.base_channels == 32
    assert config.use_attention == True
    
    print("  [OK] Polarization estimator works correctly")


def test_mos_evaluator():
    print("Testing MOS evaluator...")
    from core.mos_evaluator import MOSEvaluator, MOSDataset, MOSScore, ASPECTS
    
    mos_evaluator = MOSEvaluator()
    
    dataset = mos_evaluator.create_mos_dataset("test_dataset")
    
    for i in range(10):
        aspect_scores = {
            'overall': np.random.uniform(1, 5),
            'reflection_removal': np.random.uniform(1, 5),
            'detail_preservation': np.random.uniform(1, 5),
            'naturalness': np.random.uniform(1, 5),
            'artifact': np.random.uniform(1, 5),
            'sharpness': np.random.uniform(1, 5)
        }
        mos_evaluator.add_aspect_score(
            dataset,
            image_id=f'image_{i % 5}',
            scores=aspect_scores,
            rater_id=f'rater_{i // 5}'
        )
    
    assert len(dataset.scores) == 10
    assert len(dataset.get_all_image_ids()) == 5
    
    avg_score = dataset.get_average_score('image_0')
    assert 1 <= avg_score <= 5
    
    std_score = dataset.get_std_score('image_0')
    assert std_score >= 0
    
    restored = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
    ground_truth = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
    input_img = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
    
    obj_metrics = mos_evaluator.evaluate_objective(restored, ground_truth, input_img)
    assert 'psnr' in obj_metrics
    assert 'ssim' in obj_metrics
    assert 'rmse' in obj_metrics
    
    obj_mos = mos_evaluator.compute_objective_mos(obj_metrics)
    assert 1 <= obj_mos <= 5
    
    comp_scores = mos_evaluator.compute_comprehensive_score(3.5, obj_metrics)
    assert 'subjective_mos' in comp_scores
    assert 'objective_mos' in comp_scores
    assert 'comprehensive_score' in comp_scores
    assert 'confidence' in comp_scores
    
    subj_scores = [3.2, 4.1, 2.8, 4.5, 3.7]
    obj_scores = [3.0, 3.9, 3.1, 4.2, 3.5]
    correlation = mos_evaluator.compute_correlation(subj_scores, obj_scores)
    assert 'pearson' in correlation
    assert 'spearman' in correlation
    assert 'kendall' in correlation
    
    reliability = mos_evaluator.analyze_rater_reliability(dataset)
    assert len(reliability) == 2
    
    os.makedirs('test_output', exist_ok=True)
    report = mos_evaluator.generate_comprehensive_report(
        dataset, None, 'test_output/mos_report'
    )
    assert os.path.exists('test_output/mos_report/mos_report.json')
    assert os.path.exists('test_output/mos_report/mos_distribution.png')
    
    print("  [OK] MOS evaluator works correctly")


def test_integrated_pipeline():
    print("Testing integrated pipeline with new features...")
    config = Config()
    config.inference.enable_texture_synthesis = True
    config.inference.enable_polarization_estimation = True
    config.polarization.estimate_from_image = True
    config.polarization.use_traditional_method = True
    
    remover = ReflectionRemover(config)
    
    test_img, gt_bg, _ = generate_test_image()
    
    results = remover.remove_reflection(test_img)
    
    assert 'input' in results
    assert 'transmission' in results
    assert 'reflection' in results
    assert 'alpha' in results
    assert 'estimated_dolp' in results
    assert 'estimated_aop' in results
    assert 'polarization_mask' in results
    assert 'inpainted' in results
    assert 'strong_reflection_mask' in results
    
    assert results['estimated_dolp'].shape == test_img.shape[:2]
    assert results['estimated_aop'].shape == test_img.shape[:2]
    assert results['polarization_mask'].shape == test_img.shape[:2]
    assert results['strong_reflection_mask'].shape == test_img.shape[:2]
    assert results['inpainted'].shape == test_img.shape
    
    print("  [OK] Integrated pipeline works correctly")


def test_video_processor():
    print("Testing video processor...")
    from core.video_processor import OpticalFlowEstimator, TemporalConsistencyFilter, VideoConfig
    
    flow_estimator = OpticalFlowEstimator(method='farneback')
    
    h, w = 256, 256
    frame1 = np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)
    frame2 = np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)
    
    flow = flow_estimator.compute_flow(frame1, frame2)
    assert flow.shape == (h, w, 2), f"Expected flow shape {(h, w, 2)}, got {flow.shape}"
    
    warped = flow_estimator.warp_frame(frame1, flow)
    assert warped.shape == frame1.shape
    
    flow_mask = flow_estimator.compute_flow_mask(flow, max_flow=50.0)
    assert flow_mask.shape == (h, w)
    assert flow_mask.min() >= 0 and flow_mask.max() <= 1
    
    temporal_filter = TemporalConsistencyFilter(window_size=3, blend_factor=0.3)
    temporal_filter.reset()
    
    for i in range(5):
        frame = np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)
        filtered = temporal_filter.filter_frame(frame)
        assert filtered.shape == frame.shape
    
    video_config = VideoConfig(
        temporal_window=3,
        flow_method='farneback',
        consistency_weight=0.4
    )
    assert video_config.temporal_window == 3
    assert video_config.flow_method == 'farneback'
    
    print("  [OK] Video processor works correctly")


def test_reflection_detector():
    print("Testing reflection detector...")
    from core.reflection_detector import ReflectionDetector, ReflectionDetectorNet, DetectionConfig
    
    detector = ReflectionDetector()
    
    h, w = 256, 256
    
    clean_img = np.random.randint(30, 180, (h, w, 3), dtype=np.uint8)
    has_refl, confidence = ReflectionDetector.detect(clean_img)
    assert isinstance(has_refl, bool)
    assert isinstance(confidence, float)
    assert 0 <= confidence <= 1
    
    reflective_img = np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)
    reflective_img[50:100, 50:100] = 250
    
    mask, mask_conf = detector.detect_mask(reflective_img)
    assert mask.shape == (h, w)
    assert mask.dtype == np.uint8
    assert 0 <= mask_conf <= 1
    
    images = [clean_img, reflective_img]
    batch_results = detector.detect_batch(images, skip_no_reflection=True)
    assert len(batch_results) == 2
    for r in batch_results:
        assert 'has_reflection' in r
        assert 'confidence' in r
        assert 'should_process' in r
        assert 'reflection_mask' in r
    
    det_net = ReflectionDetectorNet()
    x = torch.randn(1, 3, 256, 256)
    with torch.no_grad():
        out = det_net(x)
    assert out.shape == (1, 1, 256, 256)
    
    config = DetectionConfig(confidence_threshold=0.5)
    assert config.confidence_threshold == 0.5
    
    print("  [OK] Reflection detector works correctly")


def test_multitask_net():
    print("Testing joint multi-task network...")
    from models.multitask_net import (
        JointMultiTaskNet, MultiTaskProcessor, MultiTaskLoss, MultiTaskConfig
    )
    
    config = MultiTaskConfig(shared_channels=32, num_shared_blocks=2)
    
    model = JointMultiTaskNet(config)
    x = torch.randn(1, 3, 256, 256)
    
    with torch.no_grad():
        predictions = model(x)
    
    assert 'reflection' in predictions
    assert 'derain' in predictions
    assert 'dehaze' in predictions
    
    assert 'transmission' in predictions['reflection']
    assert 'alpha' in predictions['reflection']
    assert 'clean' in predictions['derain']
    assert 'rain_mask' in predictions['derain']
    assert 'clean' in predictions['dehaze']
    assert 'transmission_map' in predictions['dehaze']
    assert 'airlight' in predictions['dehaze']
    
    loss_fn = MultiTaskLoss(config)
    targets = {
        'transmission': torch.rand(1, 3, 256, 256),
        'alpha': torch.rand(1, 1, 256, 256),
        'clean': torch.rand(1, 3, 256, 256)
    }
    input_img = torch.randn(1, 3, 256, 256)
    
    losses = loss_fn(predictions, targets, input_img)
    assert 'total_loss' in losses
    assert losses['total_loss'].requires_grad
    
    with torch.no_grad():
        predictions_single = model(x, tasks=['reflection'])
    assert 'reflection' in predictions_single
    assert 'derain' not in predictions_single
    
    processor = MultiTaskProcessor(config)
    h, w = 256, 256
    test_img = np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)
    
    results = processor.process(test_img)
    assert 'input' in results
    assert 'reflection_transmission' in results
    assert 'derain_clean' in results
    assert 'dehaze_clean' in results
    
    results_joint = processor.process_joint(
        test_img,
        reflection_weight=0.5,
        derain_weight=0.25,
        dehaze_weight=0.25
    )
    assert 'fused_clean' in results_joint
    
    print("  [OK] Joint multi-task network works correctly")


def run_all_tests():
    print("="*60)
    print("Running all tests for Reflection Removal System v3.0")
    print("="*60)
    print()
    
    tests = [
        test_model_forward,
        test_model_with_polarization,
        test_perceptual_loss,
        test_evaluator,
        test_polarization_processor,
        test_reflection_remover,
        test_visualizer,
        test_batch_processor,
        test_tensor_utils,
        test_texture_synthesis,
        test_polarization_estimator,
        test_mos_evaluator,
        test_integrated_pipeline,
        test_video_processor,
        test_reflection_detector,
        test_multitask_net
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
        print()
    
    print("="*60)
    print(f"Tests completed: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    
    import shutil
    if os.path.exists('test_output'):
        shutil.rmtree('test_output')
    if os.path.exists('test_data'):
        shutil.rmtree('test_data')
    if os.path.exists('output'):
        shutil.rmtree('output')
    
    sys.exit(0 if success else 1)
