import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config, VideoConfig
from depth_estimation import MidasModel, DepthPostProcessor, VideoDepthEstimator


def main():
    config = Config()
    config.model.model_type = "MiDaS_small"
    config.model.device = "cuda"
    
    video_config = VideoConfig()
    video_config.source = "0"
    video_config.target_size = (640, 480)
    video_config.show_fps = True
    video_config.display_depth = True
    video_config.colormap = 2
    video_config.save_video = False
    
    print("Initializing model...")
    model = MidasModel(config.model)
    post_processor = DepthPostProcessor(config.post_processing)
    
    print("Starting webcam...")
    estimator = VideoDepthEstimator(model, post_processor, video_config)
    
    def frame_callback(frame, depth_map):
        pass
    
    try:
        estimator.run(callback=frame_callback)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        stats = estimator.get_stats()
        print(f"\n=== Session Stats ===")
        print(f"Frames processed: {stats['frame_count']}")
        print(f"Average FPS: {stats['avg_fps']:.2f}")
    
    print("\nDone!")


if __name__ == "__main__":
    main()
