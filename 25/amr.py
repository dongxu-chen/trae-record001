import numpy as np
from mesh import QuadTreeMesh, QuadTreeNode, remove_duplicate_nodes_2d


class AMRMarker:
    def __init__(self, refine_threshold=0.5, coarsen_threshold=0.1, max_level=5, min_level=0):
        self.refine_threshold = refine_threshold
        self.coarsen_threshold = coarsen_threshold
        self.max_level = max_level
        self.min_level = min_level

    def mark_by_gradient(self, U, mesh, flux_solver, variable='all'):
        n_cells = mesh.n_cells
        marks = np.zeros(n_cells, dtype=np.int32)

        if variable == 'all':
            var_indices = list(range(U.shape[0]))
        else:
            var_indices = [variable]

        for var_idx in var_indices:
            for i in range(n_cells):
                neighbor_ids = mesh.get_neighbor_cell_ids(i)
                max_grad = 0.0

                for j in neighbor_ids:
                    if j >= 0 and j < n_cells:
                        grad = abs(U[var_idx, i] - U[var_idx, j])
                        max_grad = max(max_grad, grad)

                if max_grad > self.refine_threshold:
                    marks[i] = 1
                elif max_grad < self.coarsen_threshold:
                    if marks[i] != 1:
                        marks[i] = -1

        return marks

    def mark_by_pressure_gradient(self, U, mesh, flux_solver):
        n_cells = mesh.n_cells
        marks = np.zeros(n_cells, dtype=np.int32)

        for i in range(n_cells):
            W = flux_solver.primitive_from_conservative(U[:, i])
            p_i = W[-1]

            neighbor_ids = mesh.get_neighbor_cell_ids(i)
            max_grad = 0.0

            for j in neighbor_ids:
                if j >= 0 and j < n_cells:
                    W_j = flux_solver.primitive_from_conservative(U[:, j])
                    p_j = W_j[-1]
                    grad = abs(p_i - p_j) / (p_i + p_j + 1e-10)
                    max_grad = max(max_grad, grad)

            if max_grad > self.refine_threshold:
                marks[i] = 1
            elif max_grad < self.coarsen_threshold:
                if marks[i] != 1:
                    marks[i] = -1

        return marks

    def mark_by_density_jump(self, U, mesh, flux_solver):
        n_cells = mesh.n_cells
        marks = np.zeros(n_cells, dtype=np.int32)

        for i in range(n_cells):
            W = flux_solver.primitive_from_conservative(U[:, i])
            rho_i = W[0]

            neighbor_ids = mesh.get_neighbor_cell_ids(i)
            max_jump = 0.0

            for j in neighbor_ids:
                if j >= 0 and j < n_cells:
                    W_j = flux_solver.primitive_from_conservative(U[:, j])
                    rho_j = W_j[0]
                    jump = abs(rho_i - rho_j) / (0.5 * (rho_i + rho_j) + 1e-10)
                    max_jump = max(max_jump, jump)

            if max_jump > self.refine_threshold:
                marks[i] = 1
            elif max_jump < self.coarsen_threshold:
                if marks[i] != 1:
                    marks[i] = -1

        return marks

    def mark_by_manual_region(self, mesh, regions):
        n_cells = mesh.n_cells
        marks = np.zeros(n_cells, dtype=np.int32)

        leaves = mesh.get_leaves()
        for i, leaf in enumerate(leaves):
            for reg in regions:
                if 'refine' in reg:
                    x_min, x_max, y_min, y_max, level = reg['refine']
                    if (x_min <= leaf.center[0] <= x_max and
                            y_min <= leaf.center[1] <= y_max and
                            leaf.level < level):
                        marks[i] = 1
                        break
                elif 'coarsen' in reg:
                    x_min, x_max, y_min, y_max, level = reg['coarsen']
                    if (x_min <= leaf.center[0] <= x_max and
                            y_min <= leaf.center[1] <= y_max and
                            leaf.level > level):
                        marks[i] = -1
                        break

        return marks


