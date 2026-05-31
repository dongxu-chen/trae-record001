import numpy as np
from scipy.ndimage import map_coordinates


class BaseTransform:
    def __init__(self, dim=2, image_shape=None):
        self.dim = dim
        self.image_shape = image_shape
        self._has_matrix = True

    def get_matrix(self, params):
        if not self._has_matrix:
            raise NotImplementedError("This transform does not have a matrix representation")
        raise NotImplementedError

    def transform_point(self, point, params):
        if self._has_matrix:
            M = self.get_matrix(params)
            homogeneous = np.append(point, 1.0)
            return (M @ homogeneous)[: self.dim]
        return self._transform_point_freeform(point, params)

    def _transform_point_freeform(self, point, params):
        raise NotImplementedError

    def apply_to_image(self, image, params, output_shape=None):
        if output_shape is None:
            output_shape = image.shape

        if self._has_matrix:
            M = self.get_matrix(params)
            if self.dim == 2:
                return self._apply_2d(image, M, output_shape)
            return self._apply_3d(image, M, output_shape)

        return self._apply_freeform(image, params, output_shape)

    def _apply_freeform(self, image, params, output_shape):
        dim = len(output_shape)
        if dim == 2:
            rows, cols = output_shape[:2]
            coords = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
            coords = np.stack([coords[0].ravel(), coords[1].ravel()], axis=0)
        else:
            slices, rows, cols = output_shape[:3]
            coords = np.meshgrid(np.arange(slices), np.arange(rows), np.arange(cols), indexing="ij")
            coords = np.stack([coords[0].ravel(), coords[1].ravel(), coords[2].ravel()], axis=0)

        src_coords = self._get_source_coords(coords, params, output_shape)

        result = map_coordinates(
            image, src_coords.tolist(), order=1, mode="constant", cval=0.0
        )
        return result.reshape(output_shape)

    def _get_source_coords(self, target_coords, params, output_shape):
        raise NotImplementedError

    def get_displacement_field(self, params, output_shape):
        dim = len(output_shape)
        if dim == 2:
            rows, cols = output_shape[:2]
            y_coords, x_coords = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
            coords = np.stack([y_coords.ravel(), x_coords.ravel()], axis=0)
        else:
            slices, rows, cols = output_shape[:3]
            z_coords, y_coords, x_coords = np.meshgrid(
                np.arange(slices), np.arange(rows), np.arange(cols), indexing="ij"
            )
            coords = np.stack([z_coords.ravel(), y_coords.ravel(), x_coords.ravel()], axis=0)

        src_coords = self._get_source_coords(coords, params, output_shape)
        displacement = coords - src_coords

        if dim == 2:
            return displacement.reshape(2, rows, cols)
        return displacement.reshape(3, slices, rows, cols)

    def _apply_2d(self, image, M, output_shape):
        rows, cols = output_shape[:2]
        coords = np.meshgrid(
            np.arange(rows), np.arange(cols), indexing="ij"
        )
        coords = np.stack([coords[0].ravel(), coords[1].ravel()], axis=0)
        homogeneous = np.vstack([coords, np.ones((1, coords.shape[1]))])

        M_inv = np.linalg.inv(M)
        src_coords = M_inv @ homogeneous

        result = map_coordinates(
            image, [src_coords[0], src_coords[1]], order=1, mode="constant", cval=0.0
        )
        return result.reshape(output_shape)

    def _apply_3d(self, image, M, output_shape):
        slices, rows, cols = output_shape[:3]
        coords = np.meshgrid(
            np.arange(slices), np.arange(rows), np.arange(cols), indexing="ij"
        )
        coords = np.stack(
            [coords[0].ravel(), coords[1].ravel(), coords[2].ravel()], axis=0
        )
        homogeneous = np.vstack([coords, np.ones((1, coords.shape[1]))])

        M_inv = np.linalg.inv(M)
        src_coords = M_inv @ homogeneous

        result = map_coordinates(
            image,
            [src_coords[0], src_coords[1], src_coords[2]],
            order=1,
            mode="constant",
            cval=0.0,
        )
        return result.reshape(output_shape)

    def get_num_params(self):
        raise NotImplementedError

    def get_default_params(self):
        raise NotImplementedError


