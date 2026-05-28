import numpy as np
import cv2
from scipy import ndimage
from scipy.spatial import cKDTree
from collections import defaultdict


class MultiTextureBlender:
    def __init__(self, mesh, uv_coords):
        self.mesh = mesh
        self.uv = uv_coords
        self.textures = {}
        self.face_regions = {}
        self.blend_masks = {}
        self.base_texture = None

    def add_texture(self, name, texture):
        if isinstance(texture, str):
            img = cv2.imread(texture)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        else:
            img = texture.copy()
        self.textures[name] = img
        return img

    def remove_texture(self, name):
        if name in self.textures:
            del self.textures[name]

    def assign_region(self, face_indices, texture_name, blend_width=5):
        if texture_name not in self.textures:
            raise ValueError(f"Texture {texture_name} not found")

        self.face_regions[texture_name] = np.array(face_indices)
        self._compute_blend_masks(texture_name, blend_width)

    def _compute_blend_masks(self, texture_name, blend_width):
        h, w = self.textures[texture_name].shape[:2]
        mask = np.zeros((h, w), dtype=np.float32)

        faces_uv = self.uv[self.mesh.faces[self.face_regions[texture_name]]]

        for face_uv in faces_uv:
            pts = (face_uv * np.array([w, h])).astype(np.int32)
            pts[:, 1] = h - pts[:, 1]
            cv2.fillPoly(mask, [pts], 1.0)

        dist = ndimage.distance_transform_edt(mask)
        blend_mask = np.clip(dist / blend_width, 0, 1)
        self.blend_masks[texture_name] = blend_mask

    def select_faces_by_vertices(self, vertex_indices):
        face_indices = []
        vertex_set = set(vertex_indices)
        for i, face in enumerate(self.mesh.faces):
            if any(v in vertex_set for v in face):
                face_indices.append(i)
        return np.array(face_indices)

    def select_faces_by_normal(self, direction, threshold=0.5):
        normals = self.mesh.face_normals
        direction = direction / np.linalg.norm(direction)
        dot_products = np.dot(normals, direction)
        return np.where(dot_products > threshold)[0]

    def select_faces_by_area(self, min_area_ratio=0.0, max_area_ratio=1.0):
        areas = self.mesh.area_faces
        total_area = np.sum(areas)
        ratios = areas / total_area
        return np.where((ratios >= min_area_ratio) & (ratios <= max_area_ratio))[0]

    def blend_textures(self, size=1024):
        if not self.textures:
            return None

        result = np.zeros((size, size, 3), dtype=np.float32)
        total_weight = np.zeros((size, size), dtype=np.float32)

        for name, texture in self.textures.items():
            if texture.shape[:2] != (size, size):
                tex_resized = cv2.resize(texture, (size, size))
            else:
                tex_resized = texture

            if name in self.blend_masks:
                mask = cv2.resize(self.blend_masks[name], (size, size))
            else:
                mask = np.ones((size, size), dtype=np.float32)

            result += tex_resized.astype(np.float32) * mask[:, :, np.newaxis]
            total_weight += mask

        total_weight[total_weight == 0] = 1
        result = result / total_weight[:, :, np.newaxis]
        result = np.clip(result, 0, 255).astype(np.uint8)

        return result


