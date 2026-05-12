import numpy as np


def _remove_duplicate_nodes_1d(nodes, tolerance=1e-12):
    if len(nodes) <= 1:
        return np.array(nodes, dtype=np.float64), np.arange(len(nodes))

    sorted_indices = np.argsort(nodes)
    sorted_nodes = np.array(nodes)[sorted_indices]

    unique_mask = np.ones(len(sorted_nodes), dtype=bool)
    for i in range(1, len(sorted_nodes)):
        if abs(sorted_nodes[i] - sorted_nodes[i - 1]) < tolerance:
            unique_mask[i] = False

    unique_sorted_nodes = sorted_nodes[unique_mask]

    original_to_unique = np.zeros(len(nodes), dtype=np.int32)
    unique_idx = 0
    for i in range(len(nodes)):
        if unique_mask[sorted_indices == i]:
            original_to_unique[i] = unique_idx
            unique_idx += 1
        else:
            prev_idx = np.where(sorted_indices == i)[0][0] - 1
            while prev_idx >= 0 and not unique_mask[prev_idx]:
                prev_idx -= 1
            original_to_unique[i] = original_to_unique[sorted_indices[prev_idx]]

    return unique_sorted_nodes, original_to_unique


class UnstructuredMesh1D:
    def __init__(self, nodes, neighbors=None, remove_duplicates=True, tol=1e-12):
        nodes_array = np.array(nodes, dtype=np.float64)

        if remove_duplicates:
            self.nodes, _ = _remove_duplicate_nodes_1d(nodes_array, tolerance=tol)
        else:
            self.nodes = nodes_array

        self.n_nodes = len(self.nodes)
        self.n_cells = self.n_nodes - 1
        self._init_geometry()
        if neighbors is None:
            self._init_default_neighbors()
        else:
            self.neighbors = neighbors

    def _init_geometry(self):
        self.cell_centers = 0.5 * (self.nodes[1:] + self.nodes[:-1])
        self.cell_lengths = self.nodes[1:] - self.nodes[:-1]
        self.x_min = self.nodes[0]
        self.x_max = self.nodes[-1]

    def _init_default_neighbors(self):
        self.neighbors = np.array([
            [-1, 1],
            *[[i - 1, i + 1] for i in range(1, self.n_cells - 1)],
            [self.n_cells - 2, -1]
        ], dtype=np.int32)

    def get_left_right_cells(self, face_idx):
        if face_idx == 0:
            return -1, 0
        elif face_idx == self.n_cells:
            return self.n_cells - 1, -1
        else:
            return face_idx - 1, face_idx

    def get_face_area(self, face_idx):
        return 1.0


def generate_uniform_mesh(x_min, x_max, n_cells):
    nodes = np.linspace(x_min, x_max, n_cells + 1)
    return UnstructuredMesh1D(nodes)


def generate_non_uniform_mesh(x_min, x_max, n_cells, clustering_func=None):
    if clustering_func is None:
        eta = np.linspace(0, 1, n_cells + 1)
    else:
        eta = clustering_func(np.linspace(0, 1, n_cells + 1))
    nodes = x_min + eta * (x_max - x_min)
    return UnstructuredMesh1D(nodes)


def clustering_shock(xc, beta=5.0):
    def func(eta):
        return xc + np.tanh(beta * (eta - xc)) / (2.0 * beta) + 0.5
    return func


def _find_nodes_in_hdf5(group, path=""):
    results = []

    for key in group.keys():
        item = group[key]
        current_path = f"{path}/{key}"

        if hasattr(item, 'keys'):
            lower_key = key.lower()
            if 'gridcoordinates' in lower_key or 'coords' in lower_key:
                if 'coordinatex' in item or 'x' in item or 'CoordinateX' in [k for k in item.keys()]:
                    results.append(current_path)
            results.extend(_find_nodes_in_hdf5(item, current_path))

    return results