class RigidTransform(BaseTransform):
    def __init__(self, dim=2, image_shape=None):
        super().__init__(dim=dim, image_shape=image_shape)

    def get_num_params(self):
        if self.dim == 2:
            return 3
        return 6

    def get_default_params(self):
        if self.dim == 2:
            return np.zeros(3)
        return np.zeros(6)

    def get_matrix(self, params):
        params = np.asarray(params, dtype=np.float64)
        if self.dim == 2:
            return self._matrix_2d(params)
        return self._matrix_3d(params)

    def _matrix_2d(self, params):
        angle = params[0]
        tx, ty = params[1], params[2]
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)
        M = np.eye(3)
        M[0, 0] = cos_a
        M[0, 1] = -sin_a
        M[0, 2] = tx
        M[1, 0] = sin_a
        M[1, 1] = cos_a
        M[1, 2] = ty
        return M

    def _matrix_3d(self, params):
        rx, ry, rz = params[0], params[1], params[2]
        tx, ty, tz = params[3], params[4], params[5]

        cx, sx = np.cos(rx), np.sin(rx)
        cy, sy = np.cos(ry), np.sin(ry)
        cz, sz = np.cos(rz), np.sin(rz)

        Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
        Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
        Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])

        R = Rz @ Ry @ Rx
        M = np.eye(4)
        M[:3, :3] = R
        M[0, 3] = tx
        M[1, 3] = ty
        M[2, 3] = tz
        return M


class AffineTransform(BaseTransform):
    def __init__(self, dim=2, image_shape=None):
        super().__init__(dim=dim, image_shape=image_shape)

    def get_num_params(self):
        if self.dim == 2:
            return 6
        return 12

    def get_default_params(self):
        if self.dim == 2:
            return np.array([1.0, 0.0, 0.0, 0.0, 1.0, 0.0])
        return np.array(
            [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0]
        )

    def get_matrix(self, params):
        params = np.asarray(params, dtype=np.float64)
        if self.dim == 2:
            return self._matrix_2d(params)
        return self._matrix_3d(params)

    def _matrix_2d(self, params):
        M = np.eye(3)
        M[0, 0] = params[0]
        M[0, 1] = params[1]
        M[0, 2] = params[2]
        M[1, 0] = params[3]
        M[1, 1] = params[4]
        M[1, 2] = params[5]
        return M

    def _matrix_3d(self, params):
        M = np.eye(4)
        M[0, 0] = params[0]
        M[0, 1] = params[1]
        M[0, 2] = params[2]
        M[0, 3] = params[3]
        M[1, 0] = params[4]
        M[1, 1] = params[5]
        M[1, 2] = params[6]
        M[1, 3] = params[7]
        M[2, 0] = params[8]
        M[2, 1] = params[9]
        M[2, 2] = params[10]
        M[2, 3] = params[11]
        return M


