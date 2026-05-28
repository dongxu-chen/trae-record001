#!/usr/bin/env python3
import unittest
import numpy as np
import torch
import tempfile
import os

from flow_interpolation import InterpolationConfig
from flow_interpolation.raft import (
    RAFT, load_raft_model,
    bilinear_warp, compute_occlusion_mask,
    compute_occlusion_mask_advanced,
    compute_occlusion_confidence,
    fill_occlusion_regions,
    adaptive_blend_frames,
    resize_flow, normalize_flow,
    gaussian_blur
)
from flow_interpolation.frame_interpolator import (
    FrameInterpolator,
    compute_frames_to_insert,
    compute_interpolation_timestamps
)
from flow_interpolation.motion_blur import (
    apply_motion_blur_simple,
    apply_anisotropic_motion_blur,
    generate_anisotropic_kernel_grid,
    apply_motion_blur_optimized
)
from flow_interpolation.super_resolution import (
    SuperResolutionModel,
    SuperResolutionProcessor,
    create_sr_processor,
    BilinearUpsampler
)
from flow_interpolation.style_transfer import (
    StyleTransferModel,
    StyleTransferProcessor,
    create_style_processor,
    FastStyleTransfer
)
from flow_interpolation.sr_interpolator import (
    InterpolationStrengthController,
    SRFrameInterpolator
)


class TestInterpolationConfig(unittest.TestCase):
    def test_default_config(self):
        config = InterpolationConfig()
        self.assertEqual(config.target_fps, 60)
        self.assertTrue(config.occlusion_detection)
        self.assertTrue(config.motion_blur)
        self.assertIn(config.device, ['cpu', 'cuda'])
    
    def test_cpu_fallback(self):
        config = InterpolationConfig(use_gpu=True)
        if not torch.cuda.is_available():
            self.assertEqual(config.device, 'cpu')
    
    def test_motion_blur_kernel_validation(self):
        config = InterpolationConfig(motion_blur_kernel_size=10)
        self.assertEqual(config.motion_blur_kernel_size, 11)
        
        config2 = InterpolationConfig(motion_blur_kernel_size=2)
        self.assertEqual(config2.motion_blur_kernel_size, 3)


class TestRAFTModel(unittest.TestCase):
    def test_raft_creation(self):
        model = RAFT(small=False)
        self.assertIsNotNone(model)
    
    def test_raft_small(self):
        model = RAFT(small=True)
        self.assertEqual(model.hidden_dim, 96)
        self.assertEqual(model.context_dim, 64)
    
    def test_load_raft_model(self):
        model = load_raft_model(model_path=None, small=False, device='cpu')
        self.assertIsNotNone(model)
        self.assertEqual(next(model.parameters()).device.type, 'cpu')


class TestFlowUtils(unittest.TestCase):
    def test_bilinear_warp(self):
        image = torch.randn(1, 3, 64, 64)
        flow = torch.zeros(1, 2, 64, 64)
        
        warped = bilinear_warp(image, flow)
        self.assertEqual(warped.shape, image.shape)
    
    def test_compute_occlusion_mask(self):
        flow_forward = torch.randn(1, 2, 32, 32)
        flow_backward = -flow_forward + 0.1 * torch.randn_like(flow_forward)
        
        mask = compute_occlusion_mask(flow_forward, flow_backward, threshold=0.1)
        self.assertEqual(mask.shape, (1, 1, 32, 32))
        self.assertTrue((mask >= 0).all() and (mask <= 1).all())
    
    def test_resize_flow(self):
        flow = torch.randn(1, 2, 32, 32)
        resized = resize_flow(flow, 64, 64)
        self.assertEqual(resized.shape, (1, 2, 64, 64))
    
    def test_normalize_flow(self):
        flow = torch.randn(1, 2, 32, 32) * 10
        normalized, magnitude = normalize_flow(flow)
        
        self.assertEqual(normalized.shape, flow.shape)
        self.assertEqual(magnitude.shape, (1, 1, 32, 32))


