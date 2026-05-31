import numpy as np
import openmesh as om
from .loop_subdivision import LoopSubdivision
from .catmull_clark_subdivision import CatmullClarkSubdivision


class ViewDependentSubdivision:
    def __init__(self, mesh, camera_position=None, algorithm='loop', uv_coords=None):
        self.original_mesh = mesh
        self.camera_position = camera_position if camera_position is not None else np.array([0, 0, 5])
        self.algorithm = algorithm
        self.uv_coords = uv_coords

        self.near_threshold = 1.5
        self.far_threshold = 4.0
        self.max_level = 3

        self.face_levels = None
        self.result_mesh = None
        self.result_uv = None

    def set_camera(self, position):
        self.camera_position = np.array(position)

    def set_thresholds(self, near, far):
        self.near_threshold = near
        self.far_threshold = far

    def _compute_face_centroids(self, mesh):
        centroids = []
        for fh in mesh.faces():
            centroid = np.zeros(3)
            count = 0
            for vh in mesh.fv(fh):
                centroid += np.array(mesh.point(vh))
                count += 1
            centroid /= count
            centroids.append(centroid)
        return np.array(centroids)

    def _compute_face_distances(self, centroids):
        diff = centroids - self.camera_position[np.newaxis, :]
        distances = np.linalg.norm(diff, axis=1)
        return distances

    def _compute_face_edge_lengths(self, mesh):
        lengths = []
        for fh in mesh.faces():
            verts = [np.array(mesh.point(vh)) for vh in mesh.fv(fh)]
            if len(verts) >= 2:
                edge_len = np.mean([np.linalg.norm(verts[i] - verts[(i + 1) % len(verts)])
                                    for i in range(len(verts))])
            else:
                edge_len = 0
            lengths.append(edge_len)
        return np.array(lengths)

    def compute_subdivision_levels(self, mesh):
        centroids = self._compute_face_centroids(mesh)
        distances = self._compute_face_distances(centroids)
        edge_lengths = self._compute_face_edge_lengths(mesh)

        screen_sizes = edge_lengths / np.maximum(distances, 1e-6)

        levels = np.zeros(mesh.n_faces(), dtype=int)

        for i in range(mesh.n_faces()):
            if distances[i] < self.near_threshold:
                levels[i] = self.max_level
            elif distances[i] > self.far_threshold:
                levels[i] = 0
            else:
                t = (distances[i] - self.near_threshold) / (self.far_threshold - self.near_threshold)
                levels[i] = max(0, int(self.max_level * (1 - t) + 0.5))

            if screen_sizes[i] > 0.3:
                levels[i] = min(levels[i] + 1, self.max_level)
            elif screen_sizes[i] < 0.05:
                levels[i] = max(0, levels[i] - 1)

        self.face_levels = levels
        return levels

    def subdivide_view_dependent(self):
        mesh = self._copy_mesh(self.original_mesh)
        current_uv = self.uv_coords.copy() if self.uv_coords is not None else None

        self.compute_subdivision_levels(mesh)

        for level in range(1, self.max_level + 1):
            faces_to_subdivide = []

            if self.face_levels is not None and len(self.face_levels) == mesh.n_faces():
                for fh in mesh.faces():
                    if self.face_levels[fh.idx()] >= level:
                        faces_to_subdivide.append(fh.idx())

            if len(faces_to_subdivide) == 0:
                continue

            if len(faces_to_subdivide) == mesh.n_faces():
                if self.algorithm == 'loop' and isinstance(mesh, om.TriMesh):
                    subdiv = LoopSubdivision(mesh, current_uv)
                    mesh = subdiv.subdivide(1)
                    current_uv = subdiv.get_uv_coords()
                else:
                    subdiv = CatmullClarkSubdivision(mesh, current_uv)
                    mesh = subdiv.subdivide(1)
                    current_uv = subdiv.get_uv_coords()

                self.compute_subdivision_levels(mesh)
            else:
                mesh, current_uv = self._partial_subdivide(mesh, current_uv, faces_to_subdivide)
                self.compute_subdivision_levels(mesh)

        self.result_mesh = mesh
        self.result_uv = current_uv
        return mesh, current_uv

    def _partial_subdivide(self, mesh, uv_coords, face_indices):
        face_set = set(face_indices)
        edge_set = set()
        for fh_idx in face_indices:
            fh = mesh.face_handle(fh_idx)
            for heh in mesh.fh(fh):
                eh = mesh.edge_handle(heh)
                edge_set.add(eh.idx())

        boundary_edges = set()
        for eh_idx in edge_set:
            eh = mesh.edge_handle(eh_idx)
            heh = mesh.halfedge_handle(eh, 0)
            heh_opp = mesh.opposite_halfedge_handle(heh)

            fh0 = mesh.face_handle(heh)
            fh1 = mesh.face_handle(heh_opp)

            if fh0.idx() in face_set and (not fh1.is_valid() or fh1.idx() not in face_set):
                boundary_edges.add(eh_idx)
            elif fh1.idx() in face_set and (not fh0.is_valid() or fh0.idx() not in face_set):
                boundary_edges.add(eh_idx)

        if self.algorithm == 'loop' and isinstance(mesh, om.TriMesh):
            return self._partial_loop_subdivide(mesh, uv_coords, face_set, edge_set, boundary_edges)
        else:
            return self._partial_cc_subdivide(mesh, uv_coords, face_set, edge_set, boundary_edges)

    def _partial_loop_subdivide(self, mesh, uv_coords, face_set, edge_set, boundary_edges):
        has_uv = uv_coords is not None and len(uv_coords) == mesh.n_vertices()

        new_vertices = {}
        edge_midpoints = {}

        for eh_idx in edge_set:
            eh = mesh.edge_handle(eh_idx)
            heh = mesh.halfedge_handle(eh, 0)
            heh_opp = mesh.opposite_halfedge_handle(heh)

            v0 = mesh.from_vertex_handle(heh)
            v1 = mesh.to_vertex_handle(heh)

            p0 = np.array(mesh.point(v0))
            p1 = np.array(mesh.point(v1))

            if eh_idx in boundary_edges:
                midpoint = (p0 + p1) * 0.5
                if has_uv:
                    uv_mid = (uv_coords[v0.idx()] + uv_coords[v1.idx()]) * 0.5
            else:
                v2 = mesh.to_vertex_handle(mesh.next_halfedge_handle(heh))
                p2 = np.array(mesh.point(v2))

                if not mesh.is_boundary(eh):
                    v3 = mesh.to_vertex_handle(mesh.next_halfedge_handle(heh_opp))
                    p3 = np.array(mesh.point(v3))
                    midpoint = (p0 + p1) * 0.375 + (p2 + p3) * 0.125
                    if has_uv:
                        uv_mid = (uv_coords[v0.idx()] + uv_coords[v1.idx()]) * 0.375 + \
                                 (uv_coords[v2.idx()] + uv_coords[v3.idx()]) * 0.125
                else:
                    midpoint = (p0 + p1) * 0.5
                    if has_uv:
                        uv_mid = (uv_coords[v0.idx()] + uv_coords[v1.idx()]) * 0.5

            edge_midpoints[eh_idx] = midpoint

        return self._build_partial_mesh(mesh, uv_coords, face_set, edge_set, edge_midpoints, has_uv)

    def _partial_cc_subdivide(self, mesh, uv_coords, face_set, edge_set, boundary_edges):
        has_uv = uv_coords is not None and len(uv_coords) == mesh.n_vertices()

        face_centroids = {}
        face_uv_centroids = {}
        for fh_idx in face_set:
            fh = mesh.face_handle(fh_idx)
            centroid = np.zeros(3)
            uv_centroid = np.zeros(2) if has_uv else None
            count = 0
            for vh in mesh.fv(fh):
                centroid += np.array(mesh.point(vh))
                if has_uv:
                    uv_centroid += uv_coords[vh.idx()]
                count += 1
            centroid /= count
            face_centroids[fh_idx] = centroid
            if has_uv:
                face_uv_centroids[fh_idx] = uv_centroid / count

        edge_midpoints = {}
        for eh_idx in edge_set:
            eh = mesh.edge_handle(eh_idx)
            heh = mesh.halfedge_handle(eh, 0)
            heh_opp = mesh.opposite_halfedge_handle(heh)

            v0 = mesh.from_vertex_handle(heh)
            v1 = mesh.to_vertex_handle(heh)

            p0 = np.array(mesh.point(v0))
            p1 = np.array(mesh.point(v1))

            fh0 = mesh.face_handle(heh)
            fh1 = mesh.face_handle(heh_opp)

            if eh_idx in boundary_edges or mesh.is_boundary(eh):
                midpoint = (p0 + p1) * 0.5
                if has_uv:
                    uv_mid = (uv_coords[v0.idx()] + uv_coords[v1.idx()]) * 0.5
            else:
                fp0 = face_centroids.get(fh0.idx(), (p0 + p1) * 0.5)
                fp1 = face_centroids.get(fh1.idx(), (p0 + p1) * 0.5)
                midpoint = (p0 + p1 + fp0 + fp1) * 0.25
                if has_uv:
                    fuv0 = face_uv_centroids.get(fh0.idx(), (uv_coords[v0.idx()] + uv_coords[v1.idx()]) * 0.5)
                    fuv1 = face_uv_centroids.get(fh1.idx(), (uv_coords[v0.idx()] + uv_coords[v1.idx()]) * 0.5)
                    uv_mid = (uv_coords[v0.idx()] + uv_coords[v1.idx()] + fuv0 + fuv1) * 0.25

            edge_midpoints[eh_idx] = midpoint

        return self._build_partial_cc_mesh(mesh, uv_coords, face_set, edge_set,
                                           edge_midpoints, face_centroids,
                                           face_uv_centroids, has_uv)

    def _build_partial_mesh(self, mesh, uv_coords, face_set, edge_set, edge_midpoints, has_uv):
        if isinstance(mesh, om.TriMesh):
            new_mesh = om.TriMesh()
        else:
            new_mesh = om.PolyMesh()

        vertex_map = {}
        new_uv_list = []

        for vh in mesh.vertices():
            new_vh = new_mesh.add_vertex(mesh.point(vh))
            vertex_map[vh.idx()] = new_vh
            if has_uv:
                new_uv_list.append(uv_coords[vh.idx()])

        midpoint_vertex_map = {}
        for eh_idx, midpoint in edge_midpoints.items():
            new_vh = new_mesh.add_vertex(midpoint)
            midpoint_vertex_map[eh_idx] = new_vh

        for fh in mesh.faces():
            if fh.idx() not in face_set:
                face_vhs = [vertex_map[vh.idx()] for vh in mesh.fv(fh)]
                if len(face_vhs) == 3:
                    new_mesh.add_face(face_vhs[0], face_vhs[1], face_vhs[2])
                else:
                    new_mesh.add_face(face_vhs)
            else:
                verts = list(mesh.fv(fh))
                edges = []
                for heh in mesh.fh(fh):
                    eh = mesh.edge_handle(heh)
                    edges.append(eh)

                if len(verts) == 3 and len(edges) == 3:
                    v0 = vertex_map[verts[0].idx()]
                    v1 = vertex_map[verts[1].idx()]
                    v2 = vertex_map[verts[2].idx()]

                    e0 = midpoint_vertex_map.get(edges[0].idx())
                    e1 = midpoint_vertex_map.get(edges[1].idx())
                    e2 = midpoint_vertex_map.get(edges[2].idx())

                    if e0 is not None and e1 is not None and e2 is not None:
                        new_mesh.add_face(v0, e0, e2)
                        new_mesh.add_face(e0, v1, e1)
                        new_mesh.add_face(e2, e1, v2)
                        new_mesh.add_face(e0, e1, e2)
                    else:
                        new_mesh.add_face(v0, v1, v2)

        result_uv = np.array(new_uv_list) if has_uv and len(new_uv_list) == new_mesh.n_vertices() else None
        return new_mesh, result_uv

    def _build_partial_cc_mesh(self, mesh, uv_coords, face_set, edge_set, edge_midpoints,
                               face_centroids, face_uv_centroids, has_uv):
        new_mesh = om.PolyMesh()

        vertex_map = {}
        new_uv_list = []

        for vh in mesh.vertices():
            new_vh = new_mesh.add_vertex(mesh.point(vh))
            vertex_map[vh.idx()] = new_vh
            if has_uv:
                new_uv_list.append(uv_coords[vh.idx()])

        midpoint_vertex_map = {}
        for eh_idx, midpoint in edge_midpoints.items():
            new_vh = new_mesh.add_vertex(midpoint)
            midpoint_vertex_map[eh_idx] = new_vh

        centroid_vertex_map = {}
        for fh_idx, centroid in face_centroids.items():
            new_vh = new_mesh.add_vertex(centroid)
            centroid_vertex_map[fh_idx] = new_vh
            if has_uv and fh_idx in face_uv_centroids:
                new_uv_list.append(face_uv_centroids[fh_idx])

        for fh in mesh.faces():
            if fh.idx() not in face_set:
                face_vhs = [vertex_map[vh.idx()] for vh in mesh.fv(fh)]
                new_mesh.add_face(face_vhs)
            else:
                face_v = centroid_vertex_map[fh.idx()]

                face_vertices = list(mesh.fv(fh))
                face_edges = []
                for heh in mesh.fh(fh):
                    eh = mesh.edge_handle(heh)
                    face_edges.append(eh)

                n_sides = len(face_vertices)

                for i in range(n_sides):
                    v = vertex_map[face_vertices[i].idx()]
                    e_next = midpoint_vertex_map.get(face_edges[i].idx())
                    e_prev = midpoint_vertex_map.get(face_edges[(i - 1) % n_sides].idx())

                    if e_next is not None and e_prev is not None:
                        new_mesh.add_face([v, e_next, face_v, e_prev])
                    else:
                        pass

        result_uv = np.array(new_uv_list) if has_uv and len(new_uv_list) == new_mesh.n_vertices() else None
        return new_mesh, result_uv

    def _copy_mesh(self, mesh):
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

    def get_face_levels(self):
        return self.face_levels
