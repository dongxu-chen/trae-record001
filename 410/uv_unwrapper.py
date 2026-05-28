import numpy as np
from scipy.sparse import lil_matrix, csr_matrix, diags
from scipy.sparse.linalg import spsolve
from scipy.optimize import minimize
import networkx as nx
import trimesh


class UVUnwrapper:
    def __init__(self, mesh):
        self.mesh = mesh
        self.vertices = mesh.vertices
        self.faces = mesh.faces
        self.n_vertices = len(self.vertices)
        self.n_faces = len(self.faces)
        self.uv = None

    def compute_face_angles(self):
        v0 = self.vertices[self.faces[:, 0]]
        v1 = self.vertices[self.faces[:, 1]]
        v2 = self.vertices[self.faces[:, 2]]

        e0 = v2 - v1
        e1 = v0 - v2
        e2 = v1 - v0

        l0 = np.linalg.norm(e0, axis=1)
        l1 = np.linalg.norm(e1, axis=1)
        l2 = np.linalg.norm(e2, axis=1)

        e0_norm = e0 / l0[:, np.newaxis]
        e1_norm = e1 / l1[:, np.newaxis]
        e2_norm = e2 / l2[:, np.newaxis]

        cos0 = np.sum(-e1_norm * e2_norm, axis=1)
        cos1 = np.sum(-e2_norm * e0_norm, axis=1)
        cos2 = np.sum(-e0_norm * e1_norm, axis=1)

        cos0 = np.clip(cos0, -1, 1)
        cos1 = np.clip(cos1, -1, 1)
        cos2 = np.clip(cos2, -1, 1)

        angles = np.column_stack([np.arccos(cos0), np.arccos(cos1), np.arccos(cos2)])
        return angles

    def compute_cotangent_weights(self):
        v0 = self.vertices[self.faces[:, 0]]
        v1 = self.vertices[self.faces[:, 1]]
        v2 = self.vertices[self.faces[:, 2]]

        area = np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1) / 2.0
        area[area == 0] = 1e-8

        cot0 = np.sum((v1 - v0) * (v2 - v0), axis=1) / (2 * area)
        cot1 = np.sum((v2 - v1) * (v0 - v1), axis=1) / (2 * area)
        cot2 = np.sum((v0 - v2) * (v1 - v2), axis=1) / (2 * area)

        return np.column_stack([cot0, cot1, cot2])

    def find_boundary_vertices(self):
        edges = {}
        for f_idx, face in enumerate(self.faces):
            for i in range(3):
                edge = tuple(sorted([face[i], face[(i + 1) % 3]]))
                if edge in edges:
                    edges[edge].append(f_idx)
                else:
                    edges[edge] = [f_idx]

        boundary_vertices = set()
        for edge, faces in edges.items():
            if len(faces) == 1:
                boundary_vertices.add(edge[0])
                boundary_vertices.add(edge[1])

        return list(boundary_vertices)

    def find_boundary_loop(self):
        boundary = self.find_boundary_vertices()
        if len(boundary) < 3:
            return boundary

        G = nx.Graph()
        boundary_set = set(boundary)

        for f_idx, face in enumerate(self.faces):
            for i in range(3):
                v1, v2 = face[i], face[(i + 1) % 3]
                if v1 in boundary_set and v2 in boundary_set:
                    G.add_edge(v1, v2, face=f_idx)

        boundary_loop = []
        try:
            start = boundary[0]
            current = start
            visited = set()
            prev = None

            while len(boundary_loop) < len(boundary):
                boundary_loop.append(current)
                visited.add(current)

                neighbors = list(G.neighbors(current))
                next_nodes = [n for n in neighbors if n not in visited]

                if not next_nodes:
                    if prev is not None and prev not in visited:
                        next_nodes = [prev]
                    else:
                        break

                if len(next_nodes) == 1:
                    next_node = next_nodes[0]
                else:
                    best_next = next_nodes[0]
                    best_angle = -np.inf

                    if len(boundary_loop) >= 2:
                        prev_vec = self.vertices[current] - self.vertices[boundary_loop[-2]]
                    else:
                        prev_vec = np.array([1, 0, 0])

                    for n in next_nodes:
                        next_vec = self.vertices[n] - self.vertices[current]
                        angle = np.arccos(np.clip(
                            np.dot(prev_vec, next_vec) / (np.linalg.norm(prev_vec) * np.linalg.norm(next_vec) + 1e-8),
                            -1, 1))
                        if angle > best_angle:
                            best_angle = angle
                            best_next = n

                    next_node = best_next

                prev = current
                current = next_node

        except Exception as e:
            boundary_loop = boundary

        return boundary_loop

    def lscm_unwrap(self):
        boundary = self.find_boundary_vertices()

        if len(boundary) < 2:
            boundary = [0, 1]

        if len(boundary) > 2:
            G = nx.Graph()
            for v in boundary:
                for f in self.faces:
                    if v in f:
                        for v2 in f:
                            if v2 in boundary and v2 != v:
                                G.add_edge(v, v2)

            if G.number_of_nodes() > 0:
                try:
                    path = nx.periphery(G)
                    pinned = [path[0], path[-1]] if len(path) >= 2 else [boundary[0], boundary[1]]
                except:
                    pinned = [boundary[0], boundary[1]]
            else:
                pinned = [boundary[0], boundary[1]]
        else:
            pinned = boundary

        pinned_set = set(pinned)
        free = [i for i in range(self.n_vertices) if i not in pinned_set]
        n_free = len(free)

        v_to_idx = {v: i for i, v in enumerate(free)}

        A = lil_matrix((2 * n_free, 2 * n_free))
        b = np.zeros(2 * n_free)

        cot = self.compute_cotangent_weights()

        for f_idx, face in enumerate(self.faces):
            for i in range(3):
                v_i = face[i]
                v_j = face[(i + 1) % 3]

                w = cot[f_idx, i] * 0.5

                for (va, vb, sign) in [(v_i, v_j, 1), (v_j, v_i, -1)]:
                    if va in v_to_idx and vb in v_to_idx:
                        row_u = 2 * v_to_idx[va]
                        col_u = 2 * v_to_idx[vb]
                        col_v = 2 * v_to_idx[vb] + 1
                        A[row_u, col_u] += sign * w
                        A[row_u + 1, col_v] += sign * w
                    elif va in v_to_idx:
                        if vb in pinned_set:
                            pos = 0 if vb == pinned[0] else 1
                            pin_uv = np.array([[0, 0], [1, 0]])
                            b[2 * v_to_idx[va]] -= sign * w * pin_uv[pos, 0]
                            b[2 * v_to_idx[va] + 1] -= sign * w * pin_uv[pos, 1]

        A = A.tocsr()
        try:
            x = spsolve(A, b)
        except:
            x = np.zeros(2 * n_free)

        uv = np.zeros((self.n_vertices, 2))
        if len(pinned) >= 2:
            uv[pinned[0]] = [0, 0]
            uv[pinned[1]] = [1, 0]

        for v, idx in v_to_idx.items():
            uv[v] = [x[2 * idx], x[2 * idx + 1]]

        uv = self.normalize_uv(uv)
        self.uv = uv
        return uv

    def abf_plus_plus_unwrap(self, max_iter=10, lambda_len=0.1, lambda_area=0.01):
        boundary_loop = self.find_boundary_loop()
        n_boundary = len(boundary_loop)

        if n_boundary < 3:
            return self.lscm_unwrap()

        boundary_set = set(boundary_loop)
        interior = [i for i in range(self.n_vertices) if i not in boundary_set]
        n_interior = len(interior)
        v_to_idx = {v: i for i, v in enumerate(interior)}

        boundary_uv = np.zeros((n_boundary, 2))
        perimeter = 0
        edge_lengths = []
        for i in range(n_boundary):
            v1 = boundary_loop[i]
            v2 = boundary_loop[(i + 1) % n_boundary]
            length = np.linalg.norm(self.vertices[v1] - self.vertices[v2])
            edge_lengths.append(length)
            perimeter += length

        t = 0
        for i in range(n_boundary):
            boundary_uv[i] = [np.cos(2 * np.pi * t), np.sin(2 * np.pi * t)]
            t += edge_lengths[i] / perimeter

        target_angles = self.compute_face_angles()

        uv = np.zeros((self.n_vertices, 2))
        for i, v in enumerate(boundary_loop):
            uv[v] = boundary_uv[i]

        cot = self.compute_cotangent_weights()

        for iteration in range(max_iter):
            A = lil_matrix((2 * n_interior, 2 * n_interior))
            bx = np.zeros(2 * n_interior)
            by = np.zeros(2 * n_interior)

            for f_idx, face in enumerate(self.faces):
                for i in range(3):
                    vi = face[i]
                    vj = face[(i + 1) % 3]
                    w = cot[f_idx, (i + 2) % 3]

                    for (va, vb, sign) in [(vi, vj, 1), (vj, vi, -1)]:
                        if va in v_to_idx:
                            row = 2 * v_to_idx[va]
                            if vb in v_to_idx:
                                col = 2 * v_to_idx[vb]
                                A[row, col] += sign * w
                                A[row + 1, col + 1] += sign * w
                            elif vb in boundary_set:
                                idx = boundary_loop.index(vb)
                                bx[row] -= sign * w * boundary_uv[idx, 0]
                                by[row + 1] -= sign * w * boundary_uv[idx, 1]

            if lambda_len > 0 or lambda_area > 0:
                for f_idx, face in enumerate(self.faces):
                    v0, v1, v2 = face[0], face[1], face[2]
                    e0_len = np.linalg.norm(self.vertices[v2] - self.vertices[v1])
                    e1_len = np.linalg.norm(self.vertices[v0] - self.vertices[v2])
                    e2_len = np.linalg.norm(self.vertices[v1] - self.vertices[v0])

                    for (vi, vj, target_len) in [(v1, v2, e0_len), (v2, v0, e1_len), (v0, v1, e2_len)]:
                        if vi in v_to_idx and vj in v_to_idx:
                            i_idx, j_idx = v_to_idx[vi], v_to_idx[vj]
                            w_len = lambda_len * target_len

                            A[2 * i_idx, 2 * i_idx] += w_len
                            A[2 * i_idx + 1, 2 * i_idx + 1] += w_len
                            A[2 * j_idx, 2 * j_idx] += w_len
                            A[2 * j_idx + 1, 2 * j_idx + 1] += w_len
                            A[2 * i_idx, 2 * j_idx] -= w_len
                            A[2 * i_idx + 1, 2 * j_idx + 1] -= w_len
                            A[2 * j_idx, 2 * i_idx] -= w_len
                            A[2 * j_idx + 1, 2 * i_idx + 1] -= w_len

            A = A.tocsr()
            try:
                x = spsolve(A, bx)
                y = spsolve(A, by)
            except:
                break

            for v, idx in v_to_idx.items():
                uv[v] = [x[idx], y[idx]]

            for f_idx, face in enumerate(self.faces):
                face_uv = uv[face]
                e0 = face_uv[2] - face_uv[1]
                e1 = face_uv[0] - face_uv[2]
                e2 = face_uv[1] - face_uv[0]

                cross = e0[0] * e2[1] - e0[1] * e2[0]
                if abs(cross) < 1e-10:
                    continue

                l0 = np.linalg.norm(e0)
                l1 = np.linalg.norm(e1)
                l2 = np.linalg.norm(e2)

                cos0 = np.clip(-np.dot(e1, e2) / (l1 * l2 + 1e-8), -1, 1)
                cos1 = np.clip(-np.dot(e2, e0) / (l2 * l0 + 1e-8), -1, 1)
                cos2 = np.clip(-np.dot(e0, e1) / (l0 * l1 + 1e-8), -1, 1)

                current_angles = np.arccos([cos0, cos1, cos2])
                target = target_angles[f_idx]

                angle_error = target - current_angles
                for i in range(3):
                    vi = face[i]
                    if vi in v_to_idx:
                        idx = v_to_idx[vi]
                        scale = 0.01 / max(iteration + 1, 1)
                        uv[vi] += scale * angle_error[i] * np.array(
                            [np.cos(current_angles[i]), np.sin(current_angles[i])])

        uv = self.normalize_uv(uv)
        self.uv = uv
        return uv

    def normalize_uv(self, uv):
        min_uv = np.min(uv, axis=0)
        max_uv = np.max(uv, axis=0)
        range_uv = max_uv - min_uv
        range_uv[range_uv == 0] = 1
        uv = (uv - min_uv) / range_uv
        uv = uv * 0.9 + 0.05
        return uv

    def unwrap(self, method='abf++'):
        if method == 'lscm':
            return self.lscm_unwrap()
        elif method == 'abf' or method == 'abf++':
            return self.abf_plus_plus_unwrap()
        else:
            raise ValueError(f"Unknown method: {method}")

    def get_face_uvs(self):
        if self.uv is None:
            return None
        return self.uv[self.faces]


def unwrap_mesh(mesh, method='abf++'):
    unwrapper = UVUnwrapper(mesh)
    return unwrapper.unwrap(method)