def read_mesh_from_cgns_hdf5(filepath, remove_duplicates=True, tol=1e-12):
    try:
        import h5py
    except ImportError:
        raise ImportError(
            "Requires h5py library to read CGNS HDF5 files. "
            "Install with: pip install h5py"
        )

    with h5py.File(filepath, 'r') as f:
        coord_paths = _find_nodes_in_hdf5(f)

        if not coord_paths:
            raise ValueError(f"Mesh coordinate data not found in {filepath}")

        nodes = None
        for coord_path in coord_paths:
            coord_group = f[coord_path]
            for dataset_name in coord_group.keys():
                lower_name = dataset_name.lower()
                if 'x' in lower_name or 'coordinatex' in lower_name:
                    dataset = coord_group[dataset_name]
                    if hasattr(dataset, '__getitem__'):
                        nodes = np.array(dataset[:], dtype=np.float64).flatten()
                        if len(nodes) > 1:
                            break
            if nodes is not None and len(nodes) > 1:
                break

        if nodes is None or len(nodes) <= 1:
            raise ValueError(f"Valid 1D mesh nodes not found in {filepath}")

        nodes = np.sort(nodes)

    return UnstructuredMesh1D(nodes, remove_duplicates=remove_duplicates, tol=tol)


def read_mesh_from_text(filepath, remove_duplicates=True, tol=1e-12):
    nodes = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                try:
                    nodes.append(float(line.split()[0]))
                except ValueError:
                    continue

    if len(nodes) <= 1:
        raise ValueError(f"Insufficient nodes in {filepath}")

    nodes = np.array(nodes, dtype=np.float64)
    nodes = np.sort(nodes)

    return UnstructuredMesh1D(nodes, remove_duplicates=remove_duplicates, tol=tol)


def load_mesh(filepath, remove_duplicates=True, tol=1e-12):
    ext = filepath.lower().split('.')[-1]

    if ext in ['hdf', 'hdf5', 'h5', 'cgns']:
        return read_mesh_from_cgns_hdf5(filepath, remove_duplicates=remove_duplicates, tol=tol)
    else:
        return read_mesh_from_text(filepath, remove_duplicates=remove_duplicates, tol=tol)


class Triangle2D:
    def __init__(self, vertices, cell_id, level=0, parent_id=-1):
        self.vertices = np.array(vertices, dtype=np.float64)
        self.cell_id = cell_id
        self.level = level
        self.parent_id = parent_id
        self.children = []
        self.neighbors = [-1, -1, -1]
        self.is_active = True

        self._compute_geometry()

    def _compute_geometry(self):
        v0, v1, v2 = self.vertices
        dx1 = v1[0] - v0[0]
        dy1 = v1[1] - v0[1]
        dx2 = v2[0] - v0[0]
        dy2 = v2[1] - v0[1]

        self.area = 0.5 * abs(dx1 * dy2 - dx2 * dy1)
        self.center = np.array([
            (v0[0] + v1[0] + v2[0]) / 3.0,
            (v0[1] + v1[1] + v2[1]) / 3.0
        ])

        self.edge_centers = np.array([
            0.5 * (v0 + v1),
            0.5 * (v1 + v2),
            0.5 * (v2 + v0)
        ])

        self.edge_vectors = np.array([
            v1 - v0,
            v2 - v1,
            v0 - v2
        ])

        edge_lengths = np.array([
            np.linalg.norm(v1 - v0),
            np.linalg.norm(v2 - v1),
            np.linalg.norm(v0 - v2)
        ])
        self.edge_lengths = edge_lengths

        normals = np.array([
            [dy1, -dx1],
            [dy2 - dy1, dx1 - dx2],
            [-dy2, dx2]
        ])

        for i in range(3):
            n = normals[i]
            n_mag = np.linalg.norm(n)
            if n_mag > 0:
                normals[i] = n / n_mag

        self.edge_normals = normals

    def get_edge_nodes(self, edge_idx):
        v_idx = [(0, 1), (1, 2), (2, 0)][edge_idx]
        return self.vertices[v_idx[0]], self.vertices[v_idx[1]]

    def contains_point(self, point):
        def sign(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

        v = self.vertices
        d1 = sign(point, v[0], v[1])
        d2 = sign(point, v[1], v[2])
        d3 = sign(point, v[2], v[0])

        has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
        has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)

        return not (has_neg and has_pos)


