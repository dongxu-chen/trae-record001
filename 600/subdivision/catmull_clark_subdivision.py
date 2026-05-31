import numpy as np
import openmesh as om


class CatmullClarkSubdivision:
    def __init__(self, mesh=None, uv_coords=None):
        self.mesh = mesh
        self.uv_coords = uv_coords
        if self.mesh is not None:
            self._setup_mesh()

    def set_mesh(self, mesh, uv_coords=None):
        self.mesh = mesh
        self.uv_coords = uv_coords
        self._setup_mesh()

    def _setup_mesh(self):
        if not self.mesh.has_vertex_status():
            self.mesh.request_vertex_status()
        if not self.mesh.has_face_status():
            self.mesh.request_face_status()
        if not self.mesh.has_edge_status():
            self.mesh.request_edge_status()
        if not self.mesh.has_halfedge_status():
            self.mesh.request_halfedge_status()
        if not self.mesh.has_vertex_normals():
            self.mesh.request_vertex_normals()

    def subdivide(self, levels=1):
        if self.mesh is None:
            raise ValueError("Mesh not set")

        for _ in range(levels):
            self._subdivide_one_step()

        self._update_normals()

        return self.mesh

    def _subdivide_one_step(self):
        mesh = self.mesh
        has_uv = self.uv_coords is not None and len(self.uv_coords) == mesh.n_vertices()

        face_points = {}
        face_uvs = {}
        edge_points = {}
        edge_uvs = {}
        vertex_points = {}
        vertex_uvs = {}

        for fh in mesh.faces():
            face_centroid = np.zeros(3)
            uv_centroid = np.zeros(2) if has_uv else None
            count = 0
            for vh in mesh.fv(fh):
                face_centroid += np.array(mesh.point(vh))
                if has_uv:
                    uv_centroid += self.uv_coords[vh.idx()]
                count += 1
            face_centroid /= count
            face_points[fh.idx()] = face_centroid
            if has_uv:
                face_uvs[fh.idx()] = uv_centroid / count

        for eh in mesh.edges():
            heh = mesh.halfedge_handle(eh, 0)
            heh_opp = mesh.opposite_halfedge_handle(heh)

            v0 = mesh.from_vertex_handle(heh)
            v1 = mesh.to_vertex_handle(heh)

            p0 = np.array(mesh.point(v0))
            p1 = np.array(mesh.point(v1))

            if mesh.is_boundary(eh):
                edge_point = (p0 + p1) * 0.5
                if has_uv:
                    edge_uvs[eh.idx()] = (self.uv_coords[v0.idx()] + self.uv_coords[v1.idx()]) * 0.5
            else:
                fh0 = mesh.face_handle(heh)
                fh1 = mesh.face_handle(heh_opp)
                fp0 = face_points[fh0.idx()]
                fp1 = face_points[fh1.idx()]
                edge_point = (p0 + p1 + fp0 + fp1) * 0.25
                if has_uv:
                    fuv0 = face_uvs[fh0.idx()]
                    fuv1 = face_uvs[fh1.idx()]
                    edge_uvs[eh.idx()] = (self.uv_coords[v0.idx()] + self.uv_coords[v1.idx()] + fuv0 + fuv1) * 0.25

            edge_points[eh.idx()] = edge_point

        for vh in mesh.vertices():
            n = mesh.valence(vh)
            p = np.array(mesh.point(vh))

            if mesh.is_boundary(vh):
                pos, uv = self._compute_boundary_vertex_point(mesh, vh)
                vertex_points[vh.idx()] = pos
                if has_uv and uv is not None:
                    vertex_uvs[vh.idx()] = uv
            else:
                Q = np.zeros(3)
                Q_uv = np.zeros(2) if has_uv else None
                for fh in mesh.vf(vh):
                    Q += face_points[fh.idx()]
                    if has_uv:
                        Q_uv += face_uvs[fh.idx()]
                Q /= n
                if has_uv:
                    Q_uv /= n

                R = np.zeros(3)
                R_uv = np.zeros(2) if has_uv else None
                for eh in mesh.ve(vh):
                    heh = mesh.halfedge_handle(eh, 0)
                    v0 = mesh.from_vertex_handle(heh)
                    v1 = mesh.to_vertex_handle(heh)
                    p0 = np.array(mesh.point(v0))
                    p1 = np.array(mesh.point(v1))
                    R += (p0 + p1) * 0.5
                    if has_uv:
                        R_uv += (self.uv_coords[v0.idx()] + self.uv_coords[v1.idx()]) * 0.5
                R /= n
                if has_uv:
                    R_uv /= n

                vertex_point = (Q + 2 * R + (n - 3) * p) / n
                vertex_points[vh.idx()] = vertex_point

                if has_uv:
                    vertex_uvs[vh.idx()] = (Q_uv + 2 * R_uv + (n - 3) * self.uv_coords[vh.idx()]) / n

        new_mesh = om.PolyMesh()
        vertex_map = {}
        edge_vertex_map = {}
        face_vertex_map = {}

        new_uv_list = []

        for vh in mesh.vertices():
            new_vh = new_mesh.add_vertex(vertex_points[vh.idx()])
            vertex_map[vh.idx()] = new_vh
            if has_uv and vh.idx() in vertex_uvs:
                new_uv_list.append(vertex_uvs[vh.idx()])

        for eh in mesh.edges():
            new_vh = new_mesh.add_vertex(edge_points[eh.idx()])
            edge_vertex_map[eh.idx()] = new_vh
            if has_uv and eh.idx() in edge_uvs:
                new_uv_list.append(edge_uvs[eh.idx()])

        for fh in mesh.faces():
            new_vh = new_mesh.add_vertex(face_points[fh.idx()])
            face_vertex_map[fh.idx()] = new_vh
            if has_uv and fh.idx() in face_uvs:
                new_uv_list.append(face_uvs[fh.idx()])

        for fh in mesh.faces():
            face_v = face_vertex_map[fh.idx()]

            face_vertices = []
            for vh in mesh.fv(fh):
                face_vertices.append(vh)

            face_edges = []
            for heh in mesh.fh(fh):
                eh = mesh.edge_handle(heh)
                face_edges.append(eh)

            n_sides = len(face_vertices)

            for i in range(n_sides):
                v0 = vertex_map[face_vertices[i].idx()]
                e0 = edge_vertex_map[face_edges[i].idx()]
                e1 = edge_vertex_map[face_edges[(i - 1) % n_sides].idx()]

                new_mesh.add_face([v0, e0, face_v, e1])

        self.mesh = new_mesh
        self._setup_mesh()

        if has_uv and len(new_uv_list) == new_mesh.n_vertices():
            self.uv_coords = np.array(new_uv_list)
        else:
            self.uv_coords = None

    def _compute_boundary_vertex_point(self, mesh, vh):
        p = np.array(mesh.point(vh))
        has_uv = self.uv_coords is not None and len(self.uv_coords) == mesh.n_vertices()

        boundary_neighbors = []
        boundary_uv_neighbors = []
        for heh in mesh.voh(vh):
            if mesh.is_boundary(mesh.edge_handle(heh)):
                neighbor_vh = mesh.to_vertex_handle(heh)
                boundary_neighbors.append(np.array(mesh.point(neighbor_vh)))
                if has_uv:
                    boundary_uv_neighbors.append(self.uv_coords[neighbor_vh.idx()])

        uv_result = None
        if has_uv:
            uv = self.uv_coords[vh.idx()].copy()
            if len(boundary_uv_neighbors) == 2:
                uv_result = 0.75 * uv + 0.125 * boundary_uv_neighbors[0] + 0.125 * boundary_uv_neighbors[1]
            elif len(boundary_uv_neighbors) == 1:
                uv_result = 0.875 * uv + 0.125 * boundary_uv_neighbors[0]
            else:
                uv_result = uv

        if len(boundary_neighbors) == 2:
            pos = 0.75 * p + 0.125 * boundary_neighbors[0] + 0.125 * boundary_neighbors[1]
        elif len(boundary_neighbors) == 1:
            pos = 0.875 * p + 0.125 * boundary_neighbors[0]
        else:
            pos = p

        return pos, uv_result

    def _update_normals(self):
        if not self.mesh.has_vertex_normals():
            self.mesh.request_vertex_normals()
        self.mesh.update_vertex_normals()

    def get_vertices(self):
        return np.array([self.mesh.point(vh) for vh in self.mesh.vertices()])

    def get_faces(self):
        return np.array([[vh.idx() for vh in self.mesh.fv(fh)] for fh in self.mesh.faces()], dtype=object)

    def get_normals(self):
        self._update_normals()
        return np.array([self.mesh.normal(vh) for vh in self.mesh.vertices()])

    def get_uv_coords(self):
        return self.uv_coords
