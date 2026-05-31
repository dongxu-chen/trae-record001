import os
import logging
import numpy as np
import cv2
import open3d as o3d

logger = logging.getLogger(__name__)


class ProjectiveTexturer:
    def __init__(
        self,
        texture_resolution=4096,
        padding_pixels=4,
        visibility_thresh=0.0,
        blending_mode="median",
    ):
        self.texture_resolution = texture_resolution
        self.padding_pixels = padding_pixels
        self.visibility_thresh = visibility_thresh
        self.blending_mode = blending_mode

    def texture_mesh(
        self,
        mesh,
        images,
        cam_dicts,
        output_dir=None,
    ):
        vertices = np.asarray(mesh.vertices)
        triangles = np.asarray(mesh.triangles)
        vertex_normals = np.asarray(mesh.vertex_normals) if mesh.has_vertex_normals() else None

        if len(triangles) == 0:
            logger.warning("Mesh has no triangles")
            return mesh

        logger.info(
            f"Texturing mesh: {len(vertices)} vertices, {len(triangles)} triangles, "
            f"{len(images)} images"
        )

        best_views = self._assign_best_views(
            vertices, vertex_normals, images, cam_dicts
        )

        uv_coords = np.zeros((len(vertices), 2), dtype=np.float64)
        vertex_colors = np.zeros((len(vertices), 3), dtype=np.float64)
        vertex_valid = np.zeros(len(vertices), dtype=bool)

        for view_idx in range(len(images)):
            img = images[view_idx]
            cam = cam_dicts[view_idx]
            intrinsic = np.array(cam["intrinsic"])
            extrinsic = np.array(cam["extrinsic"])

            R = extrinsic[:3, :3]
            t = extrinsic[:3, 3]

            pts_cam = (R @ vertices.T).T + t

            behind = pts_cam[:, 2] <= 0
            pts_cam[behind, 2] = 1e-6

            fx, fy = intrinsic[0, 0], intrinsic[1, 1]
            cx, cy = intrinsic[0, 2], intrinsic[1, 2]

            px = pts_cam[:, 0] * fx / pts_cam[:, 2] + cx
            py = pts_cam[:, 1] * fy / pts_cam[:, 2] + cy

            h, w = img.shape[:2]
            in_image = (px >= 0) & (px < w) & (py >= 0) & (py < h) & ~behind

            if vertex_normals is not None:
                view_dir = -pts_cam
                view_dir = view_dir / (np.linalg.norm(view_dir, axis=1, keepdims=True) + 1e-8)
                facing = np.sum(vertex_normals * view_dir, axis=1) > self.visibility_thresh
                in_image = in_image & facing

            view_mask = (best_views == view_idx) & in_image

            px_int = np.clip(np.round(px).astype(np.int32), 0, w - 1)
            py_int = np.clip(np.round(py).astype(np.int32), 0, h - 1)

            colors = img[py_int, px_int].astype(np.float64) / 255.0

            uv_coords[view_mask, 0] = px[view_mask] / w
            uv_coords[view_mask, 1] = py[view_mask] / h

            vertex_colors[view_mask] = colors[view_mask]
            vertex_valid[view_mask] = True

            logger.info(
                f"View {view_idx}: projected {np.sum(view_mask)} vertices"
            )

        mesh_textured = o3d.geometry.TriangleMesh(mesh)
        if np.any(vertex_valid):
            vertex_colors[~vertex_valid] = 0.5
            mesh_textured.vertex_colors = o3d.utility.Vector3dVector(vertex_colors)

        logger.info(f"Textured {np.sum(vertex_valid)}/{len(vertices)} vertices")
        return mesh_textured

    def _assign_best_views(self, vertices, vertex_normals, images, cam_dicts):
        num_vertices = len(vertices)
        num_views = len(images)
        best_views = np.zeros(num_vertices, dtype=np.int32)
        best_scores = np.full(num_vertices, -np.inf)

        for view_idx in range(num_views):
            cam = cam_dicts[view_idx]
            intrinsic = np.array(cam["intrinsic"])
            extrinsic = np.array(cam["extrinsic"])

            R = extrinsic[:3, :3]
            t = extrinsic[:3, 3]

            pts_cam = (R @ vertices.T).T + t

            fx, fy = intrinsic[0, 0], intrinsic[1, 1]
            cx, cy = intrinsic[0, 2], intrinsic[1, 2]

            px = pts_cam[:, 0] * fx / pts_cam[:, 2] + cx
            py = pts_cam[:, 1] * fy / pts_cam[:, 2] + cy

            h, w = images[view_idx].shape[:2]
            in_image = (px >= 0) & (px < w) & (py >= 0) & (py < h) & (pts_cam[:, 2] > 0)

            facing_score = np.ones(num_vertices)
            if vertex_normals is not None:
                view_dir = -pts_cam
                view_dir = view_dir / (np.linalg.norm(view_dir, axis=1, keepdims=True) + 1e-8)
                facing_score = np.sum(vertex_normals * view_dir, axis=1)

            resolution_score = 1.0 / (pts_cam[:, 2] + 1e-6)

            center_dist = np.sqrt(
                (px - w / 2) ** 2 + (py - h / 2) ** 2
            ) / (max(w, h) / 2)
            center_score = 1.0 / (1.0 + center_dist)

            score = facing_score * resolution_score * center_score * in_image

            better = score > best_scores
            best_views[better] = view_idx
            best_scores[better] = score[better]

        return best_views


