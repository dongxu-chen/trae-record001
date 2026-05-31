import os
import json
import numpy as np
import cv2
import torch


def load_cam(path, max_dim=None):
    with open(path, "r") as f:
        lines = f.readlines()
    lines = [l.strip() for l in lines if l.strip()]

    extrinsic = np.array(
        [list(map(float, lines[i].split())) for i in range(4)]
    )
    intrinsic = np.array(
        [list(map(float, lines[i].split())) for i in range(4, 7)]
    )

    depth_min = float(lines[7].split()[0]) if len(lines) > 7 else 0.5
    depth_max = float(lines[7].split()[1]) if len(lines) > 7 else 10.0

    if max_dim is not None:
        h, w = int(intrinsic[1, 2] * 2), int(intrinsic[0, 2] * 2)
        scale = max_dim / max(h, w)
        if scale < 1.0:
            intrinsic[:2, :] *= scale

    proj = intrinsic @ extrinsic
    return intrinsic, extrinsic, proj, depth_min, depth_max


def load_cam_from_dict(cam_dict, max_dim=None):
    intrinsic = np.array(cam_dict["intrinsic"])
    extrinsic = np.array(cam_dict["extrinsic"])
    depth_min = cam_dict.get("depth_min", 0.5)
    depth_max = cam_dict.get("depth_max", 10.0)

    if max_dim is not None:
        h, w = int(intrinsic[1, 2] * 2), int(intrinsic[0, 2] * 2)
        scale = max_dim / max(h, w)
        if scale < 1.0:
            intrinsic[:2, :] *= scale

    proj = intrinsic @ extrinsic
    return intrinsic, extrinsic, proj, depth_min, depth_max


def load_image(path, max_dim=None):
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Image not found: {path}")
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    if max_dim is not None:
        h, w = img.shape[:2]
        scale = max_dim / max(h, w)
        if scale < 1.0:
            img = cv2.resize(img, (int(w * scale), int(h * scale)))

    img = img.astype(np.float32) / 255.0
    img = img.transpose(2, 0, 1)
    return img


def generate_depth_values(depth_min, depth_max, num_depth, interval_scale=1.06):
    depth_values = np.arange(0, num_depth, dtype=np.float32)
    depth_values = depth_min + depth_values * interval_scale
    depth_values = np.clip(depth_values, depth_min, depth_max)
    return depth_values


def to_tensor(arr):
    return torch.from_numpy(arr).float()


def save_depth_as_ply(depth, intrinsic, extrinsic, output_path, image=None):
    h, w = depth.shape
    fx = intrinsic[0, 0]
    fy = intrinsic[1, 1]
    cx = intrinsic[0, 2]
    cy = intrinsic[1, 2]

    R = extrinsic[:3, :3]
    t = extrinsic[:3, 3]

    points = []
    colors = []

    for y_idx in range(h):
        for x_idx in range(w):
            d = depth[y_idx, x_idx]
            if d <= 0:
                continue
            x_cam = (x_idx - cx) * d / fx
            y_cam = (y_idx - cy) * d / fy
            z_cam = d
            pt_cam = np.array([x_cam, y_cam, z_cam])
            pt_world = R.T @ (pt_cam - t)
            points.append(pt_world)

            if image is not None:
                colors.append(image[y_idx, x_idx] / 255.0)

    points = np.array(points)
    if len(colors) > 0:
        colors = np.array(colors)

    header = f"ply\nformat ascii 1.0\nelement vertex {len(points)}\n"
    header += "property float x\nproperty float y\nproperty float z\n"
    if len(colors) > 0:
        header += "property uchar red\nproperty uchar green\nproperty uchar blue\n"
    header += "end_header\n"

    with open(output_path, "w") as f:
        f.write(header)
        for i in range(len(points)):
            line = f"{points[i, 0]:.6f} {points[i, 1]:.6f} {points[i, 2]:.6f}"
            if len(colors) > 0:
                line += f" {int(colors[i, 0]*255)} {int(colors[i, 1]*255)} {int(colors[i, 2]*255)}"
            f.write(line + "\n")

    return len(points)