class TestFrameInterpolator(unittest.TestCase):
    def setUp(self):
        self.config = InterpolationConfig(
            use_gpu=False,
            occlusion_detection=True,
            motion_blur=False
        )
        self.raft_model = load_raft_model(model_path=None, small=True, device='cpu')
        self.interpolator = FrameInterpolator(self.config, self.raft_model)
    
    def test_compute_frames_to_insert(self):
        self.assertEqual(compute_frames_to_insert(24, 60), 1)
        self.assertEqual(compute_frames_to_insert(30, 60), 1)
        self.assertEqual(compute_frames_to_insert(24, 120), 4)
        self.assertEqual(compute_frames_to_insert(60, 30), 0)
    
    def test_compute_interpolation_timestamps(self):
        timestamps = compute_interpolation_timestamps(24, 60)
        self.assertEqual(len(timestamps), 1)
        self.assertAlmostEqual(timestamps[0], 0.5)
        
        timestamps2 = compute_interpolation_timestamps(30, 120)
        self.assertEqual(len(timestamps2), 3)
    
    def test_estimate_optical_flow(self):
        H, W = 64, 64
        frame1 = torch.randint(0, 256, (1, 3, H, W), dtype=torch.float32)
        frame2 = torch.randint(0, 256, (1, 3, H, W), dtype=torch.float32)
        
        flow_forward, flow_backward = self.interpolator.estimate_optical_flow(frame1, frame2)
        self.assertEqual(flow_forward.shape, (1, 2, H, W))
        self.assertEqual(flow_backward.shape, (1, 2, H, W))
    
    def test_interpolate_frame(self):
        H, W = 64, 64
        frame1 = torch.randint(0, 256, (1, 3, H, W), dtype=torch.float32)
        frame2 = torch.randint(0, 256, (1, 3, H, W), dtype=torch.float32)
        
        interp = self.interpolator.interpolate_frame(frame1, frame2, t=0.5)
        self.assertEqual(interp.shape, (1, 3, H, W))
    
    def test_interpolate_multiple_frames(self):
        H, W = 64, 64
        frame1 = torch.randint(0, 256, (1, 3, H, W), dtype=torch.float32)
        frame2 = torch.randint(0, 256, (1, 3, H, W), dtype=torch.float32)
        
        frames = self.interpolator.interpolate_multiple_frames(frame1, frame2, num_intermediate=2)
        self.assertEqual(len(frames), 2)
        self.assertEqual(frames[0].shape, (1, 3, H, W))


class TestMotionBlur(unittest.TestCase):
    def test_apply_motion_blur_simple(self):
        image = torch.randint(0, 256, (1, 3, 64, 64), dtype=torch.float32)
        flow = torch.ones(1, 2, 64, 64) * 10
        
        blurred = apply_motion_blur_simple(image, flow, kernel_size=11, threshold=1.0)
        self.assertEqual(blurred.shape, image.shape)
    
    def test_apply_motion_blur_opencv(self):
        image = np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)
        flow = np.ones((2, 64, 64), dtype=np.float32) * 10
        
        blurred = apply_motion_blur_opencv(image, flow, kernel_size=11, threshold=1.0)
        self.assertEqual(blurred.shape, image.shape)
        self.assertEqual(blurred.dtype, np.uint8)


class TestAdvancedOcclusion(unittest.TestCase):
    def test_compute_occlusion_mask_advanced(self):
        flow_forward = torch.randn(1, 2, 32, 32)
        flow_backward = -flow_forward + 0.1 * torch.randn_like(flow_forward)
        
        mask = compute_occlusion_mask_advanced(flow_forward, flow_backward, threshold=0.1)
        self.assertEqual(mask.shape, (1, 1, 32, 32))
        self.assertTrue((mask >= 0).all() and (mask <= 1).all())
    
    def test_compute_occlusion_confidence(self):
        flow_forward = torch.randn(1, 2, 32, 32)
        flow_backward = -flow_forward + 0.1 * torch.randn_like(flow_forward)
        
        confidence = compute_occlusion_confidence(flow_forward, flow_backward)
        self.assertEqual(confidence.shape, (1, 1, 32, 32))
        self.assertTrue((confidence >= 0).all() and (confidence <= 1).all())
    
    def test_fill_occlusion_regions(self):
        B, C, H, W = 1, 3, 32, 32
        warped1 = torch.rand(B, C, H, W)
        warped2 = torch.rand(B, C, H, W)
        flow_forward = torch.randn(1, 2, H, W)
        flow_backward = -flow_forward
        occlusion_mask = torch.zeros(1, 1, H, W)
        occlusion_mask[:, :, 10:20, 10:20] = 1.0
        original1 = torch.rand(B, C, H, W)
        original2 = torch.rand(B, C, H, W)
        
        filled = fill_occlusion_regions(
            warped1, warped2, flow_forward, flow_backward,
            occlusion_mask, original1, original2, t=0.5
        )
        self.assertEqual(filled.shape, (B, C, H, W))
    
    def test_adaptive_blend_frames(self):
        B, C, H, W = 1, 3, 32, 32
        warped1 = torch.rand(B, C, H, W)
        warped2 = torch.rand(B, C, H, W)
        flow_forward = torch.randn(1, 2, H, W)
        flow_backward = -flow_forward
        
        blended, confidence = adaptive_blend_frames(
            warped1, warped2, flow_forward, flow_backward, t=0.5
        )
        self.assertEqual(blended.shape, (B, C, H, W))
        self.assertEqual(confidence.shape, (1, 1, H, W))
    
    def test_gaussian_blur(self):
        tensor = torch.randn(1, 3, 32, 32)
        blurred = gaussian_blur(tensor, kernel_size=5, sigma=1.0)
        self.assertEqual(blurred.shape, tensor.shape)


