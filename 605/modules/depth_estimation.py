import os
import logging
import numpy as np
import cv2
import torch
from models.mvsnet import MVSNet
from utils.helpers import load_image, load_cam_from_dict, generate_depth_values, to_tensor
from config import MVSNET_CONFIG, CUDA_CONFIG

logger = logging.getLogger(__name__)


class DepthEstimator:
    def __init__(self, config=None):
        self.config = config or MVSNET_CONFIG
        self.device = self._get_device()
        self.model = self._build_model()
        self.num_depth = self.config["num_depth"]
        self.interval_scale = self.config["interval_scale"]

    def _get_device(self):
        if torch.cuda.is_available():
            gpu_id = CUDA_CONFIG.get("gpu_id", 0)
            device = torch.device(f"cuda:{gpu_id}")
            logger.info(f"Using CUDA device: {gpu_id}")
        else:
            device = torch.device("cpu")
            logger.warning("CUDA not available, using CPU")
        return device

    def _build_model(self):
        model = MVSNet(
            feat_channels=self.config["feat_channels"],
            cost_volume_channels=self.config.get("cost_volume_channels", 8),
            refine=True,
        )
        model = model.to(self.device)
        model.eval()
        return model

    def load_pretrained(self, checkpoint_path):
        if not os.path.exists(checkpoint_path):
            logger.warning(f"Checkpoint not found: {checkpoint_path}")
            return False
        state_dict = torch.load(checkpoint_path, map_location=self.device)
        if "model" in state_dict:
            state_dict = state_dict["model"]
        self.model.load_state_dict(state_dict, strict=False)
        logger.info(f"Loaded checkpoint from {checkpoint_path}")
        return True

    @torch.no_grad()
    def estimate_depth(
        self,
        ref_img_path,
        src_img_paths,
        ref_cam_dict,
        src_cam_dicts,
        depth_min=None,
        depth_max=None,
    ):
        ref_img = load_image(ref_img_path, max_dim=max(self.config["img_width"], self.config["img_height"]))
        src_imgs = [
            load_image(p, max_dim=max(self.config["img_width"], self.config["img_height"]))
            for p in src_img_paths
        ]

        ref_intrinsic, ref_extrinsic, ref_proj, d_min, d_max = load_cam_from_dict(ref_cam_dict)
        src_projs = []
        for cam_dict in src_cam_dicts:
            _, _, src_proj, _, _ = load_cam_from_dict(cam_dict)
            src_projs.append(src_proj)

        if depth_min is None:
            depth_min = d_min
        if depth_max is None:
            depth_max = d_max

        depth_values = generate_depth_values(
            depth_min, depth_max, self.num_depth, self.interval_scale
        )

        ref_img_tensor = to_tensor(ref_img).unsqueeze(0).to(self.device)
        src_img_tensors = [to_tensor(img).unsqueeze(0).to(self.device) for img in src_imgs]
        ref_proj_tensor = to_tensor(ref_proj).unsqueeze(0).to(self.device)
        src_proj_tensors = [to_tensor(sp).unsqueeze(0).to(self.device) for sp in src_projs]
        depth_values_tensor = to_tensor(depth_values).unsqueeze(0).to(self.device)

        depth_est, prob_volume = self.model(
            ref_img_tensor, src_img_tensors, ref_proj_tensor, src_proj_tensors, depth_values_tensor
        )

        depth_map = depth_est.squeeze().cpu().numpy()
        prob_map = prob_volume.squeeze().cpu().numpy()

        return depth_map, prob_map, depth_values

    @torch.no_grad()
    def estimate_depth_batch(
        self,
        images,
        cam_dicts,
        depth_min=None,
        depth_max=None,
        num_src=3,
    ):
        num_views = len(images)
        all_depths = {}
        all_probs = {}

        for ref_idx in range(num_views):
            src_indices = self._select_src_views(ref_idx, cam_dicts, num_src)

            ref_img = load_image(
                images[ref_idx],
                max_dim=max(self.config["img_width"], self.config["img_height"]),
            )
            src_imgs = [
                load_image(images[i], max_dim=max(self.config["img_width"], self.config["img_height"]))
                for i in src_indices
            ]

            ref_intrinsic, ref_extrinsic, ref_proj, d_min, d_max = load_cam_from_dict(cam_dicts[ref_idx])
            src_projs = []
            for i in src_indices:
                _, _, sp, _, _ = load_cam_from_dict(cam_dicts[i])
                src_projs.append(sp)

            if depth_min is None:
                depth_min = d_min
            if depth_max is None:
                depth_max = d_max

            depth_values = generate_depth_values(
                depth_min, depth_max, self.num_depth, self.interval_scale
            )

            ref_img_tensor = to_tensor(ref_img).unsqueeze(0).to(self.device)
            src_img_tensors = [to_tensor(img).unsqueeze(0).to(self.device) for img in src_imgs]
            ref_proj_tensor = to_tensor(ref_proj).unsqueeze(0).to(self.device)
            src_proj_tensors = [to_tensor(sp).unsqueeze(0).to(self.device) for sp in src_projs]
            depth_values_tensor = to_tensor(depth_values).unsqueeze(0).to(self.device)

            depth_est, prob_volume = self.model(
                ref_img_tensor, src_img_tensors, ref_proj_tensor, src_proj_tensors, depth_values_tensor
            )

            all_depths[ref_idx] = depth_est.squeeze().cpu().numpy()
            all_probs[ref_idx] = prob_volume.squeeze().cpu().numpy()

            logger.info(f"Estimated depth for view {ref_idx}")

        return all_depths, all_probs, depth_values

    def _select_src_views(self, ref_idx, cam_dicts, num_src):
        ref_extrinsic = np.array(cam_dicts[ref_idx]["extrinsic"])
        ref_R = ref_extrinsic[:3, :3]
        ref_t = ref_extrinsic[:3, 3]

        scores = []
        for i, cam in enumerate(cam_dicts):
            if i == ref_idx:
                scores.append(-1.0)
                continue
            src_extrinsic = np.array(cam["extrinsic"])
            src_R = src_extrinsic[:3, :3]
            src_t = src_extrinsic[:3, 3]

            cos_angle = np.clip((np.trace(ref_R.T @ src_R) - 1) / 2, -1, 1)
            angle = np.arccos(cos_angle)
            dist = np.linalg.norm(ref_t - src_t)
            score = angle + dist * 0.01
            scores.append(score)

        src_indices = sorted(
            range(len(scores)), key=lambda i: scores[i] if scores[i] >= 0 else float("inf")
        )[:num_src]
        return src_indices

    @staticmethod
    def filter_depth(depth_map, prob_map, prob_threshold=0.8):
        mask = prob_map.max(axis=0) > prob_threshold
        filtered_depth = depth_map.copy()
        filtered_depth[~mask] = 0
        return filtered_depth, mask

    @staticmethod
    def depth_to_point_cloud(depth_map, intrinsic, extrinsic, image=None):
        h, w = depth_map.shape
        fx = intrinsic[0, 0]
        fy = intrinsic[1, 1]
        cx = intrinsic[0, 2]
        cy = intrinsic[1, 2]

        R = extrinsic[:3, :3]
        t = extrinsic[:3, 3]

        mask = depth_map > 0
        ys, xs = np.where(mask)
        ds = depth_map[mask]

        x_cam = (xs - cx) * ds / fx
        y_cam = (ys - cy) * ds / fy
        z_cam = ds

        pts_cam = np.stack([x_cam, y_cam, z_cam], axis=-1)
        pts_world = (R.T @ (pts_cam - t).T).T

        colors = None
        if image is not None:
            if image.max() > 1.0:
                image = image.astype(np.float32) / 255.0
            colors = image[ys, xs]

        return pts_world, colors