class UnstructuredMesh2D:
    def __init__(self, cells=None, nodes=None, connectivity=None):
        if cells is not None:
            self.cells = cells
            self._init_from_cells()
        elif nodes is not None and connectivity is not None:
            self._init_from_connectivity(nodes, connectivity)
        else:
            self.nodes = np.zeros((0, 2), dtype=np.float64)
            self.connectivity = np.zeros((0, 3), dtype=np.int32)
            self.cells = []
            self.n_cells = 0
            self.n_nodes = 0

        self.x_min = np.min(self.nodes[:, 0]) if self.n_nodes > 0 else 0.0
        self.x_max = np.max(self.nodes[:, 0]) if self.n_nodes > 0 else 1.0
        self.y_min = np.min(self.nodes[:, 1]) if self.n_nodes > 0 else 0.0
        self.y_max = np.max(self.nodes[:, 1]) if self.n_nodes > 0 else 1.0

    def _init_from_cells(self):
        all_nodes = []
        node_to_idx = {}
        connectivity = []

        for cell in self.cells:
            cell_indices = []
            for v in cell.vertices:
                key = (round(v[0], 12), round(v[1], 12))
                if key not in node_to_idx:
                    node_to_idx[key] = len(all_nodes)
                    all_nodes.append(v)
                cell_indices.append(node_to_idx[key])
            connectivity.append(cell_indices)

        self.nodes = np.array(all_nodes, dtype=np.float64)
        self.connectivity = np.array(connectivity, dtype=np.int32)
        self.n_nodes = len(all_nodes)
        self.n_cells = len(self.cells)

    def _init_from_connectivity(self, nodes, connectivity):
        self.nodes = np.array(nodes, dtype=np.float64)
        self.connectivity = np.array(connectivity, dtype=np.int32)
        self.n_nodes = len(self.nodes)
        self.n_cells = len(self.connectivity)

        self.cells = []
        for i, conn in enumerate(self.connectivity):
            vertices = self.nodes[conn]
            cell = Triangle2D(vertices, cell_id=i)
            self.cells.append(cell)

        self._build_neighbors()

    def _build_neighbors(self):
        edge_map = {}

        for cell_idx, cell in enumerate(self.cells):
            for edge_idx in range(3):
                v1, v2 = cell.get_edge_nodes(edge_idx)
                k1 = (round(v1[0], 12), round(v1[1], 12))
                k2 = (round(v2[0], 12), round(v2[1], 12))

                edge_key = tuple(sorted([k1, k2]))

                if edge_key in edge_map:
                    other_cell, other_edge = edge_map[edge_key]
                    self.cells[cell_idx].neighbors[edge_idx] = other_cell
                    self.cells[other_cell].neighbors[other_edge] = cell_idx
                else:
                    edge_map[edge_key] = (cell_idx, edge_idx)

    def get_cell_neighbors(self, cell_idx):
        return self.cells[cell_idx].neighbors

    def get_cell_geometry(self, cell_idx):
        cell = self.cells[cell_idx]
        return cell.center, cell.area, cell.edge_lengths, cell.edge_normals

    def get_edge_geometry(self, cell_idx, edge_idx):
        cell = self.cells[cell_idx]
        center = cell.edge_centers[edge_idx]
        length = cell.edge_lengths[edge_idx]
        normal = cell.edge_normals[edge_idx]
        return center, length, normal

    def find_cell_containing_point(self, point):
        for i, cell in enumerate(self.cells):
            if cell.contains_point(point):
                return i
        return -1