class TestAnisotropicMotionBlur(unittest.TestCase):
    def test_generate_anisotropic_kernel_grid(self):
        flow = torch.randn(1, 2, 16, 16) * 10
        kernels = generate_anisotropic_kernel_grid(flow, kernel_size=11, strength=1.0)
        self.assertEqual(kernels.shape, (1, 16 * 16, 11, 11))
        
        kernel_sum = kernels.sum(dim=(-1, -2))
        self.assertTrue(torch.allclose(kernel_sum, torch.ones_like(kernel_sum), atol=1e-5))
    
    def test_apply_anisotropic_motion_blur(self):
        image = torch.randint(0, 256, (1, 3, 32, 32), dtype=torch.float32)
        flow = torch.ones(1, 2, 32, 32) * 10
        
        blurred = apply_anisotropic_motion_blur(
            image, flow, kernel_size=11, strength=1.0, threshold=1.0
        )
        self.assertEqual(blurred.shape, image.shape)
    
    def test_apply_motion_blur_optimized(self):
        image = torch.randint(0, 256, (1, 3, 64, 64), dtype=torch.float32)
        flow = torch.ones(1, 2, 64, 64) * 10
        
        blurred = apply_motion_blur_optimized(
            image, flow, kernel_size=11, strength=1.0, 
            threshold=1.0, tile_size=32
        )
        self.assertEqual(blurred.shape, image.shape)
    
    def test_motion_blur_with_zero_flow(self):
        image = torch.randint(0, 256, (1, 3, 32, 32), dtype=torch.float32)
        flow = torch.zeros(1, 2, 32, 32)
        
        blurred = apply_anisotropic_motion_blur(
            image, flow, kernel_size=11, strength=1.0, threshold=5.0
        )
        self.assertTrue(torch.allclose(blurred, image, atol=1e-5))


class TestGPUOptimizations(unittest.TestCase):
    def test_gpu_tensor_operations(self):
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        image = torch.randint(0, 256, (1, 3, 64, 64), dtype=torch.float32).to(device)
        flow = torch.randn(1, 2, 64, 64).to(device) * 10
        
        flow_mag = torch.sqrt(flow[:, 0:1] ** 2 + flow[:, 1:2] ** 2)
        self.assertEqual(flow_mag.device.type, device)
        
        blurred = apply_anisotropic_motion_blur(
            image, flow, kernel_size=11, strength=1.0, threshold=1.0
        )
        self.assertEqual(blurred.device.type, device)
    
    def test_occlusion_detection_gpu(self):
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        flow_forward = torch.randn(1, 2, 32, 32).to(device)
        flow_backward = -flow_forward + 0.1 * torch.randn_like(flow_forward)
        
        mask = compute_occlusion_mask_advanced(flow_forward, flow_backward)
        self.assertEqual(mask.device.type, device)
        
        confidence = compute_occlusion_confidence(flow_forward, flow_backward)
        self.assertEqual(confidence.device.type, device)
    
    def test_full_interpolation_pipeline(self):
        config = InterpolationConfig(
            use_gpu=torch.cuda.is_available(),
            occlusion_detection=True,
            motion_blur=True,
            bidirectional_flow=True
        )
        
        raft_model = load_raft_model(model_path=None, small=True, device=config.device)
        interpolator = FrameInterpolator(config, raft_model)
        
        H, W = 64, 64
        frame1 = torch.randint(0, 256, (1, 3, H, W), dtype=torch.float32).to(config.device)
        frame2 = torch.randint(0, 256, (1, 3, H, W), dtype=torch.float32).to(config.device)
        
        interp = interpolator.interpolate_frame(frame1, frame2, t=0.5)
        self.assertEqual(interp.shape, (1, 3, H, W))
        self.assertEqual(interp.device.type, config.device)