class BSplineTransform(BaseTransform):
    def __init__(self, dim=2, image_shape=None, grid_spacing=32, order=3):
        super().__init__(dim=dim, image_shape=image_shape)
        self._has_matrix = False
        self.grid_spacing = grid_spacing
        self.order = order
        self._control_points = None
        self._grid_size = None
        self._grid_origin = None

        if image_shape is not None:
            self._setup_grid(image_shape)

    def _setup_grid(self, image_shape):
        self.image_shape = image_shape
        dim = self.dim
        gs = self.grid_spacing

        grid_size = tuple(max(3, int(np.ceil(s / gs)) + 2) for s in image_shape)
        grid_origin = tuple(-gs for _ in range(dim))

        self._grid_size = grid_size
        self._grid_origin = np.array(grid_origin, dtype=np.float64)

        if dim == 2:
            gy, gx = np.meshgrid(
                np.arange(grid_size[0]), np.arange(grid_size[1]), indexing="ij"
            )
            self._control_points = np.stack([
                grid_origin[0] + gy * gs,
                grid_origin[1] + gx * gs,
            ], axis=-1)
        else:
            gz, gy, gx = np.meshgrid(
                np.arange(grid_size[0]), np.arange(grid_size[1]), np.arange(grid_size[2]), indexing="ij"
            )
            self._control_points = np.stack([
                grid_origin[0] + gz * gs,
                grid_origin[1] + gy * gs,
                grid_origin[2] + gx * gs,
            ], axis=-1)

    def get_num_params(self):
        if self._grid_size is None:
            raise ValueError("Grid not initialized. Call _setup_grid first.")
        return np.prod(self._grid_size) * self.dim

    def get_default_params(self):
        return np.zeros(self.get_num_params())

    def _params_to_displacements(self, params):
        params = np.asarray(params, dtype=np.float64)
        if self._grid_size is None:
            raise ValueError("Grid not initialized")
        n = np.prod(self._grid_size)
        displacements = params.reshape(self.dim, *self._grid_size)
        return displacements

    @staticmethod
    def _bspline_basis(t, order=3):
        t = np.abs(t)
        if order == 0:
            return (t < 0.5).astype(np.float64)
        elif order == 1:
            return np.where(t < 1, 1 - t, 0.0)
        elif order == 3:
            result = np.zeros_like(t)
            mask1 = t < 1
            mask2 = (t >= 1) & (t < 2)
            result[mask1] = 2.0 / 3.0 - t[mask1] ** 2 + 0.5 * t[mask1] ** 3
            result[mask2] = 1.0 / 6.0 * (2 - t[mask2]) ** 3
            return result
        else:
            raise ValueError(f"Unsupported B-spline order: {order}")

    def _get_source_coords(self, target_coords, params, output_shape):
        if self._grid_size is None:
            self._setup_grid(output_shape)

        dim = self.dim
        gs = self.grid_spacing
        order = self.order
        half_support = (order + 1) // 2

        displacements = self._params_to_displacements(params)

        n_points = target_coords.shape[1]
        src_coords = np.zeros_like(target_coords, dtype=np.float64)

        if dim == 2:
            rows, cols = output_shape[:2]

            t_y = (target_coords[0] - self._grid_origin[0]) / gs
            t_x = (target_coords[1] - self._grid_origin[1]) / gs

            base_y = np.floor(t_y).astype(np.int32) - half_support + 1
            base_x = np.floor(t_x).astype(np.int32) - half_support + 1

            u_y = t_y - base_y
            u_x = t_x - base_x

            for dy in range(order + 1):
                gy = base_y + dy
                valid_y = (gy >= 0) & (gy < self._grid_size[0])

                by = self._bspline_basis(u_y - dy, order)

                for dx in range(order + 1):
                    gx = base_x + dx
                    valid = valid_y & (gx >= 0) & (gx < self._grid_size[1])

                    bx = self._bspline_basis(u_x - dx, order)
                    weight = by * bx

                    for d in range(dim):
                        disp_vals = displacements[d, gy[valid], gx[valid]]
                        src_coords[d, valid] += weight[valid] * disp_vals

            src_coords = target_coords - src_coords

        elif dim == 3:
            slices, rows, cols = output_shape[:3]

            t_z = (target_coords[0] - self._grid_origin[0]) / gs
            t_y = (target_coords[1] - self._grid_origin[1]) / gs
            t_x = (target_coords[2] - self._grid_origin[2]) / gs

            base_z = np.floor(t_z).astype(np.int32) - half_support + 1
            base_y = np.floor(t_y).astype(np.int32) - half_support + 1
            base_x = np.floor(t_x).astype(np.int32) - half_support + 1

            u_z = t_z - base_z
            u_y = t_y - base_y
            u_x = t_x - base_x

            for dz in range(order + 1):
                gz = base_z + dz
                valid_z = (gz >= 0) & (gz < self._grid_size[0])
                bz = self._bspline_basis(u_z - dz, order)

                for dy in range(order + 1):
                    gy = base_y + dy
                    valid_y = valid_z & (gy >= 0) & (gy < self._grid_size[1])
                    by = self._bspline_basis(u_y - dy, order)
                    weight_zy = bz * by

                    for dx in range(order + 1):
                        gx = base_x + dx
                        valid = valid_y & (gx >= 0) & (gx < self._grid_size[2])
                        bx = self._bspline_basis(u_x - dx, order)
                        weight = weight_zy * bx

                        for d in range(dim):
                            disp_vals = displacements[d, gz[valid], gy[valid], gx[valid]]
                            src_coords[d, valid] += weight[valid] * disp_vals

            src_coords = target_coords - src_coords

        return src_coords

    def _transform_point_freeform(self, point, params):
        point = np.asarray(point, dtype=np.float64).reshape(self.dim, 1)
        output_shape = self.image_shape if self.image_shape is not None else (100,) * self.dim

        target_estimate = point.copy()
        for _ in range(10):
            src = self._get_source_coords(target_estimate, params, output_shape)
            displacement = target_estimate - src
            new_target = point + displacement
            if np.linalg.norm(new_target - target_estimate) < 1e-3:
                break
            target_estimate = new_target

        return target_estimate.ravel()

    def bending_energy(self, params):
        if self._grid_size is None:
            return 0.0

        displacements = self._params_to_displacements(params)
        energy = 0.0

        for d in range(self.dim):
            disp = displacements[d]
            for axis in range(self.dim):
                grad2 = np.gradient(np.gradient(disp, axis=axis), axis=axis)
                energy += np.sum(grad2 ** 2)

        return float(energy)

    def get_jacobian_determinant(self, params, output_shape=None):
        if output_shape is None:
            output_shape = self.image_shape

        if self._grid_size is None:
            self._setup_grid(output_shape)

        dim = self.dim
        if output_shape is None:
            raise ValueError("Output shape must be provided")

        if dim == 2:
            rows, cols = output_shape[:2]
            y_coords, x_coords = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
            coords = np.stack([y_coords.ravel(), x_coords.ravel()], axis=0)
        else:
            slices, rows, cols = output_shape[:3]
            z_coords, y_coords, x_coords = np.meshgrid(
                np.arange(slices), np.arange(rows), np.arange(cols), indexing="ij"
            )
            coords = np.stack([z_coords.ravel(), y_coords.ravel(), x_coords.ravel()], axis=0)

        src = self._get_source_coords(coords, params, output_shape)
        src_reshaped = src.reshape(dim, *output_shape)

        jac_det = np.ones(output_shape)
        for i in range(dim):
            for j in range(dim):
                if i != j:
                    grad = np.gradient(src_reshaped[i], axis=j)
                    jac_det *= grad

        return jac_det
