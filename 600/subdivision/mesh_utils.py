import numpy as np
import openmesh as om


class MeshUtils:
    @staticmethod
    def compute_vertex_normals(mesh):
        if not mesh.has_vertex_normals():
            mesh.request_vertex_normals()

        mesh.update_vertex_normals()

        normals = np.array([mesh.normal(vh) for vh in mesh.vertices()])
        return normals

    @staticmethod
    def compute_face_normals(mesh):
        if not mesh.has_face_normals():
            mesh.request_face_normals()

        mesh.update_face_normals()

        normals = np.array([mesh.normal(fh) for fh in mesh.faces()])
        return normals

    @staticmethod
    def generate_spherical_uv(mesh):
        vertices = np.array([mesh.point(vh) for vh in mesh.vertices()])

        center = vertices.mean(axis=0)
        centered = vertices - center

        r = np.linalg.norm(centered, axis=1)
        r = np.maximum(r, 1e-10)

        u = 0.5 + np.arctan2(centered[:, 2], centered[:, 0]) / (2 * np.pi)
        v = 0.5 + np.arcsin(np.clip(centered[:, 1] / r, -1, 1)) / np.pi

        uv = np.column_stack([u, v])
        return uv

    @staticmethod
    def generate_planar_uv(mesh):
        vertices = np.array([mesh.point(vh) for vh in mesh.vertices()])

        mins = vertices.min(axis=0)
        maxs = vertices.max(axis=0)
        ranges = maxs - mins
        ranges = np.maximum(ranges, 1e-10)

        u = (vertices[:, 0] - mins[0]) / ranges[0]
        v = (vertices[:, 1] - mins[1]) / ranges[1]

        uv = np.column_stack([u, v])
        return uv

    @staticmethod
    def generate_cylindrical_uv(mesh):
        vertices = np.array([mesh.point(vh) for vh in mesh.vertices()])

        mins = vertices.min(axis=0)
        maxs = vertices.max(axis=0)
        height_range = max(maxs[1] - mins[1], 1e-10)

        u = 0.5 + np.arctan2(vertices[:, 2], vertices[:, 0]) / (2 * np.pi)
        v = (vertices[:, 1] - mins[1]) / height_range

        uv = np.column_stack([u, v])
        return uv

    @staticmethod
    def export_obj(mesh, filepath, uv_coords=None):
        vertices = np.array([mesh.point(vh) for vh in mesh.vertices()])
        normals = MeshUtils.compute_vertex_normals(mesh)

        faces = []
        for fh in mesh.faces():
            face = [vh.idx() + 1 for vh in mesh.fv(fh)]
            faces.append(face)

        with open(filepath, 'w') as f:
            f.write("# OBJ file exported from Mesh Subdivision Tool\n")
            f.write(f"# Vertices: {len(vertices)}\n")
            f.write(f"# Faces: {len(faces)}\n\n")

            for v in vertices:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")

            f.write("\n")

            if uv_coords is not None and len(uv_coords) == len(vertices):
                for uv in uv_coords:
                    f.write(f"vt {uv[0]:.6f} {uv[1]:.6f}\n")
                f.write("\n")

            for n in normals:
                f.write(f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}\n")

            f.write("\n")

            for face in faces:
                if uv_coords is not None and len(uv_coords) == len(vertices):
                    face_str = " ".join([f"{v}/{v}/{v}" for v in face])
                else:
                    face_str = " ".join([f"{v}//{v}" for v in face])
                f.write(f"f {face_str}\n")

        return True

    @staticmethod
    def export_off(mesh, filepath):
        vertices = np.array([mesh.point(vh) for vh in mesh.vertices()])

        faces = []
        for fh in mesh.faces():
            face = [vh.idx() for vh in mesh.fv(fh)]
            faces.append(face)

        n_vertices = len(vertices)
        n_faces = len(faces)
        n_edges = mesh.n_edges()

        with open(filepath, 'w') as f:
            f.write("OFF\n")
            f.write(f"{n_vertices} {n_faces} {n_edges}\n\n")

            for v in vertices:
                f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")

            for face in faces:
                f.write(f"{len(face)} {' '.join(map(str, face))}\n")

        return True

    @staticmethod
    def export_ply(mesh, filepath, uv_coords=None):
        vertices = np.array([mesh.point(vh) for vh in mesh.vertices()])
        normals = MeshUtils.compute_vertex_normals(mesh)

        faces = []
        for fh in mesh.faces():
            face = [vh.idx() for vh in mesh.fv(fh)]
            faces.append(face)

        with open(filepath, 'w') as f:
            f.write("ply\n")
            f.write("format ascii 1.0\n")
            f.write("comment Exported from Mesh Subdivision Tool\n")
            f.write(f"element vertex {len(vertices)}\n")
            f.write("property float x\n")
            f.write("property float y\n")
            f.write("property float z\n")
            f.write("property float nx\n")
            f.write("property float ny\n")
            f.write("property float nz\n")
            if uv_coords is not None and len(uv_coords) == len(vertices):
                f.write("property float s\n")
                f.write("property float t\n")
            f.write(f"element face {len(faces)}\n")
            f.write("property list uchar int vertex_indices\n")
            f.write("end_header\n")

            for i, (v, n) in enumerate(zip(vertices, normals)):
                line = f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f} {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}"
                if uv_coords is not None and len(uv_coords) == len(vertices):
                    line += f" {uv_coords[i][0]:.6f} {uv_coords[i][1]:.6f}"
                f.write(line + "\n")

            for face in faces:
                f.write(f"{len(face)} {' '.join(map(str, face))}\n")

        return True

    @staticmethod
    def import_mesh(filepath):
        ext = filepath.lower().split('.')[-1]

        if ext == 'obj':
            mesh = om.PolyMesh()
            om.read_mesh(mesh, filepath)
        elif ext == 'off':
            mesh = om.PolyMesh()
            om.read_mesh(mesh, filepath)
        elif ext == 'ply':
            mesh = om.PolyMesh()
            om.read_mesh(mesh, filepath)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

        return mesh

    @staticmethod
    def import_obj_with_uv(filepath):
        mesh = om.PolyMesh()
        om.read_mesh(mesh, filepath)

        uv_coords = None
        try:
            with open(filepath, 'r') as f:
                uvs = []
                for line in f:
                    parts = line.strip().split()
                    if len(parts) > 0 and parts[0] == 'vt':
                        u = float(parts[1])
                        v = float(parts[2])
                        uvs.append([u, v])
                if uvs:
                    uv_coords = np.array(uvs)
        except Exception:
            uv_coords = None

        if uv_coords is not None and len(uv_coords) != mesh.n_vertices():
            uv_coords = MeshUtils.generate_spherical_uv(mesh)

        return mesh, uv_coords

    @staticmethod
    def create_tetrahedron():
        mesh = om.TriMesh()

        sqrt2_3 = np.sqrt(2.0 / 3.0)
        sqrt2_9 = np.sqrt(2.0 / 9.0)
        sqrt8_9 = np.sqrt(8.0 / 9.0)

        v0 = mesh.add_vertex([0, 0, 1])
        v1 = mesh.add_vertex([sqrt2_3, 0, -1.0/3.0])
        v2 = mesh.add_vertex([-sqrt2_9, sqrt8_9, -1.0/3.0])
        v3 = mesh.add_vertex([-sqrt2_9, -sqrt8_9, -1.0/3.0])

        mesh.add_face(v0, v1, v2)
        mesh.add_face(v0, v2, v3)
        mesh.add_face(v0, v3, v1)
        mesh.add_face(v1, v3, v2)

        uv = MeshUtils.generate_spherical_uv(mesh)

        return mesh, uv

    @staticmethod
    def create_cube():
        mesh = om.PolyMesh()

        s = 0.5
        v0 = mesh.add_vertex([-s, -s, -s])
        v1 = mesh.add_vertex([s, -s, -s])
        v2 = mesh.add_vertex([s, s, -s])
        v3 = mesh.add_vertex([-s, s, -s])
        v4 = mesh.add_vertex([-s, -s, s])
        v5 = mesh.add_vertex([s, -s, s])
        v6 = mesh.add_vertex([s, s, s])
        v7 = mesh.add_vertex([-s, s, s])

        mesh.add_face([v0, v1, v2, v3])
        mesh.add_face([v4, v7, v6, v5])
        mesh.add_face([v0, v4, v5, v1])
        mesh.add_face([v2, v6, v7, v3])
        mesh.add_face([v0, v3, v7, v4])
        mesh.add_face([v1, v5, v6, v2])

        uv = MeshUtils.generate_spherical_uv(mesh)

        return mesh, uv

    @staticmethod
    def create_octahedron():
        mesh = om.TriMesh()

        v0 = mesh.add_vertex([1, 0, 0])
        v1 = mesh.add_vertex([-1, 0, 0])
        v2 = mesh.add_vertex([0, 1, 0])
        v3 = mesh.add_vertex([0, -1, 0])
        v4 = mesh.add_vertex([0, 0, 1])
        v5 = mesh.add_vertex([0, 0, -1])

        mesh.add_face(v0, v2, v4)
        mesh.add_face(v0, v4, v3)
        mesh.add_face(v0, v3, v5)
        mesh.add_face(v0, v5, v2)
        mesh.add_face(v1, v4, v2)
        mesh.add_face(v1, v3, v4)
        mesh.add_face(v1, v5, v3)
        mesh.add_face(v1, v2, v5)

        uv = MeshUtils.generate_spherical_uv(mesh)

        return mesh, uv

    @staticmethod
    def get_mesh_info(mesh):
        info = {
            'n_vertices': mesh.n_vertices(),
            'n_edges': mesh.n_edges(),
            'n_faces': mesh.n_faces(),
            'n_halfedges': mesh.n_halfedges()
        }
        return info
