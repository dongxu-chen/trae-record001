import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
from tqdm import tqdm

from config import Config
from core import VideoSaliencyDetector, FrameSmoother, smooth_saliency_sequence
from utils.helpers import load_image, save_image


def example_smoothing_methods():
    print("=" * 60)
    print("EXAMPLE: Frame Smoothing Methods")
    print("=" * 60)
    
    methods = ['temporal', 'bilateral', 'gaussian', 'flow']
    
    test_saliency = []
    for i in range(10):
        base = np.zeros((256, 256), dtype=np.float32)
        center_x = 128 + int(30 * np.sin(i * 0.5))
        center_y = 128 + int(20 * np.cos(i * 0.3))
        for y in range(256):
            for x in range(256):
                dist = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
                base[y, x] = np.exp(-dist ** 2 / (2 * 50 ** 2))
        noise = np.random.normal(0, 0.05, base.shape).astype(np.float32)
        test_saliency.append(np.clip(base + noise, 0, 1))
    
    test_frame = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
    
    for method in methods:
        print(f"\nTesting {method} smoothing...")
        smoother = FrameSmoother(method=method, window_size=5)
        
        smoothed = []
        for sal in test_saliency:
            smoothed_sal = smoother.smooth(sal, test_frame)
            smoothed.append(smoothed_sal)
        
        original_var = np.var([s.mean() for s in test_saliency])
        smoothed_var = np.var([s.mean() for s in smoothed])
        
        print(f"  Original variance: {original_var:.6f}")
        print(f"  Smoothed variance: {smoothed_var:.6f}")
        print(f"  Variance reduction: {(1 - smoothed_var / original_var) * 100:.1f}%")
    
    print("\nSmoothing methods comparison:")
    print("  - temporal: Simple weighted average, good for slow motion")
    print("  - bilateral: Appearance-aware, preserves edges, handles occlusions")
    print("  - gaussian: Gaussian-weighted window, smooth transitions")
    print("  - flow: Optical flow-based, best for camera motion")