class AMRManager:
    def __init__(self, mesh, marker=None):
        self.mesh = mesh
        self.marker = marker if marker is not None else AMRMarker()
        self._amr_step = 0

    def adapt(self, U, flux_solver, strategy='pressure'):
        if strategy == 'pressure':
            marks = self.marker.mark_by_pressure_gradient(U, self.mesh, flux_solver)
        elif strategy == 'density':
            marks = self.marker.mark_by_density_jump(U, self.mesh, flux_solver)
        elif strategy == 'gradient':
            marks = self.marker.mark_by_gradient(U, self.mesh, flux_solver)
        else:
            raise ValueError(f"Unknown adaption strategy: {strategy}")

        refine_count = np.sum(marks == 1)
        coarsen_count = np.sum(marks == -1)

        if refine_count == 0 and coarsen_count == 0:
            return U

        new_U = self._apply_adaption(U, marks)
        self._amr_step += 1

        return new_U

    def _apply_adaption(self, U, marks):
        refine_ids = np.where(marks == 1)[0]
        coarsen_ids = np.where(marks == -1)[0]

        for cell_id in sorted(refine_ids, reverse=True):
            if self.mesh.refine_cell(cell_id):
                U = self._interpolate_to_children(U, cell_id)

        for cell_id in sorted(coarsen_ids, reverse=True):
            if self.mesh.coarsen_cell(cell_id):
                U = self._average_to_parent(U, cell_id)

        return U

    def _interpolate_to_children(self, U, parent_id):
        n_vars = U.shape[0]
        parent_data = U[:, parent_id].copy()

        old_n_cells = self.mesh.n_cells

        new_n_cells = self.mesh.n_cells
        new_U = np.zeros((n_vars, new_n_cells))

        if old_n_cells == new_n_cells:
            return U

        inserted_at = parent_id
        new_U[:, :inserted_at] = U[:, :inserted_at]
        new_U[:, inserted_at:inserted_at + 4] = parent_data.reshape(-1, 1)

        if inserted_at < old_n_cells - 1:
            new_U[:, inserted_at + 4:] = U[:, inserted_at + 1:]

        return new_U

    def _average_to_parent(self, U, child_id):
        return U

    def refine_by_region(self, U, x_min, x_max, y_min, y_max, target_level):
        leaves = self.mesh.get_leaves()
        to_refine = []

        for i, leaf in enumerate(leaves):
            if (x_min <= leaf.center[0] <= x_max and
                    y_min <= leaf.center[1] <= y_max and
                    leaf.level < target_level):
                to_refine.append(i)

        for cell_id in sorted(to_refine, reverse=True):
            if self.mesh.refine_cell(cell_id):
                U = self._interpolate_to_children(U, cell_id)

        return U

    def balance_2to1(self):
        changed = True
        max_iterations = 10
        iteration = 0

        while changed and iteration < max_iterations:
            changed = False
            iteration += 1

            leaves = self.mesh.get_leaves()
            to_refine = []

            for i, leaf in enumerate(leaves):
                neighbor_ids = self.mesh.get_neighbor_cell_ids(i)
                for j in neighbor_ids:
                    if j >= 0 and j < len(leaves):
                        neighbor = leaves[j]
                        if neighbor.level - leaf.level > 1:
                            to_refine.append(i)
                            changed = True
                            break

            for cell_id in sorted(set(to_refine), reverse=True):
                self.mesh.refine_cell(cell_id)

        return changed


class DataInterpolator:
    def __init__(self):
        pass

    def linear_interpolation(self, source_points, source_values, target_points):
        n_target = len(target_points)
        n_source = len(source_points)
        result = np.zeros(n_target)

        for i, tp in enumerate(target_points):
            dists = np.linalg.norm(source_points - tp, axis=1)
            closest = np.argsort(dists)[:3]

            weights = 1.0 / (dists[closest] + 1e-12)
            weights /= weights.sum()
            result[i] = np.sum(source_values[closest] * weights)

        return result

    def conservative_interpolation_fine_to_coarse(self, fine_centers, fine_volumes, fine_values,
                                                   coarse_centers, coarse_volumes):
        n_coarse = len(coarse_centers)
        result = np.zeros(n_coarse)

        for i in range(n_coarse):
            c = coarse_centers[i]
            h = np.sqrt(coarse_volumes[i]) / 2.0

            mask = np.logical_and(
                np.abs(fine_centers[:, 0] - c[0]) <= h,
                np.abs(fine_centers[:, 1] - c[1]) <= h
            )

            if np.any(mask):
                result[i] = np.sum(fine_values[mask] * fine_volumes[mask]) / coarse_volumes[i]
            else:
                result[i] = fine_values[np.argmin(np.linalg.norm(fine_centers - c, axis=1))]

        return result

    def conservative_interpolation_coarse_to_fine(self, coarse_centers, coarse_volumes, coarse_values,
                                                   fine_centers, fine_volumes):
        n_fine = len(fine_centers)
        result = np.zeros(n_fine)

        for i in range(n_fine):
            c = fine_centers[i]
            dists = np.linalg.norm(coarse_centers - c, axis=1)
            closest = np.argmin(dists)
            result[i] = coarse_values[closest]

        return result


def gradient_based_error_indicator(U, mesh, flux_solver):
    n_cells = mesh.n_cells
    error = np.zeros(n_cells)

    for i in range(n_cells):
        W = flux_solver.primitive_from_conservative(U[:, i])
        rho_i, u_i, p_i = W[0], W[1], W[-1]

        neighbor_ids = mesh.get_neighbor_cell_ids(i)
        max_relative_change = 0.0

        for j in neighbor_ids:
            if j >= 0 and j < n_cells:
                W_j = flux_solver.primitive_from_conservative(U[:, j])
                rho_j, u_j, p_j = W_j[0], W_j[1], W_j[-1]

                drho = abs(rho_i - rho_j) / (0.5 * (rho_i + rho_j) + 1e-10)
                dp = abs(p_i - p_j) / (0.5 * (p_i + p_j) + 1e-10)

                max_relative_change = max(max_relative_change, drho, dp)

        error[i] = max_relative_change

    return error


def shock_detection_indicator(U, mesh, flux_solver):
    n_cells = mesh.n_cells
    indicator = np.zeros(n_cells)

    for i in range(n_cells):
        W = flux_solver.primitive_from_conservative(U[:, i])
        p_i = W[-1]

        neighbor_ids = mesh.get_neighbor_cell_ids(i)
        max_press_ratio = 1.0

        for j in neighbor_ids:
            if j >= 0 and j < n_cells:
                W_j = flux_solver.primitive_from_conservative(U[:, j])
                p_j = W_j[-1]

                ratio = max(p_i, p_j) / (min(p_i, p_j) + 1e-10)
                max_press_ratio = max(max_press_ratio, ratio)

        indicator[i] = max_press_ratio - 1.0

    return indicator
