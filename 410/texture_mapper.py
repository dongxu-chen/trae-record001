import numpy as np
import cv2
from scipy import ndimage
from collections import defaultdict


class TextureMapper:
    def __init__(self, mesh, uv_coords):
        self.mesh = mesh
        self.uv = uv_coords
        self.texture = None
        self.texture_size = 1024

    def set_texture(self, texture_image):
        if isinstance(texture_image, str):
            self.texture = cv2.imread(texture_image)
            self.texture = cv2.cvtColor(self.texture, cv2.COLOR_BGR2RGB)
        else:
            self.texture = texture_image
        self.texture_size = self.texture.shape[0]
        return self.texture

    def create_checkerboard_texture(self, size=1024, square_size=64):
        self.texture_size = size
        texture = np.zeros((size, size, 3), dtype=np.uint8)
        for i in range(0, size, square_size):
            for j in range(0, size, square_size):
                if (i // square_size + j // square_size) % 2 == 0:
                    texture[i:i + square_size, j:j + square_size] = [200, 200, 200]
                else:
                    texture[i:i + square_size, j:j + square_size] = [100, 100, 100]
        self.texture = texture
        return texture

    def create_gradient_texture(self, size=1024):
        self.texture_size = size
        x = np.linspace(0, 1, size)
        y = np.linspace(0, 1, size)
        xv, yv = np.meshgrid(x, y)
        texture = np.zeros((size, size, 3), dtype=np.uint8)
        texture[:, :, 0] = (xv * 255).astype(np.uint8)
        texture[:, :, 1] = (yv * 255).astype(np.uint8)
        texture[:, :, 2] = 128
        self.texture = texture
        return texture

    def render_uv_layout(self, size=1024, line_color=(0, 0, 0), line_width=1):
        layout = np.ones((size, size, 3), dtype=np.uint8) * 255
        faces_uv = self.uv[self.mesh.faces]

        for face_uv in faces_uv:
            points = (face_uv * size).astype(np.int32)
            points[:, 1] = size - points[:, 1]
            cv2.polylines(layout, [points], True, line_color, line_width)

        return layout

    def get_vertex_colors_from_texture(self):
        if self.texture is None:
            return None

        h, w = self.texture.shape[:2]
        uv = self.uv.copy()
        uv = np.clip(uv, 0, 1)
        x = (uv[:, 0] * (w - 1)).astype(np.int32)
        y = ((1 - uv[:, 1]) * (h - 1)).astype(np.int32)
        colors = self.texture[y, x]
        return colors

    def find_seam_edges(self):
        edge_faces = defaultdict(list)
        for f_idx, face in enumerate(self.mesh.faces):
            for i in range(3):
                v1, v2 = face[i], face[(i + 1) % 3]
                edge = tuple(sorted([v1, v2]))
                edge_faces[edge].append(f_idx)

        seam_edges = [edge for edge, faces in edge_faces.items() if len(faces) > 1]
        return seam_edges, edge_faces

    def fix_seams_boundary_copy(self, blend_width=3):
        if self.texture is None:
            return None

        h, w = self.texture.shape[:2]
        result = self.texture.copy().astype(np.float32)

        seam_edges, edge_faces = self.find_seam_edges()

        edge_uv_pairs = []
        for edge in seam_edges:
            v1, v2 = edge
            uv1 = self.uv[v1]
            uv2 = self.uv[v2]
            edge_uv_pairs.append((uv1, uv2))

        seam_mask = np.zeros((h, w), dtype=np.uint8)
        faces_uv = self.uv[self.mesh.faces]

        for face_uv in faces_uv:
            pts = (face_uv * np.array([w, h])).astype(np.int32)
            pts[:, 1] = h - pts[:, 1]
            cv2.fillPoly(seam_mask, [pts], 255)

        border_mask = np.zeros((h, w), dtype=np.uint8)
        for uv1, uv2 in edge_uv_pairs:
            p1 = (int(uv1[0] * (w - 1)), int((1 - uv1[1]) * (h - 1)))
            p2 = (int(uv2[0] * (w - 1)), int((1 - uv2[1]) * (h - 1)))
            cv2.line(border_mask, p1, p2, 255, blend_width * 2 + 1)

        border_mask = cv2.dilate(border_mask, np.ones((3, 3), np.uint8), iterations=1)

        seam_region = border_mask > 0

        distance = ndimage.distance_transform_edt(255 - seam_mask)

        near_border = (distance < blend_width * 2) & (seam_mask > 0)
        fill_mask = seam_region & ~near_border

        for c in range(3):
            channel = result[:, :, c]

            seam_pixels = np.argwhere(seam_region)
            for y, x in seam_pixels:
                min_dist = float('inf')
                best_val = 0

                for dy in range(-blend_width, blend_width + 1):
                    for dx in range(-blend_width, blend_width + 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w:
                            if seam_mask[ny, nx] > 0 and not seam_region[ny, nx]:
                                dist = dx * dx + dy * dy
                                if dist < min_dist:
                                    min_dist = dist
                                    best_val = channel[ny, nx]

                if min_dist < float('inf'):
                    channel[y, x] = best_val

            result[:, :, c] = channel

        result = np.clip(result, 0, 255).astype(np.uint8)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        for c in range(3):
            result[:, :, c] = cv2.morphologyEx(result[:, :, c], cv2.MORPH_CLOSE, kernel)

        self.texture = result
        return result

    def fix_seams_linear(self, blend_width=2):
        if self.texture is None:
            return None

        edges = {}
        for f_idx, face in enumerate(self.mesh.faces):
            for i in range(3):
                edge = tuple(sorted([face[i], face[(i + 1) % 3]]))
                if edge in edges:
                    edges[edge].append(f_idx)
                else:
                    edges[edge] = [f_idx]

        seam_mask = np.zeros(self.texture.shape[:2], dtype=np.float32)

        h, w = self.texture.shape[:2]
        faces_uv = self.uv[self.mesh.faces]

        for face_uv in faces_uv:
            points = (face_uv * np.array([w, h])).astype(np.int32)
            points[:, 1] = h - points[:, 1]
            cv2.fillPoly(seam_mask, [points], 1.0)

        dist = ndimage.distance_transform_edt(seam_mask)
        blend_region = (dist < blend_width) & (dist > 0)

        result = self.texture.copy()
        for c in range(3):
            channel = result[:, :, c].astype(np.float32)
            blurred = cv2.GaussianBlur(channel, (blend_width * 2 + 1, blend_width * 2 + 1), 0)
            channel[blend_region] = blurred[blend_region]
            result[:, :, c] = np.clip(channel, 0, 255).astype(np.uint8)

        self.texture = result
        return result

    def fix_seams_poisson(self):
        if self.texture is None:
            return None

        gray = cv2.cvtColor(self.texture, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=1)
        mask = dilated > 0

        result = self.texture.copy()
        for c in range(3):
            channel = result[:, :, c]
            mask_uint8 = mask.astype(np.uint8) * 255
            result[:, :, c] = cv2.inpaint(channel, mask_uint8, 3, cv2.INPAINT_TELEA)

        self.texture = result
        return result

    def apply_texture_to_mesh(self):
        if self.texture is None:
            self.create_checkerboard_texture()

        visual = self.mesh.visual
        visual = visual.to_texture()
        visual.material.baseColorTexture = self.texture
        visual.uv = self.uv
        self.mesh.visual = visual
        return self.mesh


def export_textured_mesh(mesh, uv_coords, texture, output_path, additional_maps=None):
    import os
    base_path = os.path.splitext(output_path)[0]
    obj_path = base_path + '.obj'
    mtl_path = base_path + '.mtl'
    tex_path = base_path + '_diffuse.png'

    if texture is not None:
        cv2.imwrite(tex_path, cv2.cvtColor(texture, cv2.COLOR_RGB2BGR))

    with open(mtl_path, 'w') as f:
        f.write('newmtl material_0\n')
        f.write('Ka 1.0 1.0 1.0\n')
        f.write('Kd 1.0 1.0 1.0\n')
        f.write('Ks 0.5 0.5 0.5\n')
        f.write('Ns 50.0\n')
        f.write(f'map_Kd {os.path.basename(tex_path)}\n')

        if additional_maps:
            if 'normal' in additional_maps:
                normal_path = base_path + '_normal.png'
                cv2.imwrite(normal_path, cv2.cvtColor(additional_maps['normal'], cv2.COLOR_RGB2BGR))
                f.write(f'map_Bump {os.path.basename(normal_path)}\n')
                f.write(f'bump {os.path.basename(normal_path)}\n')

            if 'specular' in additional_maps:
                spec_path = base_path + '_specular.png'
                cv2.imwrite(spec_path, cv2.cvtColor(additional_maps['specular'], cv2.COLOR_RGB2BGR))
                f.write(f'map_Ks {os.path.basename(spec_path)}\n')

            if 'roughness' in additional_maps:
                rough_path = base_path + '_roughness.png'
                cv2.imwrite(rough_path, cv2.cvtColor(additional_maps['roughness'], cv2.COLOR_RGB2BGR))
                f.write(f'map_Ns {os.path.basename(rough_path)}\n')

            if 'ao' in additional_maps:
                ao_path = base_path + '_ao.png'
                cv2.imwrite(ao_path, cv2.cvtColor(additional_maps['ao'], cv2.COLOR_RGB2BGR))
                f.write(f'map_ao {os.path.basename(ao_path)}\n')

    with open(obj_path, 'w') as f:
        f.write(f'mtllib {os.path.basename(mtl_path)}\n')
        for v in mesh.vertices:
            f.write(f'v {v[0]} {v[1]} {v[2]}\n')
        for uv in uv_coords:
            f.write(f'vt {uv[0]} {uv[1]}\n')
        f.write('usemtl material_0\n')
        for face in mesh.faces:
            f.write(f'f {face[0] + 1}/{face[0] + 1} {face[1] + 1}/{face[1] + 1} {face[2] + 1}/{face[2] + 1}\n')

    return obj_path
