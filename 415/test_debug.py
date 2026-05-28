import numpy as np
import cv2
from multi_view_reconstruction import generate_synthetic_scene, generate_camera_poses, project_points

gt_pts, gt_col = generate_synthetic_scene()
gt_poses = generate_camera_poses(12)
K = gt_poses[0]['K']

pose = gt_poses[0]
print('Camera 0:')
print(f'  R_w2c:\n{pose["R_w2c"]}')
print(f'  t_w2c: {pose["t_w2c"].ravel()}')

test_pt = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
pts_cam = (pose['R_w2c'] @ test_pt.T).T + pose['t_w2c'].ravel()
print(f'  Test points in camera coords:')
print(f'  {pts_cam}')

valid_idx, pixels_2d = project_points(gt_pts, K, pose['R_w2c'], pose['t_w2c'].ravel(), 480, 640)
print(f'  Valid points: {len(valid_idx)}')
if len(valid_idx) > 0:
    print(f'  First pixel: {pixels_2d[0]}')
    print(f'  First color: {gt_col[valid_idx[0]]}')
    print(f'  Color type: {type(gt_col[valid_idx[0]])}')
    print(f'  Color * 255: {gt_col[valid_idx[0]] * 255}')
    print(f'  astype int: {(gt_col[valid_idx[0]] * 255).astype(int)}')