class TestSuperResolution(unittest.TestCase):
    def test_sr_model_creation(self):
        model = SuperResolutionModel(scale=2)
        self.assertIsNotNone(model)
    
    def test_sr_forward(self):
        model = SuperResolutionModel(scale=2)
        x = torch.randint(0, 256, (1, 3, 32, 32), dtype=torch.float32)
        with torch.no_grad():
            out = model(x)
        self.assertEqual(out.shape, (1, 3, 64, 64))
    
    def test_sr_scale_4(self):
        model = SuperResolutionModel(scale=4)
        x = torch.randint(0, 256, (1, 3, 32, 32), dtype=torch.float32)
        with torch.no_grad():
            out = model(x)
        self.assertEqual(out.shape, (1, 3, 128, 128))
    
    def test_bilinear_upsampler(self):
        upsampler = BilinearUpsampler(scale=2)
        x = torch.randint(0, 256, (1, 3, 32, 32), dtype=torch.float32)
        out = upsampler(x)
        self.assertEqual(out.shape, (1, 3, 64, 64))
    
    def test_sr_processor(self):
        processor = create_sr_processor(scale=2, device='cpu', use_esrgan=False)
        x = torch.randint(0, 256, (1, 3, 32, 32), dtype=torch.float32)
        out = processor.upscale(x)
        self.assertEqual(out.shape, (1, 3, 64, 64))


class TestStyleTransfer(unittest.TestCase):
    def test_style_model_creation(self):
        model = StyleTransferModel(base_channels=32)
        self.assertIsNotNone(model)
    
    def test_style_forward(self):
        model = StyleTransferModel(base_channels=32)
        content = torch.randint(0, 256, (1, 3, 64, 64), dtype=torch.float32)
        style = torch.randint(0, 256, (1, 3, 64, 64), dtype=torch.float32)
        
        with torch.no_grad():
            style_features = model.extract_style_features(style)
            out = model(content, style_features, alpha=1.0)
        
        self.assertEqual(out.shape, (1, 3, 64, 64))
    
    def test_fast_style_transfer(self):
        model = FastStyleTransfer(num_styles=3)
        x = torch.randint(0, 256, (1, 3, 64, 64), dtype=torch.float32)
        
        with torch.no_grad():
            out = model(x, style_idx=0, alpha=0.5)
        
        self.assertEqual(out.shape, (1, 3, 64, 64))
    
    def test_style_processor(self):
        processor = create_style_processor(device='cpu')
        
        style = torch.randint(0, 256, (1, 3, 64, 64), dtype=torch.float32)
        processor.set_style_image(style)
        
        content = torch.randint(0, 256, (1, 3, 64, 64), dtype=torch.float32)
        out = processor.transfer(content, alpha=0.8)
        
        self.assertEqual(out.shape, (1, 3, 64, 64))


class TestInterpolationStrength(unittest.TestCase):
    def test_default_controller(self):
        controller = InterpolationStrengthController()
        self.assertEqual(controller.smoothness, 0.5)
        self.assertEqual(controller.sharpness, 0.5)
    
    def test_custom_controller(self):
        controller = InterpolationStrengthController(smoothness=0.8, sharpness=0.3)
        self.assertEqual(controller.smoothness, 0.8)
        self.assertEqual(controller.sharpness, 0.3)
    
    def test_preset_balanced(self):
        controller = InterpolationStrengthController()
        controller.get_preset('balanced')
        self.assertEqual(controller.smoothness, 0.5)
        self.assertEqual(controller.sharpness, 0.5)
    
    def test_preset_smooth(self):
        controller = InterpolationStrengthController()
        controller.get_preset('smooth')
        self.assertGreater(controller.smoothness, 0.5)
        self.assertLess(controller.sharpness, 0.5)
    
    def test_preset_sharp(self):
        controller = InterpolationStrengthController()
        controller.get_preset('sharp')
        self.assertLess(controller.smoothness, 0.5)
        self.assertGreater(controller.sharpness, 0.5)
    
    def test_flow_weight(self):
        controller = InterpolationStrengthController(smoothness=1.0)
        weight = controller.get_flow_weight()
        self.assertGreater(weight, 0.5)
    
    def test_motion_blur_strength(self):
        controller_smooth = InterpolationStrengthController(smoothness=1.0)
        controller_sharp = InterpolationStrengthController(smoothness=0.0)
        self.assertGreater(
            controller_smooth.get_motion_blur_strength(),
            controller_sharp.get_motion_blur_strength()
        )
    
    def test_clamping(self):
        controller = InterpolationStrengthController(smoothness=1.5, sharpness=-0.5)
        self.assertEqual(controller.smoothness, 1.0)
        self.assertEqual(controller.sharpness, 0.0)