class TextureAtlasGenerator:
    def __init__(
        self,
        atlas_resolution=4096,
        chart_padding=4,
        gaussian_sigma=1.0,
    ):
        self.atlas_resolution = atlas_resolution
        self.chart_padding = chart_padding
        self.gaussian_sigma = gaussian_sigma

    def generate_texture_atlas(
        self,
        mesh,
        images,
        cam_dicts,
        output_dir=None,
    ):
        vertices = np.asarray(mesh.vertices)
        triangles = np.asarray(mesh.triangles)

        if len(triangles) == 0:
            logger.warning("Mesh has no triangles for atlas generation")
            return mesh, None, None

        logger.info("Generating UV coordinates via xatlas-style parametrization")

        uv_coords = self._generate_uv_coords(vertices, triangles)

        texture_atlas = np.ones(
            (self.atlas_resolution, self.atlas_resolution, 3),
            dtype=np.uint8,
        ) * 255

        texture_atlas, uv_coords = self._rasterize_texture(
            texture_atlas, uv_coords, vertices, triangles, images, cam_dicts
        )

        mesh_textured = o3d.geometry.TriangleMesh(mesh)
        mesh_textured.vertex_colors = o3d.utility.Vector3dVector(
            self._sample_atlas_colors(uv_coords, texture_atlas)
        )

        atlas_path = None
        if output_dir is not None:
            os.makedirs(output_dir, exist_ok=True)
            atlas_path = os.path.join(output_dir, "texture_atlas.png")
            cv2.imwrite(atlas_path, cv2.cvtColor(texture_atlas, cv2.COLOR_RGB2BGR))
            logger.info(f"Saved texture atlas: {atlas_path}")

        return mesh_textured, uv_coords, atlas_path

    def _generate_uv_coords(self, vertices, triangles):
        num_vertices = len(vertices)
        bbox_min = vertices.min(axis=0)
        bbox_max = vertices.max(axis=0)
        bbox_size = bbox_max - bbox_min
        max_extent = max(bbox_size)

        if max_extent < 1e-8:
            return np.zeros((num_vertices, 2), dtype=np.float64)

        normalized = (vertices - bbox_min) / max_extent

        if bbox_size.shape[0] == 3:
            projection_axis = np.argmax(bbox_size)
        else:
            projection_axis = 1

        uv = np.zeros((num_vertices, 2), dtype=np.float64)
        axes = [i for i in range(3) if i != projection_axis]
        uv[:, 0] = normalized[:, axes[0]]
        uv[:, 1] = 1.0 - normalized[:, axes[1]]

        margin = 0.01
        uv = uv * (1.0 - 2 * margin) + margin

        return uv

    def _rasterize_texture(
        self,
        atlas,
        uv_coords,
        vertices,
        triangles,
        images,
        cam_dicts,
    ):
        atlas_h, atlas_w = atlas.shape[:2]
        num_views = len(images)

        view_contributions = [np.zeros_like(atlas, dtype=np.float64) for _ in range(num_views)]
        view_weights = [np.zeros((atlas_h, atlas_w), dtype=np.float64) for _ in range(num_views)]

        for view_idx in range(num_views):
            img = images[view_idx]
            cam = cam_dicts[view_idx]
            intrinsic = np.array(cam["intrinsic"])
            extrinsic = np.array(cam["extrinsic"])
            R = extrinsic[:3, :3]
            t = extrinsic[:3, 3]

            h, w = img.shape[:2]
            fx, fy = intrinsic[0, 0], intrinsic[1, 1]
            cx, cy = intrinsic[0, 2], intrinsic[1, 2]

            for tri_idx, tri in enumerate(triangles):
                tri_verts = vertices[tri]
                pts_cam = (R @ tri_verts.T).T + t

                if np.any(pts_cam[:, 2] <= 0):
                    continue

                tri_px = pts_cam[:, 0] * fx / pts_cam[:, 2] + cx
                tri_py = pts_cam[:, 1] * fy / pts_cam[:, 2] + cy

                if np.any(tri_px < 0) or np.any(tri_px >= w):
                    continue
                if np.any(tri_py < 0) or np.any(tri_py >= h):
                    continue

                tri_uv = uv_coords[tri]

                avg_depth = np.mean(pts_cam[:, 2])
                weight = 1.0 / (avg_depth + 1e-6)

                self._rasterize_triangle_to_atlas(
                    atlas, view_contributions[view_idx],
                    view_weights[view_idx],
                    tri_uv, tri_px, tri_py, img, weight,
                )

        atlas_blended = np.zeros_like(atlas, dtype=np.float64)
        total_weight = np.zeros((atlas_h, atlas_w), dtype=np.float64)

        for view_idx in range(num_views):
            valid = view_weights[view_idx] > 0
            atlas_blended[valid] += view_contributions[view_idx][valid]
            total_weight[valid] += view_weights[view_idx][valid]

        valid_pixels = total_weight > 0
        atlas[valid_pixels] = (
            atlas_blended[valid_pixels] / total_weight[valid_pixels, np.newaxis]
        ).astype(np.uint8)

        if self.gaussian_sigma > 0:
            for c in range(3):
                atlas[:, :, c] = cv2.GaussianBlur(
                    atlas[:, :, c], (0, 0), self.gaussian_sigma
                )

        return atlas, uv_coords

    def _rasterize_triangle_to_atlas(
        self,
        atlas,
        contribution,
        weight_map,
        tri_uv,
        tri_px,
        tri_py,
        image,
        weight,
    ):
        atlas_h, atlas_w = atlas.shape[:2]
        h, w = image.shape[:2]

        uv_min = tri_uv.min(axis=0)
        uv_max = tri_uv.max(axis=0)

        px_min = max(0, int(uv_min[0] * atlas_w) - self.chart_padding)
        px_max = min(atlas_w, int(uv_max[0] * atlas_w) + self.chart_padding + 1)
        py_min = max(0, int(uv_min[1] * atlas_h) - self.chart_padding)
        py_max = min(atlas_h, int(uv_max[1] * atlas_h) + self.chart_padding + 1)

        step = max(1, (px_max - px_min) // 32)

        for ay in range(py_min, py_max, step):
            for ax in range(px_min, px_max, step):
                u = ax / atlas_w
                v = ay / atlas_h

                bary = self._compute_barycentric(u, v, tri_uv)
                if bary is None:
                    continue
                if np.any(bary < -0.01) or np.any(bary > 1.01):
                    continue

                src_x = bary[0] * tri_px[0] + bary[1] * tri_px[1] + bary[2] * tri_px[2]
                src_y = bary[0] * tri_py[0] + bary[1] * tri_py[1] + bary[2] * tri_py[2]

                src_xi = int(np.clip(np.round(src_x), 0, w - 1))
                src_yi = int(np.clip(np.round(src_y), 0, h - 1))

                color = image[src_yi, src_xi].astype(np.float64)
                contribution[ay, ax] += color * weight
                weight_map[ay, ax] += weight

    @staticmethod
    def _compute_barycentric(px, py, triangle):
        x0, y0 = triangle[0]
        x1, y1 = triangle[1]
        x2, y2 = triangle[2]

        denom = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(denom) < 1e-10:
            return None

        l0 = ((y1 - y2) * (px - x2) + (x2 - x1) * (py - y2)) / denom
        l1 = ((y2 - y0) * (px - x2) + (x0 - x2) * (py - y2)) / denom
        l2 = 1.0 - l0 - l1

        return np.array([l0, l1, l2])

    def _sample_atlas_colors(self, uv_coords, atlas):
        atlas_h, atlas_w = atlas.shape[:2]
        num_vertices = len(uv_coords)

        colors = np.zeros((num_vertices, 3), dtype=np.float64)
        for i in range(num_vertices):
            ax = int(np.clip(uv_coords[i, 0] * atlas_w, 0, atlas_w - 1))
            ay = int(np.clip(uv_coords[i, 1] * atlas_h, 0, atlas_h - 1))
            colors[i] = atlas[ay, ax].astype(np.float64) / 255.0

        return colors


class MeshTexturer:
    def __init__(self, method="projective", atlas_resolution=4096):
        self.method = method
        self.projective = ProjectiveTexturer(texture_resolution=atlas_resolution)
        self.atlas_gen = TextureAtlasGenerator(atlas_resolution=atlas_resolution)

    def texture(
        self,
        mesh,
        images,
        cam_dicts,
        output_dir=None,
    ):
        processed_images = []
        for img in images:
            if isinstance(img, str):
                img = cv2.imread(img)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            processed_images.append(img)

        if self.method == "projective":
            mesh_textured = self.projective.texture_mesh(
                mesh, processed_images, cam_dicts
            )
            atlas_path = None
        elif self.method == "atlas":
            mesh_textured, uv_coords, atlas_path = self.atlas_gen.generate_texture_atlas(
                mesh, processed_images, cam_dicts, output_dir
            )
        else:
            raise ValueError(f"Unknown texturing method: {self.method}")

        return mesh_textured, atlas_path
