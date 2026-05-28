#!/usr/bin/env python3
import os
import numpy as np
import cv2
import torch

from flow_interpolation import VideoInterpolator, InterpolationConfig


def example_basic_usage():
    print('=== Example 1: Basic Video Interpolation ===')
    
    config = InterpolationConfig(
        target_fps=60,
        source_fps=24,
        use_gpu=True,
        occlusion_detection=True,
        motion_blur=True,
        bidirectional_flow=True
    )
    
    interpolator = VideoInterpolator(config)
    
    input_video = 'input_video.mp4'
    output_video = 'output_video_60fps.mp4'
    
    if os.path.exists(input_video):
        interpolator.process_video(input_video, output_video)
        print(f'Processed video saved to {output_video}')
    else:
        print(f'Input video {input_video} not found, skipping...')


def example_frame_pair_interpolation():
    print('\n=== Example 2: Single Frame Pair Interpolation ===')
    
    config = InterpolationConfig(
        use_gpu=False,
        occlusion_detection=True,
        motion_blur=False
    )
    
    interpolator = VideoInterpolator(config)
    
    frame1 = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    frame2 = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    
    for shift in [2, 4, 8]:
        frame2_shifted = np.roll(frame1, shift, axis=1)
        
        interp_frame = interpolator.interpolate_frame_pair(frame1, frame2_shifted, t=0.5)
        
        print(f'  Shift={shift}: Interpolated frame shape = {interp_frame.shape}')
        
        cv2.imwrite(f'frame1_shift{shift}.png', frame1)
        cv2.imwrite(f'frame2_shift{shift}.png', frame2_shifted)
        cv2.imwrite(f'interp_shift{shift}.png', interp_frame)
        
        print(f'  Saved frames for shift={shift}')


def example_custom_config():
    print('\n=== Example 3: Custom Configuration ===')
    
    config = InterpolationConfig(
        target_fps=120,
        source_fps=30,
        use_gpu=True,
        raft_iters=20,
        raft_small=False,
        occlusion_detection=True,
        occlusion_threshold=0.005,
        motion_blur=True,
        motion_blur_kernel_size=15,
        motion_blur_strength=1.5,
        bidirectional_flow=True,
        output_crf=16,
        output_preset='slow',
        save_flow_visualization=True
    )
    
    print('Custom configuration:')
    print(f'  Target FPS: {config.target_fps}')
    print(f'  RAFT iterations: {config.raft_iters}')
    print(f'  Motion blur kernel: {config.motion_blur_kernel_size}')
    print(f'  Save flow visualization: {config.save_flow_visualization}')


def example_optical_flow_estimation():
    print('\n=== Example 4: Optical Flow Estimation ===')
    
    config = InterpolationConfig(
        use_gpu=False,
        raft_iters=12
    )
    
    interpolator = VideoInterpolator(config)
    
    frame1 = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    frame2 = np.roll(frame1, 5, axis=1)
    
    flow = interpolator.get_optical_flow(frame1, frame2)
    
    print(f'  Flow shape: {flow.shape}')
    print(f'  Flow range: [{flow.min():.2f}, {flow.max():.2f}]')
    print(f'  Mean flow magnitude: {np.sqrt(flow[0]**2 + flow[1]**2).mean():.2f}')


if __name__ == '__main__':
    print('Running Flow Interpolation Examples\n')
    
    try:
        example_custom_config()
    except Exception as e:
        print(f'Example 3 failed: {e}')
    
    try:
        example_optical_flow_estimation()
    except Exception as e:
        print(f'Example 4 failed: {e}')
    
    try:
        example_frame_pair_interpolation()
    except Exception as e:
        print(f'Example 2 failed: {e}')
    
    print('\nAll examples completed.')
