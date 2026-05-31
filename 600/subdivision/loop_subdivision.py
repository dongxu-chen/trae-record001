import numpy as np
import openmesh as om


class LoopSubdivision:
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

    def _beta(self, n):
        if n == 3:
            return 3.0 / 16.0
        else:
            return (1.0 / n) * (5.0 / 8.0 - (3.0 / 8.0 + 0.25 * np.cos(2.0 * np.pi / n)) ** 2)

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

        edge_points = {}
        vertex_points = {}
        edge_uvs = {}
        vertex_uvs = {}

        for vh in mesh.vertices():
            if mesh.is_boundary(vh):
                vertex_points[vh.idx()], vertex_uvs[vh.idx()] = self._compute_boundary_vertex_point(mesh, vh)
            else:
                n = mesh.valence(vh)
                beta = self._beta(n)

                pos = np.array(mesh.point(vh)) * (1 - n * beta)

                for vv in mesh.vv(vh):
                    pos += np.array(mesh.point(vv)) * beta

                vertex_points[vh.idx()] = pos

                if has_uv:
                    uv = self.uv_coords[vh.idx()] * (1 - n * beta)
                    for vv in mesh.vv(vh):
                        uv += self.uv_coords[vv.idx()] * beta
                    vertex_uvs[vh.idx()] = uv

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
                    uv0 = self.uv_coords[v0.idx()]
                    uv1 = self.uv_coords[v1.idx()]
                    edge_uvs[eh.idx()] = (uv0 + uv1) * 0.5
            else:
                v2 = mesh.to_vertex_handle(mesh.next_halfedge_handle(heh))
                p2 = np.array(mesh.point(v2))

                v3 = mesh.to_vertex_handle(mesh.next_halfedge_handle(heh_opp))
                p3 = np.array(mesh.point(v3))

                edge_point = (p0 + p1) * 0.375 + (p2 + p3) * 0.125

                if has_uv:
                    uv0 = self.uv_coords[v0.idx()]
                    uv1 = self.uv_coords[v1.idx()]
                    uv2 = self.uv_coords[v2.idx()]
                    uv3 = self.uv_coords[v3.idx()]
                    edge_uvs[eh.idx()] = (uv0 + uv1) * 0.375 + (uv2 + uv3) * 0.125

            edge_points[eh.idx()] = edge_point

        new_mesh = om.TriMesh()
        vertex_map = {}
        edge_vertex_map = {}

        new_uv_list = []

        for vh in mesh.vertices():
            new_vh = new_mesh.add_vertex(vertex_points[vh.idx()])
            vertex_map[vh.idx()] = new_vh
            if has_uv:
                new_uv_list.append(vertex_uvs.get(vh.idx(), self.uv_coords[vh.idx()]))

        for eh in mesh.edges():
            new_vh = new_mesh.add_vertex(edge_points[eh.idx()])
            edge_vertex_map[eh.idx()] = new_vh
            if has_uv and eh.idx() in edge_uvs:
                new_uv_list.append(edge_uvs[eh.idx()])

        for fh in mesh.faces():
            vertices = []
            for vh in mesh.fv(fh):
                vertices.append(vh)

            edges = []
            for heh in mesh.fh(fh):
                eh = mesh.edge_handle(heh)
                edges.append(eh)

            v0 = vertex_map[vertices[0].idx()]
            v1 = vertex_map[vertices[1].idx()]
            v2 = vertex_map[vertices[2].idx()]

            e0 = edge_vertex_map[edges[0].idx()]
            e1 = edge_vertex_map[edges[1].idx()]
            e2 = edge_vertex_map[edges[2].idx()]

            new_mesh.add_face(v0, e0, e2)
            new_mesh.add_face(e0, v1, e1)
            new_mesh.add_face(e2, e1, v2)
            new_mesh.add_face(e0, e1, e2)

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
        return np.array([[vh.idx() for vh in self.mesh.fv(fh)] for fh in self.mesh.faces()])

    def get_normals(self):
        self._update_normals()
        return np.array([self.mesh.normal(vh) for vh in self.mesh.vertices()])

    def get_uv_coords(self):
        return self.uv_coords
