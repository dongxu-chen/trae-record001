import numpy as np
import cv2
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

# Map: point_id -> pixel_coord for each view
idx0 = np.where(mask0)[0]
idx1 = np.where(mask1)[0]
map0 = {pt_id: pixels0[j] for j, pt_id in enumerate(idx0)}
map1 = {pt_id: pixels1[j] for j, pt_id in enumerate(idx1)}

# Find common points
common_ids = set(idx0) & set(idx1)
pts0 = np.float32([map0[pid] for pid in common_ids])
pts1 = np.float32([map1[pid] for pid in common_ids])

print(f'Pair ({i0}, {i1}): {len(common_ids)} matches')

R_rel_gt = pose0['R_w2c'] @ pose1['R_c2w']
print(f'Ground truth relative R:\n{R_rel_gt}')

E, mask, R_est, t_est = estimate_essential_matrix(pts0, pts1, K)
print(f'\nEstimated R:\n{R_est}')
print(f'Estimated t: {t_est}')

R_diff = R_est.T @ R_rel_gt
cos_angle = (np.trace(R_diff) - 1) / 2
cos_angle = np.clip(cos_angle, -1, 1)
angle = np.arccos(cos_angle) * 180 / np.pi
print(f'Angle between R_est and R_rel_gt: {angle:.2f} deg')

K_inv = np.linalg.inv(K)
pts0_norm = (K_inv @ np.hstack([pts0, np.ones((len(pts0), 1))]).T).T[:, :2]
pts1_norm = (K_inv @ np.hstack([pts1, np.ones((len(pts1), 1))]).T).T[:, :2]

E2, mask2 = cv2.findEssentialMat(pts0_norm, pts1_norm, method=cv2.RANSAC, prob=0.999, threshold=1.0)
mask2 = mask2.ravel().astype(bool)

U, S, Vt = np.linalg.svd(E2)
W = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]])

print('\nChecking all 4 solutions:')
for idx, (sign_R, sign_t) in enumerate([(1, 1), (1, -1), (-1, 1), (-1, -1)]):
    if sign_R == 1:
        R_sol = U @ W @ Vt
    else:
        R_sol = U @ W.T @ Vt
    t_sol = sign_t * U[:, 2]

    P1 = K @ np.hstack([np.eye(3), np.zeros((3, 1))])
    P2 = K @ np.hstack([R_sol, t_sol.reshape(3, 1)])
    pts_h = cv2.triangulatePoints(P1, P2, pts0_norm[mask2].T, pts1_norm[mask2].T)
    pts_3d = (pts_h[:3] / pts_h[3]).T

    proj1 = pts_3d[:, 2]
    proj2 = (R_sol @ pts_3d.T).T[:, 2] + t_sol[2]

    valid = (proj1 > 0) & (proj2 > 0)
    n_valid = np.sum(valid)

    R_diff_sol = R_sol.T @ R_rel_gt
    cos_angle_sol = (np.trace(R_diff_sol) - 1) / 2
    cos_angle_sol = np.clip(cos_angle_sol, -1, 1)
    angle_sol = np.arccos(cos_angle_sol) * 180 / np.pi

    r_sign = 'W' if sign_R == 1 else 'W^T'
    print(f'  Solution {idx}: R_sign={r_sign}, t_sign={sign_t}, valid={n_valid}, angle={angle_sol:.2f} deg')
