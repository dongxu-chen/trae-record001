import numpy as np
import openmesh as om
from .loop_subdivision import LoopSubdivision
from .catmull_clark_subdivision import CatmullClarkSubdivision


class MultiResolutionMesh:
    def __init__(self, mesh, algorithm='loop', max_levels=4, uv_coords=None):
        self.base_mesh = mesh
        self.algorithm = algorithm
        self.max_levels = max_levels
        self.base_uv = uv_coords

        self.levels = {}
        self.uv_levels = {}

        self._copy_to_level(0, mesh, uv_coords)

        self.current_level = 0
        self._build_all_levels()

    def _copy_to_level(self, level, mesh, uv_coords=None):
        if isinstance(mesh, om.TriMesh):
            new_mesh = om.TriMesh()
        else:
            new_mesh = om.PolyMesh()

        vertex_map = {}
        for vh in mesh.vertices():
            new_vh = new_mesh.add_vertex(mesh.point(vh))
            vertex_map[vh.idx()] = new_vh

        for fh in mesh.faces():
            face_vertices = [vertex_map[vh.idx()] for vh in mesh.fv(fh)]
            new_mesh.add_face(face_vertices)

        if not new_mesh.has_vertex_normals():
            new_mesh.request_vertex_normals()
        new_mesh.update_vertex_normals()

        self.levels[level] = new_mesh
        self.uv_levels[level] = uv_coords.copy() if uv_coords is not None else None

    def _build_all_levels(self):
        mesh = self._copy_mesh_for_sub(self.levels[0])
        uv = self.uv_levels[0].copy() if self.uv_levels[0] is not None else None

        for level in range(1, self.max_levels + 1):
            if self.algorithm == 'loop':
                if not isinstance(mesh, om.TriMesh):
                    mesh = self._to_triangular(mesh)
                    uv = None

                subdiv = LoopSubdivision(mesh, uv)
                mesh = subdiv.subdivide(1)
                uv = subdiv.get_uv_coords()
            else:
                subdiv = CatmullClarkSubdivision(mesh, uv)
                mesh = subdiv.subdivide(1)
                uv = subdiv.get_uv_coords()

            self.levels[level] = mesh
            self.uv_levels[level] = uv

    def _copy_mesh_for_sub(self, mesh):
        if isinstance(mesh, om.TriMesh):
            new_mesh = om.TriMesh()
        else:
            new_mesh = om.PolyMesh()

        vertex_map = {}
        for vh in mesh.vertices():
            new_vh = new_mesh.add_vertex(mesh.point(vh))
            vertex_map[vh.idx()] = new_vh

        for fh in mesh.faces():
            face_vertices = [vertex_map[vh.idx()] for vh in mesh.fv(fh)]
            new_mesh.add_face(face_vertices)

        return new_mesh

    def _to_triangular(self, mesh):
        tri_mesh = om.TriMesh()

        vertex_map = {}
        for vh in mesh.vertices():
            new_vh = tri_mesh.add_vertex(mesh.point(vh))
            vertex_map[vh.idx()] = new_vh

        for fh in mesh.faces():
            face_vertices = list(mesh.fv(fh))
            if len(face_vertices) == 3:
                v0 = vertex_map[face_vertices[0].idx()]
                v1 = vertex_map[face_vertices[1].idx()]
                v2 = vertex_map[face_vertices[2].idx()]
                tri_mesh.add_face(v0, v1, v2)
            elif len(face_vertices) >= 4:
                v0 = vertex_map[face_vertices[0].idx()]
                for i in range(1, len(face_vertices) - 1):
                    v1 = vertex_map[face_vertices[i].idx()]
                    v2 = vertex_map[face_vertices[i + 1].idx()]
                    tri_mesh.add_face(v0, v1, v2)

        return tri_mesh

    def get_level(self, level):
        if level in self.levels:
            return self.levels[level], self.uv_levels.get(level)
        return None, None

    def get_current(self):
        return self.levels[self.current_level], self.uv_levels.get(self.current_level)

    def set_current_level(self, level):
        if 0 <= level <= self.max_levels:
            self.current_level = level
            return True
        return False

    def refine(self):
        if self.current_level < self.max_levels:
            self.current_level += 1
            return True
        return False

    def coarsen(self):
        if self.current_level > 0:
            self.current_level -= 1
            return True
        return False

    def get_mesh_info(self, level=None):
        if level is None:
            level = self.current_level

        if level not in self.levels:
            return None

        mesh = self.levels[level]
        return {
            'level': level,
            'n_vertices': mesh.n_vertices(),
            'n_edges': mesh.n_edges(),
            'n_faces': mesh.n_faces(),
            'has_uv': self.uv_levels.get(level) is not None
        }

    def get_all_levels_info(self):
        infos = []
        for level in range(self.max_levels + 1):
            info = self.get_mesh_info(level)
            if info is not None:
                infos.append(info)
        return infos

    def get_base_mesh(self):
        return self.levels[0]

    def get_fine_mesh(self):
        return self.levels[self.max_levels]

    def interpolate_level(self, t):
        t = np.clip(t, 0.0, 1.0)

        level_f = t * self.max_levels
        level_low = int(np.floor(level_f))
        level_high = min(level_low + 1, self.max_levels)
        alpha = level_f - level_low

        if level_low == level_high:
            return self.levels[level_low], self.uv_levels.get(level_low)

        mesh_low = self.levels[level_low]
        mesh_high = self.levels[level_high]

        uv_low = self.uv_levels.get(level_low)
        uv_high = self.uv_levels.get(level_high)

        if alpha < 0.01:
            return mesh_low, uv_low
        elif alpha > 0.99:
            return mesh_high, uv_high
        else:
            return self._interpolate_meshes(mesh_low, mesh_high, alpha, uv_low, uv_high)

    def _interpolate_meshes(self, mesh_low, mesh_high, alpha, uv_low, uv_high):
        if isinstance(mesh_high, om.TriMesh):
            new_mesh = om.TriMesh()
        else:
            new_mesh = om.PolyMesh()

        vertices_low = np.array([mesh_low.point(vh) for vh in mesh_low.vertices()])
        vertices_high = np.array([mesh_high.point(vh) for vh in mesh_high.vertices()])

        n_common = min(len(vertices_low), len(vertices_high))

        for i in range(n_common):
            interp_pos = vertices_low[i] * (1 - alpha) + vertices_high[i] * alpha
            new_mesh.add_vertex(interp_pos)

        for i in range(n_common, len(vertices_high)):
            new_mesh.add_vertex(vertices_high[i])

        vertex_map = {}
        for i in range(new_mesh.n_vertices()):
            vertex_map[i] = new_mesh.vertex_handle(i)

        for fh in mesh_high.faces():
            face_idx = [vh.idx() for vh in mesh_high.fv(fh)]
            if all(idx < new_mesh.n_vertices() for idx in face_idx):
                face_vhs = [vertex_map[idx] for idx in face_idx]
                try:
                    new_mesh.add_face(face_vhs)
                except Exception:
                    pass

        if not new_mesh.has_vertex_normals():
            new_mesh.request_vertex_normals()
        new_mesh.update_vertex_normals()

        interp_uv = None
        if uv_low is not None and uv_high is not None:
            n_uv = min(len(uv_low), len(uv_high), n_common)
            interp_uv = uv_low[:n_uv] * (1 - alpha) + uv_high[:n_uv] * alpha
            if len(uv_high) > n_uv:
                interp_uv = np.vstack([interp_uv, uv_high[n_uv:]]) if n_uv > 0 else uv_high.copy()

        return new_mesh, interp_uv