class TestSRFrameInterpolator(unittest.TestCase):
    def setUp(self):
        self.config = InterpolationConfig(
            use_gpu=False,
            occlusion_detection=True,
            motion_blur=False
        )
        self.raft_model = load_raft_model(model_path=None, small=True, device='cpu')
        self.sr_processor = create_sr_processor(scale=2, device='cpu', use_esrgan=False)
        self.interpolator = SRFrameInterpolator(
            self.config, self.raft_model, self.sr_processor
        )
    
    def test_interpolate_with_sr(self):
        H, W = 32, 32
        frame1 = torch.randint(0, 256, (1, 3, H, W), dtype=torch.float32)
        frame2 = torch.randint(0, 256, (1, 3, H, W), dtype=torch.float32)
        
        out = self.interpolator.interpolate_frame(frame1, frame2, t=0.5, use_sr=True)
        self.assertEqual(out.shape, (1, 3, 64, 64))
    
    def test_interpolate_without_sr(self):
        H, W = 32, 32
        frame1 = torch.randint(0, 256, (1, 3, H, W), dtype=torch.float32)
        frame2 = torch.randint(0, 256, (1, 3, H, W), dtype=torch.float32)
        
        out = self.interpolator.interpolate_frame(frame1, frame2, t=0.5, use_sr=False)
        self.assertEqual(out.shape, (1, 3, 32, 32))
    
    def test_set_strength(self):
        self.interpolator.set_strength(preset='smooth')
        self.assertEqual(self.interpolator.strength_controller.smoothness, 0.8)
    
    def test_interpolate_multiple_with_sr(self):
        H, W = 32, 32
        frame1 = torch.randint(0, 256, (1, 3, H, W), dtype=torch.float32)
        frame2 = torch.randint(0, 256, (1, 3, H, W), dtype=torch.float32)
        
        frames = self.interpolator.interpolate_multiple_frames(
            frame1, frame2, num_intermediate=2, use_sr=True
        )
        self.assertEqual(len(frames), 2)
        self.assertEqual(frames[0].shape, (1, 3, 64, 64))
    
    def test_create_slow_motion(self):
        H, W = 32, 32
        frames = [
            torch.randint(0, 256, (1, 3, H, W), dtype=torch.float32)
            for _ in range(3)
        ]
        
        result = self.interpolator.create_slow_motion(
            frames, slow_factor=3, use_sr=True
        )
        expected_length = 3 + 2 * 2
        self.assertEqual(len(result), expected_length)
        self.assertEqual(result[0].shape, (1, 3, 64, 64))


class TestConfigWithNewFeatures(unittest.TestCase):
    def test_sr_config(self):
        config = InterpolationConfig(
            enable_sr=True,
            sr_scale=4,
            smoothness=0.7,
            sharpness=0.6
        )
        self.assertTrue(config.enable_sr)
        self.assertEqual(config.sr_scale, 4)
        self.assertEqual(config.smoothness, 0.7)
    
    def test_style_transfer_config(self):
        config = InterpolationConfig(
            enable_style_transfer=True,
            style_alpha=0.8
        )
        self.assertTrue(config.enable_style_transfer)
        self.assertEqual(config.style_alpha, 0.8)
    
    def test_strength_preset_config(self):
        config = InterpolationConfig(strength_preset='cinematic')
        self.assertEqual(config.smoothness, 0.7)
        self.assertEqual(config.sharpness, 0.6)
    
    def test_sr_and_style_combined(self):
        config = InterpolationConfig(
            enable_sr=True,
            sr_scale=2,
            enable_style_transfer=True,
            style_alpha=0.5,
            strength_preset='balanced'
        )
        self.assertTrue(config.enable_sr)
        self.assertTrue(config.enable_style_transfer)
        self.assertEqual(config.smoothness, 0.5)


if __name__ == '__main__':
    unittest.main(verbosity=2)