class QuadTreeNode:
    def __init__(self, x_min, x_max, y_min, y_max, level=0, parent=None, idx_in_parent=-1):
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self.level = level
        self.parent = parent
        self.idx_in_parent = idx_in_parent
        self.children = None
        self.is_leaf = True
        self.cells = []
        self.cell_id = -1

    @property
    def center(self):
        return np.array([(self.x_min + self.x_max) / 2.0, (self.y_min + self.y_max) / 2.0])

    @property
    def width(self):
        return self.x_max - self.x_min

    @property
    def height(self):
        return self.y_max - self.y_min

    @property
    def size(self):
        return max(self.width, self.height)

    def contains_point(self, point):
        return (self.x_min <= point[0] <= self.x_max and
                self.y_min <= point[1] <= self.y_max)

    def intersects_rect(self, rect):
        rx_min, rx_max, ry_min, ry_max = rect
        return not (rx_max < self.x_min or rx_min > self.x_max or
                    ry_max < self.y_min or ry_min > self.y_max)

    def refine(self, n_children=4):
        if self.children is not None:
            return

        x_mid = (self.x_min + self.x_max) / 2.0
        y_mid = (self.y_min + self.y_max) / 2.0

        self.children = [
            QuadTreeNode(self.x_min, x_mid, self.y_min, y_mid,
                         self.level + 1, self, 0),
            QuadTreeNode(x_mid, self.x_max, self.y_min, y_mid,
                         self.level + 1, self, 1),
            QuadTreeNode(self.x_min, x_mid, y_mid, self.y_max,
                         self.level + 1, self, 2),
            QuadTreeNode(x_mid, self.x_max, y_mid, self.y_max,
                         self.level + 1, self, 3),
        ]
        self.is_leaf = False

    def coarsen(self):
        if self.children is None:
            return

        for child in self.children:
            if not child.is_leaf:
                child.coarsen()

        self.children = None
        self.is_leaf = True


