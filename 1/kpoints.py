import numpy as np

class KPointSampler:
    def __init__(self, lattice_constant=5.431):
        self.a = lattice_constant
        self.basis = self._get_reciprocal_basis()
        self.special_points = self._get_special_points()

    def _get_reciprocal_basis(self):
        a = self.a
        return 2 * np.pi / a * np.array([
            [-0.5, 0.5, 0.5],
            [0.5, -0.5, 0.5],
            [0.5, 0.5, -0.5]
        ])

    def _get_special_points(self):
        return {
            'G': np.array([0.0, 0.0, 0.0]),
            'X': np.array([0.5, 0.0, 0.0]),
            'L': np.array([0.5, 0.5, 0.5]),
            'K': np.array([0.75, 0.75, 0.0]),
            'U': np.array([0.5, 0.25, 0.25]),
            'W': np.array([0.5, 0.25, 0.0]),
        }

    def get_path(self, path_labels, num_points_per_segment=20):
        k_points = []
        for i in range(len(path_labels) - 1):
            start = self.special_points[path_labels[i]]
            end = self.special_points[path_labels[i + 1]]
            segment = self._interpolate_kpoints(start, end, num_points_per_segment)
            k_points.extend(segment[:-1])
        k_points.append(self.special_points[path_labels[-1]])
        return np.array(k_points)

    def _interpolate_kpoints(self, start, end, num_points):
        return np.array([
            start + (end - start) * t / (num_points - 1)
            for t in range(num_points)
        ])

    def get_silicon_path(self, num_points_per_segment=20):
        path = ['G', 'X', 'U', 'K', 'G', 'L', 'W', 'X']
        return self.get_path(path, num_points_per_segment)

    def get_irreducible_kpoints(self, k_points, tol=1e-6, use_time_reversal=True):
        if use_time_reversal:
            return self._reduce_with_time_reversal(k_points, tol)
        else:
            return self._reduce_simple(k_points, tol)

    def _reduce_simple(self, k_points, tol):
        unique_indices = []
        seen = []
        for i, k in enumerate(k_points):
            is_equiv = False
            for s in seen:
                if np.linalg.norm(k - s) < tol:
                    is_equiv = True
                    break
            if not is_equiv:
                unique_indices.append(i)
                seen.append(k)
        return np.array(unique_indices), None

    def _reduce_with_time_reversal(self, k_points, tol):
        unique_indices = []
        symmetry_map = {}
        seen = []
        source_map = {}
        for i, k in enumerate(k_points):
            is_equiv = False
            equiv_source = None
            for j, s in enumerate(seen):
                if np.linalg.norm(k - s) < tol:
                    is_equiv = True
                    equiv_source = source_map[j]
                    break
                k_neg = -s
                if np.linalg.norm(k - k_neg) < tol:
                    is_equiv = True
                    equiv_source = source_map[j]
                    break
            if not is_equiv:
                unique_indices.append(i)
                seen.append(k)
                source_map[len(seen) - 1] = i
            else:
                symmetry_map[i] = equiv_source
        return np.array(unique_indices), symmetry_map

    def get_monkhorst_pack_grid(self, grid_size, center_gamma=True):
        nx, ny, nz = grid_size
        k_points = []
        for i in range(nx):
            for j in range(ny):
                for k in range(nz):
                    if center_gamma:
                        kx = (i + 0.5) / nx - 0.5
                        ky = (j + 0.5) / ny - 0.5
                        kz = (k + 0.5) / nz - 0.5
                    else:
                        kx = i / nx
                        ky = j / ny
                        kz = k / nz
                    k_points.append([kx, ky, kz])
        return np.array(k_points)

    def get_high_symmetry_points_info(self):
        info = {
            'G': r'$\Gamma$',
            'X': r'X',
            'L': r'L',
            'K': r'K',
            'U': r'U',
            'W': r'W',
        }
        return info

    def get_path_distances(self, k_points):
        distances = np.zeros(len(k_points))
        for i in range(1, len(k_points)):
            k1_cart = 2 * np.pi / self.a * k_points[i]
            k0_cart = 2 * np.pi / self.a * k_points[i - 1]
            distances[i] = distances[i - 1] + np.linalg.norm(k1_cart - k0_cart)
        return distances

    def get_si_point_labels(self, k_points, path_labels=None, num_points_per_segment=20):
        if path_labels is None:
            path_labels = ['G', 'X', 'U', 'K', 'G', 'L', 'W', 'X']
        label_positions = []
        label_names = []
        current_pos = 0
        label_positions.append(0)
        label_names.append(path_labels[0])
        for i in range(1, len(path_labels)):
            current_pos += num_points_per_segment - 1
            label_positions.append(current_pos)
            label_names.append(path_labels[i])
        return np.array(label_positions), label_names
