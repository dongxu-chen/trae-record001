import numpy as np
from multi_view_reconstruction import (
    generate_synthetic_scene, generate_camera_poses,
    evaluate_reconstruction, ReconstructionMetrics
)

# Generate test data
gt_points, gt_colors = generate_synthetic_scene()
gt_poses = generate_camera_poses(12)

# Create dummy estimated poses (simulating SfM output)
estimated_poses = []
for i in range(12):
    gt_pose = gt_poses[i]
    estimated_poses.append({
        "view_idx": i,
        "R_w2c": gt_pose["R_w2c"],
        "t_w2c": gt_pose["t_w2c"].ravel(),
        "R_c2w": gt_pose["R_c2w"],
        "position": gt_pose["position"],
        "K": gt_pose["K"],
    })

# Evaluate
metrics = evaluate_reconstruction(
    sparse_points=gt_points,
    dense_points=gt_points,
    sparse_colors=gt_colors,
    dense_colors=gt_colors,
    gt_points=gt_points,
    gt_colors=gt_colors,
    estimated_poses=estimated_poses,
    gt_poses=gt_poses,
    reprojection_error=0.0
)

print(f"\nOverall score: {metrics.overall_score}")
