import numpy as np
import cv2
from multi_view_reconstruction import (
    generate_synthetic_scene, generate_camera_poses,
    project_points, Config, estimate_essential_matrix,
    triangulate_points
)

gt_pts, gt_col = generate_synthetic_scene()
gt_poses = generate_camera_poses(12)
K = gt_poses[0]['K']

i0, i1 = 0, 10
pose0 = gt_poses[i0]
pose1 = gt_poses[i1]

pixels0, mask0 = project_points(gt_pts, pose0['K'], pose0['R_w2c'], pose0['t_w2c'],
                                (Config.IMAGE_WIDTH, Config.IMAGE_HEIGHT))
pixels1, mask1 = project_points(gt_pts, pose1['K'], pose1['R_w2c'], pose1['t_w2c'],
                                (Config.IMAGE_WIDTH, Config.IMAGE_HEIGHT))

idx0 = np.where(mask0)[0]
idx1 = np.where(mask1)[0]
map0 = {pt_id: pixels0[j] for j, pt_id in enumerate(idx0)}
map1 = {pt_id: pixels1[j] for j, pt_id in enumerate(idx1)}

common_ids = set(idx0) & set(idx1)
pts0 = np.float32([map0[pid] for pid in common_ids])
pts1 = np.float32([map1[pid] for pid in common_ids])

E, mask, R_est, t_est = estimate_essential_matrix(pts0, pts1, K)

R0 = np.eye(3)
t0 = np.zeros(3)
R1 = R_est
t1 = t_est

print("=== Before trace check ===")
print(f"R_est (from recoverPose):\n{R1}")
R_rel_gt = pose0['R_w2c'] @ pose1['R_c2w']
print(f"R_rel_gt:\n{R_rel_gt}")
trace_val = np.trace(R1.T @ R_rel_gt)
print(f"Trace: {trace_val:.4f}")

if trace_val < 1.0:
    print("Flipping R1")
    R1 = R1.T
    t1 = -t1

print("\n=== After trace check ===")
print(f"R1 after flip:\n{R1}")

# Coordinate system alignment
R_align_T = pose0["R_c2w"].T  # R_w2c_0
cam_pos0 = pose0['position']
print(f"\nR_w2c_0:\n{R_align_T}")
print(f"cam_pos0: {cam_pos0}")

R0 = R0 @ R_align_T
t0 = t0 - R0 @ cam_pos0
R1 = R1 @ R_align_T
t1 = t1 - R1 @ cam_pos0

print("\n=== After coordinate system alignment ===")
print(f"R0_new:\n{R0}")
print(f"R0_gt (R_w2c_0):\n{pose0['R_w2c']}")
print(f"R1_new:\n{R1}")
print(f"R1_gt (R_w2c_1):\n{pose1['R_w2c']}")

# Check rotation errors
R0_diff = R0.T @ pose0['R_w2c']
R1_diff = R1.T @ pose1['R_w2c']
cos0 = np.clip((np.trace(R0_diff) - 1) / 2, -1, 1)
cos1 = np.clip((np.trace(R1_diff) - 1) / 2, -1, 1)
print(f"\nCam0 rot error: {np.arccos(cos0)*180/np.pi:.4f} deg")
print(f"Cam1 rot error: {np.arccos(cos1)*180/np.pi:.4f} deg")

# Verify: R1_new should equal R_w2c_1
# R1 = R_rel_gt after trace check
# R1_new = R_rel_gt @ R_w2c_0
# R_rel_gt = R_w2c_0 @ R_c2w_1
# R1_new = R_w2c_0 @ R_c2w_1 @ R_w2c_0
# R_w2c_1 = R_c2w_1^T
print(f"\nR_w2c_0 @ R_c2w_1 @ R_w2c_0:\n{R_align_T @ pose1['R_c2w'] @ R_align_T}")
print(f"R_w2c_1:\n{pose1['R_w2c']}")
print(f"Equal: {np.allclose(R_align_T @ pose1['R_c2w'] @ R_align_T, pose1['R_w2c'])}")
