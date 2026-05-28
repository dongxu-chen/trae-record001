import numpy as np
from multi_view_reconstruction import (
    generate_synthetic_scene, generate_camera_poses,
    project_points, Config, estimate_essential_matrix
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

# Trace check
R_rel_gt = pose0['R_w2c'] @ pose1['R_c2w']
trace_val = np.trace(R1.T @ R_rel_gt)
if trace_val < 1.0:
    R1 = R1.T
    t1 = -t1

print(f"R1 after trace check:\n{R1}")
print(f"R_rel_gt:\n{R_rel_gt}")
print(f"R1 == R_rel_gt: {np.allclose(R1, R_rel_gt)}")

# Coordinate system alignment
R_align_T = pose0["R_c2w"].T  # R_w2c_0
cam_pos0 = pose0['position']
R0_new = R0 @ R_align_T
t0_new = t0 - R0_new @ cam_pos0
R1_new = R1 @ R_align_T
t1_new = t1 - R1_new @ cam_pos0

print(f"\nR0_new:\n{R0_new}")
print(f"R0_gt (R_w2c_0):\n{pose0['R_w2c']}")
print(f"R0_new == R_w2c_0: {np.allclose(R0_new, pose0['R_w2c'])}")

print(f"\nR1_new:\n{R1_new}")
print(f"R1_gt (R_w2c_1):\n{pose1['R_w2c']}")

# Check relative rotation
R_rel_new = R0_new @ R1_new.T
print(f"\nR_rel_new:\n{R_rel_new}")
print(f"R_rel_gt^T:\n{R_rel_gt.T}")
print(f"R_rel_new == R_rel_gt^T: {np.allclose(R_rel_new, R_rel_gt.T)}")

# Check camera 1 position
cam_pos1_est = -R1_new.T @ t1_new
print(f"\nCam1 pos est: {cam_pos1_est}")
print(f"Cam1 pos gt: {pose1['position']}")