def example_video_processing():
    print("\n" + "=" * 60)
    print("EXAMPLE: Video Saliency Detection")
    print("=" * 60)
    
    test_dir = Config.TEST_IMAGE_DIR
    output_dir = os.path.join(Config.OUTPUT_DIR, 'video_demo')
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\nCreating synthetic video for demo...")
    video_path = os.path.join(output_dir, 'demo_video.mp4')
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = 10
    width, height = 320, 240
    writer = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
    
    for i in range(30):
        frame = np.ones((height, width, 3), dtype=np.uint8) * 200
        
        obj_x = int(50 + (width - 100) * (i / 29))
        obj_y = int(height // 2 + 50 * np.sin(i * 0.3))
        
        cv2.circle(frame, (obj_x, obj_y), 30, (0, 0, 255), -1)
        cv2.rectangle(frame, (obj_x - 20, obj_y - 20), (obj_x + 20, obj_y + 20), (0, 255, 0), 2)
        
        writer.write(frame)
    
    writer.release()
    print(f"Demo video created: {video_path}")
    
    print("\nInitializing video saliency detector...")
    detector = VideoSaliencyDetector(
        model_name='basnet',
        use_tensorrt=False,
        use_dynamic_batch=True
    )
    
    print("\nSetting smoothing method to 'bilateral'...")
    detector.set_smoothing_method(
        method='bilateral',
        window_size=5,
        alpha=0.7,
        beta=0.5
    )
    
    print("\nProcessing video...")
    try:
        result = detector.process_video(
            video_path=video_path,
            output_dir=output_dir,
            start_frame=0,
            end_frame=30,
            stride=1,
            smooth=True,
            refine_method='guided',
            save_results=True,
            show_progress=True
        )
        
        print(f"\nProcessing complete!")
        print(f"  Total frames: {result.total_frames}")
        print(f"  FPS: {result.fps}")
        print(f"  Output video: {result.output_video_path}")
        
    except Exception as e:
        print(f"Full processing not available (PyTorch may be unavailable): {e}")
        print("\nRunning synthetic smoothing demo...")
        demo_synthetic_smoothing(output_dir)


def demo_synthetic_smoothing(output_dir: str):
    print("\n" + "-" * 40)
    print("Synthetic Frame Smoothing Demo")
    print("-" * 40)
    
    num_frames = 20
    frames = []
    saliency_maps = []
    
    print("\nGenerating synthetic data...")
    for i in range(num_frames):
        frame = np.ones((256, 256, 3), dtype=np.uint8) * 180
        
        obj_x = int(60 + 120 * (i / (num_frames - 1)))
        obj_y = int(128 + 40 * np.sin(i * 0.4))
        
        cv2.circle(frame, (obj_x, obj_y), 25, (255, 100, 100), -1)
        frames.append(frame)
        
        saliency = np.zeros((256, 256), dtype=np.float32)
        for y in range(256):
            for x in range(256):
                dist = np.sqrt((x - obj_x) ** 2 + (y - obj_y) ** 2)
                saliency[y, x] = np.exp(-dist ** 2 / (2 * 30 ** 2))
        saliency += np.random.normal(0, 0.03, saliency.shape).astype(np.float32)
        saliency = np.clip(saliency, 0, 1)
        saliency_maps.append(saliency)
    
    print("\nApplying different smoothing methods...")
    smoothed_results = {}
    
    for method in ['temporal', 'gaussian', 'bilateral']:
        smoother = FrameSmoother(method=method, window_size=5)
        smoothed = []
        for sal, frame in zip(saliency_maps, frames):
            smoothed.append(smoother.smooth(sal, frame))
        smoothed_results[method] = smoothed
    
    print("\nSaving visualization...")
    for i in tqdm(range(num_frames), desc="Saving frames"):
        frame = frames[i]
        
        sal_orig = saliency_maps[i]
        sal_orig_color = cv2.applyColorMap((sal_orig * 255).astype(np.uint8), cv2.COLORMAP_JET)
        sal_orig_color = cv2.cvtColor(sal_orig_color, cv2.COLOR_BGR2RGB)
        
        row = [frame, sal_orig_color]
        
        for method in ['temporal', 'gaussian', 'bilateral']:
            sal_smooth = smoothed_results[method][i]
            sal_smooth_color = cv2.applyColorMap((sal_smooth * 255).astype(np.uint8), cv2.COLORMAP_JET)
            sal_smooth_color = cv2.cvtColor(sal_smooth_color, cv2.COLOR_BGR2RGB)
            
            cv2.putText(sal_smooth_color, method, (10, 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            row.append(sal_smooth_color)
        
        combined = np.hstack(row)
        save_path = os.path.join(output_dir, f'frame_{i:03d}.png')
        save_image(combined, save_path)
    
    print("\nCreating output video...")
    output_video = os.path.join(output_dir, 'smoothing_comparison.mp4')
    h, w = combined.shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_video, fourcc, 10, (w, h))
    
    for i in range(num_frames):
        img_path = os.path.join(output_dir, f'frame_{i:03d}.png')
        img = cv2.imread(img_path)
        if img is not None:
            writer.write(img)
    
    writer.release()
    print(f"Output video: {output_video}")
    
    print("\nAnalyzing smoothing quality...")
    original_std = np.std([s.mean() for s in saliency_maps])
    print(f"  Original std dev: {original_std:.4f}")
    
    for method in ['temporal', 'gaussian', 'bilateral']:
        smoothed_std = np.std([s.mean() for s in smoothed_results[method]])
        reduction = (1 - smoothed_std / original_std) * 100
        print(f"  {method:12s} std dev: {smoothed_std:.4f} (reduction: {reduction:.1f}%)")


def example_clip_extraction():
    print("\n" + "=" * 60)
    print("EXAMPLE: Salient Clip Extraction")
    print("=" * 60)
    
    output_dir = os.path.join(Config.OUTPUT_DIR, 'clip_demo')
    os.makedirs(output_dir, exist_ok=True)
    
    num_frames = 100
    fps = 10
    
    print("\nGenerating synthetic video with varying saliency...")
    saliency_scores = np.zeros(num_frames)
    for i in range(num_frames):
        if 20 <= i < 45:
            saliency_scores[i] = 0.3 + 0.5 * np.sin((i - 20) * np.pi / 25)
        elif 60 <= i < 85:
            saliency_scores[i] = 0.2 + 0.6 * np.sin((i - 60) * np.pi / 25)
        else:
            saliency_scores[i] = 0.1 * np.random.random()
    
    frame_results = []
    for i in range(num_frames):
        sal = np.zeros((256, 256), dtype=np.float32) + saliency_scores[i]
        mask = (sal > 0.5).astype(np.float32)
        frame_results.append({
            'frame_idx': i,
            'saliency_map': sal,
            'binary_mask': mask,
            'smoothed_saliency': sal
        })
    
    detector = VideoSaliencyDetector()
    
    class MockVideoResult:
        def __init__(self):
            self.fps = fps
            self.frame_results = []
    
    video_result = MockVideoResult()
    
    from dataclasses import dataclass
    @dataclass
    class MockFrameResult:
        frame_idx: int
        smoothed_saliency: np.ndarray
        saliency_map: np.ndarray
    
    video_result.frame_results = [
        MockFrameResult(i, sal, sal) for i, sal in enumerate(saliency_scores)
    ]
    
    print("\nExtracting salient clips...")
    clips = detector.extract_salient_clips(
        video_result,
        threshold=0.3,
        min_duration=1.0
    )
    
    print(f"\nFound {len(clips)} salient clips:")
    for i, clip in enumerate(clips):
        print(f"\n  Clip #{i+1}:")
        print(f"    Frames: {clip['start_frame']} - {clip['end_frame']}")
        print(f"    Time:   {clip['start_time']:.1f}s - {clip['end_time']:.1f}s")
        print(f"    Duration: {clip['duration']:.1f}s")
        print(f"    Avg saliency: {clip['avg_saliency']:.3f}")
    
    plot_path = os.path.join(output_dir, 'saliency_timeline.png')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(range(num_frames), saliency_scores, 'b-', label='Saliency score')
    ax.axhline(0.3, color='r', linestyle='--', label='Threshold')
    
    for clip in clips:
        ax.axvspan(clip['start_frame'], clip['end_frame'],
                   alpha=0.3, color='green', label='Salient clip')
    
    ax.set_xlabel('Frame')
    ax.set_ylabel('Saliency Score')
    ax.set_title('Video Saliency Timeline')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(plot_path)
    plt.close()
    
    print(f"\nTimeline plot saved to: {plot_path}")


def example_sequence_smoothing():
    print("\n" + "=" * 60)
    print("EXAMPLE: Sequence Smoothing Function")
    print("=" * 60)
    
    print("\nGenerating synthetic saliency sequence...")
    num_frames = 15
    sequence = []
    for i in range(num_frames):
        sal = np.zeros((64, 64), dtype=np.float32)
        cx = 32 + int(15 * np.sin(i * 0.5))
        cy = 32 + int(10 * np.cos(i * 0.3))
        for y in range(64):
            for x in range(64):
                dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                sal[y, x] = np.exp(-dist ** 2 / (2 * 20 ** 2))
        sal += np.random.normal(0, 0.05, sal.shape).astype(np.float32)
        sal = np.clip(sal, 0, 1)
        sequence.append(sal)
    
    print("\nSmoothing with different methods...")
    smoothed_temporal = smooth_saliency_sequence(sequence, method='temporal', window_size=5)
    smoothed_gaussian = smooth_saliency_sequence(sequence, method='gaussian', window_size=5)
    
    print("\nQuantitative comparison:")
    original_diff = np.mean([np.abs(sequence[i] - sequence[i-1]).mean() 
                            for i in range(1, len(sequence))])
    temp_diff = np.mean([np.abs(smoothed_temporal[i] - smoothed_temporal[i-1]).mean() 
                        for i in range(1, len(smoothed_temporal))])
    gauss_diff = np.mean([np.abs(smoothed_gaussian[i] - smoothed_gaussian[i-1]).mean() 
                         for i in range(1, len(smoothed_gaussian))])
    
    print(f"  Original avg frame difference: {original_diff:.4f}")
    print(f"  Temporal smoothed: {temp_diff:.4f} (reduction: {(1 - temp_diff/original_diff)*100:.1f}%)")
    print(f"  Gaussian smoothed: {gauss_diff:.4f} (reduction: {(1 - gauss_diff/original_diff)*100:.1f}%)")


def main():
    print("\n" + "=" * 60)
    print("VIDEO SALIENCY DETECTION - COMPREHENSIVE DEMO")
    print("=" * 60)
    
    try:
        example_smoothing_methods()
        example_sequence_smoothing()
        example_video_processing()
        example_clip_extraction()
        
        print("\n" + "=" * 60)
        print("ALL EXAMPLES COMPLETE")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError during examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
