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

print(f'Pair ({i0}, {i1}): {len(common_ids)} matches')

E, mask, R_est, t_est = estimate_essential_matrix(pts0, pts1, K)

R0 = np.eye(3)
t0 = np.zeros(3)
R1 = R_est
t1 = t_est

# Trace check
R_rel_gt = pose0['R_w2c'] @ pose1['R_c2w']
trace_val = np.trace(R1.T @ R_rel_gt)
print(f'Trace: {trace_val:.4f}')
if trace_val < 1.0:
    print("Flipping rotation sign")
    R1 = R1.T
    t1 = -t1

# Coordinate system alignment (correct formula)
# X_gt = R_c2w_0 @ X_sfm + cam_pos_0
# R_i_new = R_i @ R_c2w_0^T, t_i_new = t_i - R_i @ R_c2w_0^T @ cam_pos_0
R_align_T = pose0["R_c2w"].T  # R_w2c_0
cam_pos0 = pose0['position']
R0 = R0 @ R_align_T
t0 = t0 - R0 @ cam_pos0
R1 = R1 @ R_align_T
t1 = t1 - R1 @ cam_pos0

# Scale calibration
gt_pos0 = pose0['position']
gt_pos1 = pose1['position']
gt_baseline = np.linalg.norm(gt_pos1 - gt_pos0)
est_baseline = np.linalg.norm(t1)
scale_factor = gt_baseline / est_baseline
t1 = t1 * scale_factor
print(f'Scale factor: {scale_factor:.4f}')

# Check camera positions
cam_pos0_est = -R0.T @ t0
cam_pos1_est = -R1.T @ t1
print(f'Cam0 pos est: {cam_pos0_est}, gt: {gt_pos0}')
print(f'Cam1 pos est: {cam_pos1_est}, gt: {gt_pos1}')
print(f'Cam0 pos error: {np.linalg.norm(cam_pos0_est - gt_pos0):.6f}')
print(f'Cam1 pos error: {np.linalg.norm(cam_pos1_est - gt_pos1):.6f}')

# Check rotation errors
R0_diff = R0.T @ pose0['R_w2c']
R1_diff = R1.T @ pose1['R_w2c']
cos0 = np.clip((np.trace(R0_diff) - 1) / 2, -1, 1)
cos1 = np.clip((np.trace(R1_diff) - 1) / 2, -1, 1)
print(f'Cam0 rot error: {np.arccos(cos0)*180/np.pi:.4f} deg')
print(f'Cam1 rot error: {np.arccos(cos1)*180/np.pi:.4f} deg')

# Triangulate
pts_3d = triangulate_points(pts0[mask], pts1[mask], K, R0, t0, R1, t1)

# Check depth
proj0 = (R0 @ pts_3d.T).T + t0
proj1 = (R1 @ pts_3d.T).T + t1
valid = (proj0[:, 2] > 0) & (proj1[:, 2] > 0)
print(f'Valid points: {np.sum(valid)} / {len(valid)}')

if np.sum(valid) > 0:
    pts_valid = pts_3d[valid]
    print(f'Range X: [{pts_valid[:,0].min():.2f}, {pts_valid[:,0].max():.2f}]')
    print(f'Range Y: [{pts_valid[:,1].min():.2f}, {pts_valid[:,1].max():.2f}]')
    print(f'Range Z: [{pts_valid[:,2].min():.2f}, {pts_valid[:,2].max():.2f}]')
    print(f'GT Range X: [{gt_pts[:,0].min():.2f}, {gt_pts[:,0].max():.2f}]')
    print(f'GT Range Y: [{gt_pts[:,1].min():.2f}, {gt_pts[:,1].max():.2f}]')
    print(f'GT Range Z: [{gt_pts[:,2].min():.2f}, {gt_pts[:,2].max():.2f}]')