class TextureBaker:
    def __init__(self, mesh, uv_coords):
        self.mesh = mesh
        self.uv = uv_coords

    def generate_normal_map(self, size=1024, strength=1.0):
        h, w = size, size
        normal_map = np.zeros((h, w, 3), dtype=np.float32)
        weight_map = np.zeros((h, w), dtype=np.float32)

        vertex_normals = self.mesh.vertex_normals
        faces_uv = self.uv[self.mesh.faces]

        for f_idx, face in enumerate(self.mesh.faces):
            face_uv = faces_uv[f_idx]
            face_normals = vertex_normals[face]

            pts = (face_uv * np.array([w, h])).astype(np.int32)
            pts[:, 1] = h - pts[:, 1]

            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.fillPoly(mask, [pts], 1)

            y, x = np.where(mask > 0)
            if len(y) == 0:
                continue

            for i, (py, px) in enumerate(zip(y, x)):
                uv_pt = np.array([px / w, 1 - py / h])

                v0, v1, v2 = face_uv
                v0v1 = v1 - v0
                v0v2 = v2 - v0
                v0p = uv_pt - v0

                d00 = np.dot(v0v1, v0v1)
                d01 = np.dot(v0v1, v0v2)
                d11 = np.dot(v0v2, v0v2)
                d20 = np.dot(v0p, v0v1)
                d21 = np.dot(v0p, v0v2)

                denom = d00 * d11 - d01 * d01
                if abs(denom) < 1e-8:
                    w0, w1, w2 = 1/3, 1/3, 1/3
                else:
                    w1 = (d11 * d20 - d01 * d21) / denom
                    w2 = (d00 * d21 - d01 * d20) / denom
                    w0 = 1 - w1 - w2

                normal = w0 * face_normals[0] + w1 * face_normals[1] + w2 * face_normals[2]
                normal = normal / (np.linalg.norm(normal) + 1e-8)

                normal_map[py, px] += normal
                weight_map[py, px] += 1

        weight_map[weight_map == 0] = 1
        normal_map = normal_map / weight_map[:, :, np.newaxis]

        normal_map = (normal_map + 1) / 2 * 255
        normal_map = np.clip(normal_map, 0, 255).astype(np.uint8)

        return normal_map

    def generate_specular_map(self, base_texture, size=1024, shininess=0.5):
        if base_texture.shape[:2] != (size, size):
            texture = cv2.resize(base_texture, (size, size))
        else:
            texture = base_texture.copy()

        gray = cv2.cvtColor(texture, cv2.COLOR_RGB2GRAY)

        sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        edge_mag = np.sqrt(sobel_x**2 + sobel_y**2)
        edge_mag = (edge_mag - edge_mag.min()) / (edge_mag.max() - edge_mag.min() + 1e-8)

        brightness = gray.astype(np.float32) / 255.0

        specular = (brightness * (1 - edge_mag * 0.5)) ** (1 / shininess)
        specular = (specular * 255).astype(np.uint8)

        specular_rgb = cv2.merge([specular, specular, specular])
        return specular_rgb

    def generate_roughness_map(self, base_texture, size=1024, roughness=0.3):
        if base_texture.shape[:2] != (size, size):
            texture = cv2.resize(base_texture, (size, size))
        else:
            texture = base_texture.copy()

        gray = cv2.cvtColor(texture, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0

        laplacian = cv2.Laplacian(gray, cv2.CV_32F)
        detail = np.abs(laplacian)
        detail = (detail - detail.min()) / (detail.max() - detail.min() + 1e-8)

        roughness_map = roughness + detail * (1 - roughness)
        roughness_map = np.clip(roughness_map, 0, 1)
        roughness_map = (roughness_map * 255).astype(np.uint8)

        roughness_rgb = cv2.merge([roughness_map, roughness_map, roughness_map])
        return roughness_rgb

    def generate_ao_map(self, size=1024, samples=64):
        h, w = size, size
        ao_map = np.ones((h, w), dtype=np.float32)

        vertices = self.mesh.vertices
        normals = self.mesh.vertex_normals
        tree = cKDTree(vertices)

        sample_pts = []
        for face in self.mesh.faces:
            for v in face:
                pt = self.uv[v]
                x = int(pt[0] * (w - 1))
                y = int((1 - pt[1]) * (h - 1))
                sample_pts.append((x, y, v))

        for x, y, v_idx in sample_pts:
            pos = vertices[v_idx]
            normal = normals[v_idx]

            distances, indices = tree.query(pos, k=samples + 1)
            distances = distances[1:]
            indices = indices[1:]

            ao = 0.0
            for dist, idx in zip(distances, indices):
                if dist < 1e-6:
                    continue
                dir_to_sample = vertices[idx] - pos
                dir_to_sample = dir_to_sample / (np.linalg.norm(dir_to_sample) + 1e-8)

                dot = np.dot(normal, dir_to_sample)
                if dot > 0:
                    ao += dot / (1 + dist * dist)

            ao_map[y, x] = 1.0 - min(ao / samples * 2, 1.0)

        ao_map = cv2.GaussianBlur(ao_map, (5, 5), 0)
        ao_map = (ao_map * 255).astype(np.uint8)
        ao_rgb = cv2.merge([ao_map, ao_map, ao_map])
        return ao_rgb

    def bake_all_maps(self, base_texture, size=1024):
        maps = {}
        maps['normal'] = self.generate_normal_map(size)
        maps['specular'] = self.generate_specular_map(base_texture, size)
        maps['roughness'] = self.generate_roughness_map(base_texture, size)
        maps['ao'] = self.generate_ao_map(size // 2)
        maps['ao'] = cv2.resize(maps['ao'], (size, size))
        return maps


class TextureStyleTransfer:
    def __init__(self):
        pass

    def color_transfer(self, source, target):
        if source.shape[:2] != target.shape[:2]:
            target = cv2.resize(target, (source.shape[1], source.shape[0]))

        source_lab = cv2.cvtColor(source, cv2.COLOR_RGB2LAB).astype(np.float32)
        target_lab = cv2.cvtColor(target, cv2.COLOR_RGB2LAB).astype(np.float32)

        src_mean = np.mean(source_lab, axis=(0, 1))
        src_std = np.std(source_lab, axis=(0, 1))
        tgt_mean = np.mean(target_lab, axis=(0, 1))
        tgt_std = np.std(target_lab, axis=(0, 1))

        tgt_std[tgt_std == 0] = 1

        result_lab = (target_lab - tgt_mean) * (src_std / tgt_std) + src_mean
        result_lab = np.clip(result_lab, 0, 255).astype(np.uint8)

        result_rgb = cv2.cvtColor(result_lab, cv2.COLOR_LAB2RGB)
        return result_rgb

    def histogram_matching(self, source, target):
        if source.shape[:2] != target.shape[:2]:
            target = cv2.resize(target, (source.shape[1], source.shape[0]))

        result = np.zeros_like(target)
        for c in range(3):
            src_hist, src_bins = np.histogram(source[:, :, c].flatten(), 256, [0, 256])
            tgt_hist, _ = np.histogram(target[:, :, c].flatten(), 256, [0, 256])

            src_cdf = src_hist.cumsum()
            tgt_cdf = tgt_hist.cumsum()

            src_cdf_norm = src_cdf / src_cdf[-1]
            tgt_cdf_norm = tgt_cdf / tgt_cdf[-1]

            lut = np.zeros(256, dtype=np.uint8)
            for i in range(256):
                j = np.argmin(np.abs(tgt_cdf_norm - src_cdf_norm[i]))
                lut[i] = j

            result[:, :, c] = lut[target[:, :, c]]

        return result

    def stylize_texture(self, texture, style_reference, method='histogram'):
        if method == 'color':
            return self.color_transfer(style_reference, texture)
        elif method == 'histogram':
            return self.histogram_matching(style_reference, texture)
        else:
            raise ValueError(f"Unknown method: {method}")

    def blend_styles(self, texture, style1, style2, blend_factor=0.5):
        result1 = self.histogram_matching(style1, texture)
        result2 = self.histogram_matching(style2, texture)
        blended = cv2.addWeighted(result1, 1 - blend_factor, result2, blend_factor, 0)
        return blended

    def add_noise_style(self, texture, intensity=0.1, noise_type='gaussian'):
        h, w = texture.shape[:2]

        if noise_type == 'gaussian':
            noise = np.random.normal(0, intensity * 255, (h, w, 3))
        elif noise_type == 'salt_pepper':
            noise = np.random.choice([-intensity * 255, 0, intensity * 255], (h, w, 3), p=[0.05, 0.9, 0.05])
        elif noise_type == 'speckle':
            noise = np.random.normal(1, intensity, (h, w, 3))
            result = texture.astype(np.float32) * noise
            return np.clip(result, 0, 255).astype(np.uint8)
        else:
            noise = np.zeros((h, w, 3))

        result = texture.astype(np.float32) + noise
        result = np.clip(result, 0, 255).astype(np.uint8)
        return result

    def adjust_brightness_contrast(self, texture, brightness=0, contrast=0):
        brightness = max(-127, min(127, brightness))
        contrast = max(-127, min(127, contrast))

        B = brightness / 127.0
        C = contrast / 127.0

        if C > 0:
            k = 1.0 / (1.0 - C)
        else:
            k = 1.0 + C

        result = texture.astype(np.float32)
        result = (result - 127.5) * k + 127.5 + B * 127
        result = np.clip(result, 0, 255).astype(np.uint8)
        return result

    def apply_vignette(self, texture, strength=0.5):
        h, w = texture.shape[:2]
        y, x = np.ogrid[:h, :w]
        center_y, center_x = h / 2, w / 2

        dist_from_center = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
        max_dist = np.sqrt(center_x ** 2 + center_y ** 2)
        mask = 1 - (dist_from_center / max_dist) ** 2 * strength
        mask = mask[:, :, np.newaxis]

        result = (texture.astype(np.float32) * mask).astype(np.uint8)
        return result