class QuadTreeMesh:
    def __init__(self, x_min=0.0, x_max=1.0, y_min=0.0, y_max=1.0, base_level=0, max_level=5):
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self.max_level = max_level

        self.root = QuadTreeNode(x_min, x_max, y_min, y_max, level=base_level)

        if base_level > 0:
            self._refine_to_level(self.root, base_level)

        self._assign_cell_ids()

    def _refine_to_level(self, node, target_level):
        if node.level >= target_level:
            return

        node.refine()
        for child in node.children:
            self._refine_to_level(child, target_level)

    def _assign_cell_ids(self):
        self._cell_id_counter = 0
        self._leaf_nodes = []
        self._assign_ids_recursive(self.root)
        self.n_cells = self._cell_id_counter

    def _assign_ids_recursive(self, node):
        if node.is_leaf:
            node.cell_id = self._cell_id_counter
            self._leaf_nodes.append(node)
            self._cell_id_counter += 1
        else:
            for child in node.children:
                self._assign_ids_recursive(child)

    def get_leaves(self):
        return self._leaf_nodes

    def find_leaf_containing_point(self, point):
        return self._find_leaf_recursive(self.root, point)

    def _find_leaf_recursive(self, node, point):
        if not node.contains_point(point):
            return None

        if node.is_leaf:
            return node

        for child in node.children:
            result = self._find_leaf_recursive(child, point)
            if result is not None:
                return result

        return None

    def refine_cell(self, cell_id):
        node = self._leaf_nodes[cell_id]
        if node.level >= self.max_level:
            return False

        node.refine()
        self._assign_cell_ids()
        return True

    def coarsen_cell(self, cell_id):
        node = self._leaf_nodes[cell_id]
        parent = node.parent

        if parent is None:
            return False

        can_coarsen = True
        for sibling in parent.children:
            if not sibling.is_leaf:
                can_coarsen = False
                break

        if can_coarsen:
            parent.coarsen()
            self._assign_cell_ids()
            return True
        return False

    def get_cell_geometry(self, cell_id):
        node = self._leaf_nodes[cell_id]
        center = node.center
        area = node.width * node.height
        h = min(node.width, node.height)

        edge_centers = np.array([
            [node.x_min, center[1]],
            [node.x_max, center[1]],
            [center[0], node.y_min],
            [center[0], node.y_max],
        ])

        edge_lengths = np.array([node.height, node.height, node.width, node.width])

        edge_normals = np.array([
            [-1.0, 0.0],
            [1.0, 0.0],
            [0.0, -1.0],
            [0.0, 1.0],
        ])

        return center, area, edge_centers, edge_lengths, edge_normals, h, node.level

    def get_neighbor_cell_ids(self, cell_id):
        node = self._leaf_nodes[cell_id]
        neighbors = []

        edge_dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]

        for dx, dy in edge_dirs:
            neighbor = self._find_neighbor_in_direction(node, dx, dy)
            if neighbor is not None:
                neighbors.append(neighbor.cell_id)
            else:
                neighbors.append(-1)

        return neighbors

    def _find_neighbor_in_direction(self, node, dx, dy):
        current = node
        parent = node.parent

        if parent is None:
            return None

        child_idx = node.idx_in_parent

        sibling_idx = self._get_sibling_index(child_idx, dx, dy)

        if sibling_idx != -1:
            result = self._descend_to_leaf(parent.children[sibling_idx], -dx, -dy)
            if result is not None:
                return result

        ancestor_neighbor = self._find_neighbor_in_direction(parent, dx, dy)
        if ancestor_neighbor is None:
            return None

        return self._descend_to_leaf(ancestor_neighbor, -dx, -dy)

    def _get_sibling_index(self, idx, dx, dy):
        quad = [
            [0, 1],
            [2, 3]
        ]

        row = idx // 2
        col = idx % 2

        new_row = row + dy
        new_col = col + dx

        if 0 <= new_row < 2 and 0 <= new_col < 2:
            return quad[new_row][new_col]
        return -1

    def _descend_to_leaf(self, node, dx, dy):
        if node.is_leaf:
            return node

        if dx == 0 and dy == 0:
            return node.children[0]

        quad = [
            [0, 1],
            [2, 3]
        ]

        target_row = 0 if dy < 0 else 1
        target_col = 0 if dx < 0 else 1

        child_idx = quad[target_row][target_col]
        return self._descend_to_leaf(node.children[child_idx], dx, dy)

    def get_level_distribution(self):
        levels = {}
        for leaf in self._leaf_nodes:
            l = leaf.level
            levels[l] = levels.get(l, 0) + 1
        return levels


def generate_triangular_mesh(x_min, x_max, y_min, y_max, nx, ny):
    nodes = []
    for j in range(ny + 1):
        for i in range(nx + 1):
            x = x_min + (x_max - x_min) * i / nx
            y = y_min + (y_max - y_min) * j / ny
            nodes.append([x, y])
    nodes = np.array(nodes, dtype=np.float64)

    connectivity = []
    for j in range(ny):
        for i in range(nx):
            idx0 = j * (nx + 1) + i
            idx1 = idx0 + 1
            idx2 = idx0 + (nx + 1)
            idx3 = idx2 + 1

            connectivity.append([idx0, idx1, idx2])
            connectivity.append([idx1, idx3, idx2])

    return UnstructuredMesh2D(nodes=nodes, connectivity=connectivity)


def generate_quadtree_mesh(x_min, x_max, y_min, y_max, base_level=1, max_level=5):
    return QuadTreeMesh(x_min, x_max, y_min, y_max, base_level=base_level, max_level=max_level)


def remove_duplicate_nodes_2d(nodes, tolerance=1e-12):
    if len(nodes) <= 1:
        return np.array(nodes, dtype=np.float64), np.arange(len(nodes))

    key_to_idx = {}
    unique_nodes = []
    mapping = np.zeros(len(nodes), dtype=np.int32)

    for i, node in enumerate(nodes):
        key = (round(node[0], 12), round(node[1], 12))

        if key not in key_to_idx:
            key_to_idx[key] = len(unique_nodes)
            unique_nodes.append(node)

        mapping[i] = key_to_idx[key]

    return np.array(unique_nodes, dtype=np.float64), mapping
