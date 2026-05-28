import numpy as np
import cv2
from multi_view_reconstruction import (
    generate_synthetic_scene, generate_camera_poses,
    extract_features, match_features, create_feature_detector,
    estimate_essential_matrix, triangulate_points, Config
)

gt_pts, gt_col = generate_synthetic_scene()
gt_poses = generate_camera_poses(12)
K = gt_poses[0]['K']

# Load images
images = []
for i in range(12):
    img = cv2.imread(f'output/images/view_{i:04d}.png')
    if img is not None:
        images.append(img)

# Extract features
detector = create_feature_detector('SIFT', 2000)
features = extract_features(images, detector)
matches_dict = match_features(features, 0.75, 'SIFT')

# Check initial pair (0, 10)
i0, i1 = 0, 10
kp0, _ = features[i0]
kp1, _ = features[i1]
matches = matches_dict[(i0, i1)]
pts0 = np.float32([kp0[m.queryIdx].pt for m in matches])
pts1 = np.float32([kp1[m.trainIdx].pt for m in matches])

E, inlier_mask, R_est, t_est = estimate_essential_matrix(pts0, pts1, K)

# Ground truth relative rotation
gt_pose0 = gt_poses[i0]
gt_pose1 = gt_poses[i1]
R_rel_gt = gt_pose0['R_w2c'] @ gt_pose1['R_c2w']

# Compare
print('Estimated R:')
print(R_est)
print('\nGround truth relative R:')
print(R_rel_gt)
print('\nR_rel_gt @ R_est^T (should be I if same):')
print(R_rel_gt @ R_est.T)

# Compute angle
R_diff = R_est.T @ R_rel_gt
cos_angle = (np.trace(R_diff) - 1) / 2
cos_angle = np.clip(cos_angle, -1, 1)
angle = np.arccos(cos_angle) * 180 / np.pi
print(f'\nAngle between R_est and R_rel_gt: {angle:.2f} deg')

# Check if R_est with different sign matches
print(f'\nAngle between -R_est and R_rel_gt: {np.arccos(np.clip((np.trace((-R_est).T @ R_rel_gt) - 1) / 2, -1, 1)) * 180 / np.pi:.2f} deg')

# Check t direction
t_est_norm = t_est / (np.linalg.norm(t_est) + 1e-10)
t_gt = gt_pose0['t_w2c'].ravel() - gt_pose1['t_w2c'].ravel()
t_gt_norm = t_gt / (np.linalg.norm(t_gt) + 1e-10)
print(f'\nt_est_norm: {t_est_norm}')
print(f't_gt_norm (difference in world): {t_gt_norm}')

# t in camera 0 coordinates
t_rel_gt = gt_pose0['R_w2c'] @ (gt_pose1['t_c2w'] - gt_pose0['t_c2w'])
t_rel_gt_norm = t_rel_gt / (np.linalg.norm(t_rel_gt) + 1e-10)
print(f't_rel_gt_norm (in cam0 coords): {t_rel_gt_norm}')
