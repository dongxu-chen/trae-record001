import numpy as np
from scipy.ndimage import zoom, distance_transform_edt
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from typing import Optional, Tuple, Dict, Callable, List
import threading
import time


class LaplaceSolver:
    def __init__(self, nx: int, ny: int, dx: float = 1.0, dy: float = 1.0):
        self.nx = nx
        self.ny = ny
        self.dx = dx
        self.dy = dy
        self.u = np.zeros((ny, nx))
        self.mask = np.ones((ny, nx), dtype=bool)
        self.boundary_mask = np.zeros((ny, nx), dtype=bool)
        self.boundary_values = np.zeros((ny, nx))
        self.convergence_history = []
        self.iteration_count = 0
        self._interp_boundary_weights = None
        self._interp_boundary_indices = None

    def set_dirichlet_boundary(self, boundary_func: Callable[[np.ndarray, np.ndarray], np.ndarray]):
        x = np.linspace(0, (self.nx - 1) * self.dx, self.nx)
        y = np.linspace(0, (self.ny - 1) * self.dy, self.ny)
        X, Y = np.meshgrid(x, y)
        
        edge_mask = np.zeros_like(self.mask)
        edge_mask[0, :] = True
        edge_mask[-1, :] = True
        edge_mask[:, 0] = True
        edge_mask[:, -1] = True
        
        self.boundary_mask = edge_mask & self.mask
        self.boundary_values[self.boundary_mask] = boundary_func(X[self.boundary_mask], Y[self.boundary_mask])
        self.u[self.boundary_mask] = self.boundary_values[self.boundary_mask]

    def set_region_mask(self, mask: np.ndarray):
        if mask.shape != (self.ny, self.nx):
            raise ValueError(f"Mask shape {mask.shape} must match grid shape {(self.ny, self.nx)}")
        self.mask = mask.astype(bool)
        self.u[~self.mask] = np.nan

    def set_circular_region(self, center_x: float, center_y: float, radius: float):
        x = np.linspace(0, (self.nx - 1) * self.dx, self.nx)
        y = np.linspace(0, (self.ny - 1) * self.dy, self.ny)
        X, Y = np.meshgrid(x, y)
        dist_from_center = np.sqrt((X - center_x) ** 2 + (Y - center_y) ** 2)
        self.mask = dist_from_center <= radius
        self.u[~self.mask] = np.nan

    def set_annular_region(self, center_x: float, center_y: float, inner_radius: float, outer_radius: float):
        x = np.linspace(0, (self.nx - 1) * self.dx, self.nx)
        y = np.linspace(0, (self.ny - 1) * self.dy, self.ny)
        X, Y = np.meshgrid(x, y)
        dist_from_center = np.sqrt((X - center_x) ** 2 + (Y - center_y) ** 2)
        self.mask = (dist_from_center >= inner_radius) & (dist_from_center <= outer_radius)
        self.u[~self.mask] = np.nan

    def setup_linear_interpolation_boundary(self, boundary_func: Callable[[np.ndarray, np.ndarray], np.ndarray],
                                            boundary_distance: float = 1.0):
        x = np.linspace(0, (self.nx - 1) * self.dx, self.nx)
        y = np.linspace(0, (self.ny - 1) * self.dy, self.ny)
        X, Y = np.meshgrid(x, y)
        
        dist_to_boundary = distance_transform_edt(~self.mask)
        near_boundary = (dist_to_boundary <= boundary_distance) & self.mask
        
        boundary_points = []
        boundary_values_list = []
        
        for j in range(self.ny):
            for i in range(self.nx):
                if near_boundary[j, i] and not self.boundary_mask[j, i]:
                    neighbors = []
                    for dj in [-1, 0, 1]:
                        for di in [-1, 0, 1]:
                            if dj == 0 and di == 0:
                                continue
                            nj, ni = j + dj, i + di
                            if 0 <= nj < self.ny and 0 <= ni < self.nx:
                                if not self.mask[nj, ni]:
                                    px = i * self.dx
                                    py = j * self.dy
                                    
                                    if di != 0:
                                        t = 0.5 if di > 0 else -0.5
                                        bx = px + t * self.dx
                                        by = py
                                    elif dj != 0:
                                        t = 0.5 if dj > 0 else -0.5
                                        bx = px
                                        by = py + t * dj * self.dy
                                    else:
                                        bx = px + 0.5 * di * self.dx
                                        by = py + 0.5 * dj * self.dy
                                    
                                    bv = boundary_func(np.array([bx]), np.array([by]))[0]
                                    dist = np.sqrt((bx - px) ** 2 + (by - py) ** 2)
                                    neighbors.append((dist, bv))
                    
                    if neighbors:
                        neighbors.sort(key=lambda x: x[0])
                        if len(neighbors) >= 2:
                            d1, v1 = neighbors[0]
                            d2, v2 = neighbors[1]
                            if d1 + d2 > 0:
                                w1 = d2 / (d1 + d2)
                                w2 = d1 / (d1 + d2)
                                interp_val = w1 * v1 + w2 * v2
                                boundary_points.append((j, i))
                                boundary_values_list.append(interp_val)
                        else:
                            boundary_points.append((j, i))
                            boundary_values_list.append(neighbors[0][1])
        
        if boundary_points:
            self._interp_boundary_indices = np.array(boundary_points)
            self._interp_boundary_weights = np.array(boundary_values_list)
            
            for idx, (j, i) in enumerate(boundary_points):
                self.boundary_mask[j, i] = True
                self.boundary_values[j, i] = boundary_values_list[idx]
                self.u[j, i] = boundary_values_list[idx]
        
        print(f"Set up {len(boundary_points)} linear interpolation boundary points")

    def _apply_interp_boundary(self):
        if self._interp_boundary_indices is not None and len(self._interp_boundary_indices) > 0:
            for idx, (j, i) in enumerate(self._interp_boundary_indices):
                if self.mask[j, i]:
                    self.u[j, i] = self._interp_boundary_weights[idx]

    def jacobi_step(self) -> float:
        u_new = np.copy(self.u)
        interior = ~self.boundary_mask & self.mask
        
        u_new_interior = np.zeros_like(self.u[1:-1, 1:-1])
        count = np.zeros_like(self.u[1:-1, 1:-1])
        
        interior_mask = interior[1:-1, 1:-1]
        
        for dj, di in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            neighbor_vals = self.u[1+dj:self.ny-1+dj, 1+di:self.nx-1+di]
            neighbor_mask = self.mask[1+dj:self.ny-1+dj, 1+di:self.nx-1+di]
            valid = neighbor_mask & interior_mask
            u_new_interior[valid] += neighbor_vals[valid]
            count[valid] += 1
        
        valid_count = count > 0
        u_new_interior[valid_count] /= count[valid_count]
        u_new[1:-1, 1:-1][interior_mask & valid_count] = u_new_interior[interior_mask & valid_count]
        
        residual = 0.0
        if np.any(interior):
            residual = np.max(np.abs(u_new[interior] - self.u[interior]))
            self.u[interior] = u_new[interior]
        
        self._apply_interp_boundary()
        return residual

    def gauss_seidel_step(self) -> float:
        max_residual = 0.0
        interior = ~self.boundary_mask & self.mask
        
        for j in range(1, self.ny - 1):
            for i in range(1, self.nx - 1):
                if interior[j, i]:
                    old_val = self.u[j, i]
                    neighbors = []
                    for dj, di in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nj, ni = j + dj, i + di
                        if self.mask[nj, ni]:
                            neighbors.append(self.u[nj, ni])
                    
                    if neighbors:
                        self.u[j, i] = sum(neighbors) / len(neighbors)
                        residual = abs(self.u[j, i] - old_val)
                        if residual > max_residual:
                            max_residual = residual
        
        self._apply_interp_boundary()
        return max_residual

    def sor_step(self, omega: float = 1.8) -> float:
        max_residual = 0.0
        interior = ~self.boundary_mask & self.mask
        
        for j in range(1, self.ny - 1):
            for i in range(1, self.nx - 1):
                if interior[j, i]:
                    old_val = self.u[j, i]
                    neighbors = []
                    for dj, di in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nj, ni = j + dj, i + di
                        if self.mask[nj, ni]:
                            neighbors.append(self.u[nj, ni])
                    
                    if neighbors:
                        new_val = sum(neighbors) / len(neighbors)
                        self.u[j, i] = old_val + omega * (new_val - old_val)
                        residual = abs(self.u[j, i] - old_val)
                        if residual > max_residual:
                            max_residual = residual
        
        self._apply_interp_boundary()
        return max_residual

    def solve(self, method: str = 'jacobi', tol: float = 1e-6, max_iter: int = 10000, 
              omega: float = 1.8, verbose: bool = True, 
              live_plot: bool = False, plot_interval: int = 10) -> Tuple[np.ndarray, bool]:
        self.convergence_history = []
        self.iteration_count = 0
        converged = False
        
        step_funcs = {
            'jacobi': self.jacobi_step,
            'gauss_seidel': self.gauss_seidel_step,
            'sor': lambda: self.sor_step(omega)
        }
        
        if method not in step_funcs:
            raise ValueError(f"Unknown method: {method}. Choose from {list(step_funcs.keys())}")
        
        step_func = step_funcs[method]
        
        if live_plot:
            return self._solve_with_live_plot(step_func, tol, max_iter, verbose, plot_interval)
        
        for i in range(max_iter):
            residual = step_func()
            self.convergence_history.append(residual)
            self.iteration_count += 1
            
            if residual < tol:
                converged = True
                if verbose:
                    print(f"Converged after {i+1} iterations. Residual: {residual:.2e}")
                break
            
            if verbose and (i + 1) % 100 == 0:
                print(f"Iteration {i+1}, Residual: {residual:.2e}")
        
        if not converged and verbose:
            print(f"Did not converge after {max_iter} iterations. Final residual: {residual:.2e}")
        
        return self.u, converged

    def _solve_with_live_plot(self, step_func: Callable, tol: float, max_iter: int, 
                               verbose: bool, plot_interval: int) -> Tuple[np.ndarray, bool]:
        import matplotlib
        matplotlib.use('TkAgg')
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        u_masked = self.get_solution()
        im = ax1.imshow(u_masked, cmap='viridis', origin='lower',
                       extent=[0, (self.nx-1)*self.dx, 0, (self.ny-1)*self.dy])
        plt.colorbar(im, ax=ax1, label='Temperature')
        ax1.set_xlabel('x')
        ax1.set_ylabel('y')
        ax1.set_title('Temperature Distribution')
        
        line, = ax2.semilogy([], [])
        ax2.set_xlabel('Iteration')
        ax2.set_ylabel('Max Residual')
        ax2.grid(True, alpha=0.3)
        ax2.set_title('Convergence (Live)')
        
        plt.ion()
        plt.show()
        
        converged = False
        residual_history = []
        
        for i in range(max_iter):
            residual = step_func()
            residual_history.append(residual)
            self.convergence_history.append(residual)
            self.iteration_count += 1
            
            if i % plot_interval == 0:
                u_masked = self.get_solution()
                im.set_array(u_masked)
                im.set_clim(vmin=np.nanmin(u_masked), vmax=np.nanmax(u_masked))
                
                line.set_data(range(len(residual_history)), residual_history)
                ax2.set_xlim(0, max(100, len(residual_history)))
                if len(residual_history) > 0:
                    ax2.set_ylim(max(1e-10, min(residual_history) * 0.1), 
                                 max(residual_history) * 10)
                
                ax1.set_title(f'Temperature (Iter {i})')
                fig.canvas.draw()
                fig.canvas.flush_events()
            
            if residual < tol:
                converged = True
                if verbose:
                    print(f"Converged after {i+1} iterations. Residual: {residual:.2e}")
                break
            
            if verbose and (i + 1) % 100 == 0:
                print(f"Iteration {i+1}, Residual: {residual:.2e}")
        
        plt.ioff()
        
        return self.u, converged

    def get_solution(self) -> np.ndarray:
        return np.ma.masked_where(~self.mask, self.u)

    def plot_convergence(self, ax: Optional[plt.Axes] = None) -> plt.Axes:
        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 5))
        
        ax.semilogy(self.convergence_history, linewidth=2)
        ax.set_xlabel('Iteration')
        ax.set_ylabel('Max Residual')
        ax.set_title('Convergence History')
        ax.grid(True, alpha=0.3, which='both')
        return ax

    def plot_solution(self, ax: Optional[plt.Axes] = None, cmap: str = 'viridis') -> plt.Axes:
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 8))
        
        u_masked = self.get_solution()
        im = ax.imshow(u_masked, cmap=cmap, origin='lower', 
                       extent=[0, (self.nx-1)*self.dx, 0, (self.ny-1)*self.dy])
        plt.colorbar(im, ax=ax, label='Temperature')
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.set_title('Steady-State Temperature Distribution')
        return ax

    def plot_contour(self, ax: Optional[plt.Axes] = None, levels: int = 20, cmap: str = 'viridis') -> plt.Axes:
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 8))
        
        x = np.linspace(0, (self.nx - 1) * self.dx, self.nx)
        y = np.linspace(0, (self.ny - 1) * self.dy, self.ny)
        X, Y = np.meshgrid(x, y)
        
        u_masked = np.ma.masked_where(~self.mask, self.u)
        contour = ax.contourf(X, Y, u_masked, levels=levels, cmap=cmap)
        plt.colorbar(contour, ax=ax, label='Temperature')
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.set_title('Temperature Contour Plot')
        ax.set_aspect('equal')
        return ax


class MultiGridLaplaceSolver(LaplaceSolver):
    def __init__(self, nx: int, ny: int, dx: float = 1.0, dy: float = 1.0, 
                 n_levels: Optional[int] = None, min_coarse_size: int = 3):
        super().__init__(nx, ny, dx, dy)
        
        self.min_coarse_size = min_coarse_size
        self.n_levels = self._compute_adaptive_levels(n_levels)
        
        self.grids = []
        self.grid_masks = []
        self.grid_dx = []
        self.grid_dy = []
        self._setup_multigrid()
        
        print(f"Adaptive multigrid setup: {self.n_levels} levels")
        print(f"  Grid sizes: {[f'{g.shape[1]}x{g.shape[0]}' for g in self.grids]}")

    def _compute_adaptive_levels(self, n_levels: Optional[int]) -> int:
        if n_levels is not None:
            return max(2, n_levels)
        
        current_nx, current_ny = self.nx, self.ny
        levels = 1
        
        while True:
            next_nx = (current_nx + 1) // 2
            next_ny = (current_ny + 1) // 2
            
            if next_nx < self.min_coarse_size or next_ny < self.min_coarse_size:
                break
            
            if levels >= 10:
                break
            
            current_nx, current_ny = next_nx, next_ny
            levels += 1
        
        return max(2, levels)

    def _setup_multigrid(self):
        current_nx, current_ny = self.nx, self.ny
        current_dx, current_dy = self.dx, self.dy
        
        for level in range(self.n_levels):
            self.grids.append(np.zeros((current_ny, current_nx)))
            self.grid_masks.append(np.ones((current_ny, current_nx), dtype=bool))
            self.grid_dx.append(current_dx)
            self.grid_dy.append(current_dy)
            
            if level < self.n_levels - 1:
                current_nx = max(self.min_coarse_size, (current_nx + 1) // 2)
                current_ny = max(self.min_coarse_size, (current_ny + 1) // 2)
                current_dx *= 2
                current_dy *= 2

    def set_region_mask(self, mask: np.ndarray):
        super().set_region_mask(mask)
        self.grid_masks[0] = self.mask.copy()
        
        for level in range(1, self.n_levels):
            coarse_mask = zoom(self.grid_masks[level-1].astype(float), 0.5, order=0) > 0.5
            self.grid_masks[level] = coarse_mask

    def _restrict(self, fine: np.ndarray, mask: np.ndarray) -> np.ndarray:
        coarse_ny = (fine.shape[0] + 1) // 2
        coarse_nx = (fine.shape[1] + 1) // 2
        coarse = np.zeros((coarse_ny, coarse_nx))
        
        for j in range(coarse_ny):
            for i in range(coarse_nx):
                fj, fi = 2 * j, 2 * i
                count = 0
                val = 0.0
                
                for dj in [0, 1]:
                    for di in [0, 1]:
                        if (fj + dj) < fine.shape[0] and (fi + di) < fine.shape[1]:
                            if mask[fj + dj, fi + di]:
                                val += fine[fj + dj, fi + di]
                                count += 1
                
                if count > 0:
                    coarse[j, i] = val / count
        
        return coarse

    def _interpolate(self, coarse: np.ndarray, mask: np.ndarray) -> np.ndarray:
        fine_ny = 2 * coarse.shape[0]
        fine_nx = 2 * coarse.shape[1]
        fine = np.zeros((fine_ny, fine_nx))
        
        for j in range(coarse.shape[0]):
            for i in range(coarse.shape[1]):
                val = coarse[j, i]
                fine[2*j, 2*i] = val
                if 2*j + 1 < fine_ny:
                    fine[2*j+1, 2*i] = val
                if 2*i + 1 < fine_nx:
                    fine[2*j, 2*i+1] = val
                if 2*j + 1 < fine_ny and 2*i + 1 < fine_nx:
                    fine[2*j+1, 2*i+1] = val
        
        return fine

    def _smooth(self, u: np.ndarray, mask: np.ndarray, n_smooth: int = 3, 
                 omega: float = 1.8) -> np.ndarray:
        ny, nx = u.shape
        boundary_mask = np.zeros_like(mask)
        boundary_mask[0, :] = True
        boundary_mask[-1, :] = True
        boundary_mask[:, 0] = True
        boundary_mask[:, -1] = True
        
        for _ in range(n_smooth):
            for j in range(1, ny - 1):
                for i in range(1, nx - 1):
                    if mask[j, i] and not boundary_mask[j, i]:
                        neighbors = []
                        for dj, di in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nj, ni = j + dj, i + di
                            if mask[nj, ni]:
                                neighbors.append(u[nj, ni])
                        if neighbors:
                            new_val = sum(neighbors) / len(neighbors)
                            u[j, i] = u[j, i] + omega * (new_val - u[j, i])
        return u

    def _compute_residual(self, u: np.ndarray, mask: np.ndarray) -> np.ndarray:
        residual = np.zeros_like(u)
        for j in range(1, u.shape[0] - 1):
            for i in range(1, u.shape[1] - 1):
                if mask[j, i]:
                    neighbors = []
                    for dj, di in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nj, ni = j + dj, i + di
                        if mask[nj, ni]:
                            neighbors.append(u[nj, ni])
                    if neighbors:
                        laplacian = sum(neighbors) - len(neighbors) * u[j, i]
                        residual[j, i] = -laplacian
        return residual

    def _v_cycle(self, level: int, u: np.ndarray, mask: np.ndarray, 
                 boundary_vals: np.ndarray, n_smooth: int = 3) -> np.ndarray:
        if level == self.n_levels - 1:
            return self._smooth(u, mask, n_smooth * 2)
        
        u = self._smooth(u, mask, n_smooth)
        
        residual = self._compute_residual(u, mask)
        coarse_mask = self.grid_masks[level + 1]
        coarse_residual = self._restrict(residual, mask)
        coarse_correction = np.zeros_like(coarse_residual)
        
        coarse_boundary = np.zeros_like(coarse_correction)
        coarse_correction = self._v_cycle(level + 1, coarse_correction, coarse_mask, 
                                          coarse_boundary, n_smooth)
        
        fine_correction = self._interpolate(coarse_correction, mask)
        if fine_correction.shape == u.shape:
            u = u + fine_correction
        
        u = self._smooth(u, mask, n_smooth)
        
        return u

    def solve_multigrid(self, tol: float = 1e-6, max_iter: int = 100, 
                        n_smooth: int = 3, verbose: bool = True,
                        live_plot: bool = False, plot_interval: int = 2) -> Tuple[np.ndarray, bool]:
        self.convergence_history = []
        self.iteration_count = 0
        converged = False
        
        u = self.u.copy()
        mask = self.mask.copy()
        
        if live_plot:
            return self._solve_mg_with_live_plot(u, mask, tol, max_iter, n_smooth, verbose, plot_interval)
        
        for iteration in range(max_iter):
            u_old = u.copy()
            u = self._v_cycle(0, u, mask, self.boundary_values, n_smooth)
            
            residual = np.max(np.abs(u[mask] - u_old[mask]))
            self.convergence_history.append(residual)
            self.iteration_count += 1
            
            if residual < tol:
                converged = True
                if verbose:
                    print(f"Multigrid converged after {iteration+1} V-cycles. Residual: {residual:.2e}")
                break
            
            if verbose and (iteration + 1) % 10 == 0:
                print(f"V-cycle {iteration+1}, Residual: {residual:.2e}")
        
        self.u = u
        
        if not converged and verbose:
            print(f"Multigrid did not converge after {max_iter} V-cycles. Final residual: {residual:.2e}")
        
        return self.u, converged

    def _solve_mg_with_live_plot(self, u: np.ndarray, mask: np.ndarray, tol: float, 
                                  max_iter: int, n_smooth: int, verbose: bool,
                                  plot_interval: int) -> Tuple[np.ndarray, bool]:
        import matplotlib
        matplotlib.use('TkAgg')
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        u_masked = np.ma.masked_where(~mask, u)
        im = ax1.imshow(u_masked, cmap='viridis', origin='lower',
                       extent=[0, (self.nx-1)*self.dx, 0, (self.ny-1)*self.dy])
        plt.colorbar(im, ax=ax1, label='Temperature')
        ax1.set_xlabel('x')
        ax1.set_ylabel('y')
        ax1.set_title('Temperature Distribution (Multigrid)')
        
        line, = ax2.semilogy([], [], 'o-', markersize=3, linewidth=1.5)
        ax2.set_xlabel('V-cycle')
        ax2.set_ylabel('Max Residual')
        ax2.grid(True, alpha=0.3, which='both')
        ax2.set_title('Multigrid Convergence (Live)')
        
        plt.ion()
        plt.show()
        
        converged = False
        residual_history = []
        
        for iteration in range(max_iter):
            u_old = u.copy()
            u = self._v_cycle(0, u, mask, self.boundary_values, n_smooth)
            
            residual = np.max(np.abs(u[mask] - u_old[mask]))
            residual_history.append(residual)
            self.convergence_history.append(residual)
            self.iteration_count += 1
            
            if iteration % plot_interval == 0:
                u_masked = np.ma.masked_where(~mask, u)
                im.set_array(u_masked)
                im.set_clim(vmin=np.nanmin(u_masked), vmax=np.nanmax(u_masked))
                
                line.set_data(range(len(residual_history)), residual_history)
                ax2.set_xlim(0, max(10, len(residual_history)))
                if len(residual_history) > 0:
                    ax2.set_ylim(max(1e-10, min(residual_history) * 0.1), 
                                 max(residual_history) * 10)
                
                ax1.set_title(f'Temperature (V-cycle {iteration})')
                fig.canvas.draw()
                fig.canvas.flush_events()
            
            if residual < tol:
                converged = True
                if verbose:
                    print(f"Multigrid converged after {iteration+1} V-cycles. Residual: {residual:.2e}")
                break
            
            if verbose and (iteration + 1) % 10 == 0:
                print(f"V-cycle {iteration+1}, Residual: {residual:.2e}")
        
        self.u = u
        plt.ioff()
        
        return self.u, converged


class AnimatedLaplaceSolver(LaplaceSolver):
    def __init__(self, nx: int, ny: int, dx: float = 1.0, dy: float = 1.0):
        super().__init__(nx, ny, dx, dy)
        self.snapshots = []

    def solve_with_animation(self, method: str = 'jacobi', tol: float = 1e-6, 
                             max_iter: int = 10000, snapshot_interval: int = 10,
                             omega: float = 1.8) -> FuncAnimation:
        self.snapshots = []
        self.convergence_history = []
        self.iteration_count = 0
        
        step_funcs = {
            'jacobi': self.jacobi_step,
            'gauss_seidel': self.gauss_seidel_step,
            'sor': lambda: self.sor_step(omega)
        }
        
        if method not in step_funcs:
            raise ValueError(f"Unknown method: {method}. Choose from {list(step_funcs.keys())}")
        
        step_func = step_funcs[method]
        
        for i in range(max_iter):
            residual = step_func()
            self.convergence_history.append(residual)
            self.iteration_count += 1
            
            if i % snapshot_interval == 0:
                self.snapshots.append(self.get_solution().copy())
            
            if residual < tol:
                self.snapshots.append(self.get_solution().copy())
                print(f"Converged after {i+1} iterations.")
                break
        
        return self._create_animation()

    def _create_animation(self) -> FuncAnimation:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        x = np.linspace(0, (self.nx - 1) * self.dx, self.nx)
        y = np.linspace(0, (self.ny - 1) * self.dy, self.ny)
        
        im = ax1.imshow(self.snapshots[0], cmap='viridis', origin='lower',
                        extent=[0, (self.nx-1)*self.dx, 0, (self.ny-1)*self.dy],
                        animated=True)
        plt.colorbar(im, ax=ax1, label='Temperature')
        ax1.set_xlabel('x')
        ax1.set_ylabel('y')
        
        line, = ax2.semilogy([], [], linewidth=2)
        ax2.set_xlabel('Iteration')
        ax2.set_ylabel('Max Residual')
        ax2.grid(True, alpha=0.3, which='both')
        ax2.set_xlim(0, len(self.convergence_history))
        if len(self.convergence_history) > 0:
            ax2.set_ylim(min(self.convergence_history) * 0.1, max(self.convergence_history) * 10)
        
        title = fig.suptitle('Iteration 0')
        
        def update(frame):
            im.set_array(self.snapshots[frame])
            im.set_clim(vmin=np.nanmin(self.snapshots[frame]), 
                       vmax=np.nanmax(self.snapshots[frame]))
            
            current_iter = frame * 10
            line.set_data(range(0, min(current_iter + 1, len(self.convergence_history))), 
                         self.convergence_history[:current_iter + 1])
            title.set_text(f'Iteration {current_iter}')
            return im, line, title
        
        ani = FuncAnimation(fig, update, frames=len(self.snapshots), 
                            interval=100, blit=True)
        plt.tight_layout()
        return ani


def example_rectangular_domain():
    print("=== Example 1: Rectangular Domain ===")
    
    nx, ny = 50, 50
    solver = LaplaceSolver(nx, ny)
    
    def boundary_temp(x, y):
        temp = np.zeros_like(x)
        temp[y == 0] = 100
        temp[y == (ny-1)] = 0
        return temp
    
    solver.set_dirichlet_boundary(boundary_temp)
    u, converged = solver.solve(method='sor', tol=1e-6, max_iter=5000, omega=1.8, verbose=False)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    solver.plot_contour(ax=ax1)
    solver.plot_convergence(ax=ax2)
    plt.tight_layout()
    plt.savefig('example_rectangular.png', dpi=150)
    plt.close()
    
    print(f"Converged: {converged}, Iterations: {solver.iteration_count}")
    print("Saved: example_rectangular.png")


def example_circular_domain_linear_interp():
    print("\n=== Example 2: Circular Domain with Linear Interpolation Boundary ===")
    
    nx, ny = 80, 80
    solver = LaplaceSolver(nx, ny)
    
    center_x, center_y = (nx-1)/2, (ny-1)/2
    radius = 30
    solver.set_circular_region(center_x, center_y, radius)
    
    def circular_boundary(x, y):
        angle = np.arctan2(y - center_y, x - center_x)
        return 50 + 50 * np.cos(angle)
    
    solver.setup_linear_interpolation_boundary(circular_boundary, boundary_distance=2.0)
    
    u, converged = solver.solve(method='sor', tol=1e-6, max_iter=5000, omega=1.7, verbose=False)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    solver.plot_contour(ax=ax1)
    solver.plot_convergence(ax=ax2)
    
    boundary_x = center_x + radius * np.cos(np.linspace(0, 2*np.pi, 100))
    boundary_y = center_y + radius * np.sin(np.linspace(0, 2*np.pi, 100))
    ax1.plot(boundary_x, boundary_y, 'r--', linewidth=2, label='True Boundary')
    ax1.legend()
    
    plt.tight_layout()
    plt.savefig('example_circular_linear_interp.png', dpi=150)
    plt.close()
    
    print(f"Converged: {converged}, Iterations: {solver.iteration_count}")
    print("Saved: example_circular_linear_interp.png")


def example_adaptive_multigrid():
    print("\n=== Example 3: Adaptive Multigrid ===")
    
    for size in [65, 129, 257]:
        nx, ny = size, size
        print(f"\nTesting {nx}x{ny} grid:")
        
        solver_mg = MultiGridLaplaceSolver(nx, ny)
        
        def boundary_temp(x, y):
            temp = np.zeros_like(x)
            temp[y == 0] = 100
            temp[y == (ny-1)] = 0
            return temp
        
        solver_mg.set_dirichlet_boundary(boundary_temp)
        u_mg, converged_mg = solver_mg.solve_multigrid(
            tol=1e-6, max_iter=100, n_smooth=3, verbose=False
        )
        
        print(f"  Levels: {solver_mg.n_levels}, V-cycles: {solver_mg.iteration_count}")
        print(f"  Final residual: {solver_mg.convergence_history[-1]:.2e}")


def example_live_convergence():
    print("\n=== Example 4: Live Convergence Plot ===")
    print("Note: This example requires a display and may not work in all environments")
    print("Skipping live plot example in headless mode...")
    
    nx, ny = 100, 100
    solver = MultiGridLaplaceSolver(nx, ny)
    
    def boundary_temp(x, y):
        temp = np.zeros_like(x)
        temp[y == 0] = 100
        temp[y == (ny-1)] = 0
        temp[x == 0] = 50 + 50 * np.sin(np.pi * y[y == 0] / (ny-1))
        return temp
    
    solver.set_dirichlet_boundary(boundary_temp)
    u, converged = solver.solve_multigrid(tol=1e-6, max_iter=50, verbose=False)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    solver.plot_contour(ax=ax1)
    solver.plot_convergence(ax=ax2)
    
    ax1.set_title(f'Adaptive Multigrid: {solver.n_levels} levels')
    ax2.set_title(f'Convergence: {solver.iteration_count} V-cycles')
    
    plt.tight_layout()
    plt.savefig('example_multigrid_convergence.png', dpi=150)
    plt.close()
    
    print(f"Converged: {converged}, V-cycles: {solver.iteration_count}")
    print("Saved: example_multigrid_convergence.png")


def example_annular_linear_interp():
    print("\n=== Example 5: Annular Domain with Linear Interpolation ===")
    
    nx, ny = 100, 100
    solver = LaplaceSolver(nx, ny)
    
    center_x, center_y = (nx-1)/2, (ny-1)/2
    inner_radius = 20
    outer_radius = 45
    solver.set_annular_region(center_x, center_y, inner_radius, outer_radius)
    
    def inner_boundary(x, y):
        return 100.0
    
    def outer_boundary(x, y):
        angle = np.arctan2(y - center_y, x - center_x)
        return 20 + 30 * np.cos(2 * angle)
    
    def combined_boundary(x, y):
        dist = np.sqrt((x - center_x)**2 + (y - center_y)**2)
        inner_dist = np.abs(dist - inner_radius)
        outer_dist = np.abs(dist - outer_radius)
        return np.where(inner_dist < outer_dist, inner_boundary(x, y), outer_boundary(x, y))
    
    solver.setup_linear_interpolation_boundary(combined_boundary, boundary_distance=2.0)
    
    u, converged = solver.solve(method='sor', tol=1e-6, max_iter=8000, omega=1.6, verbose=False)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    solver.plot_contour(ax=ax1, levels=25)
    solver.plot_convergence(ax=ax2)
    
    theta = np.linspace(0, 2*np.pi, 100)
    ax1.plot(center_x + inner_radius * np.cos(theta), 
             center_y + inner_radius * np.sin(theta), 'r--', linewidth=2, label='Inner Boundary')
    ax1.plot(center_x + outer_radius * np.cos(theta), 
             center_y + outer_radius * np.sin(theta), 'b--', linewidth=2, label='Outer Boundary')
    ax1.legend()
    
    plt.tight_layout()
    plt.savefig('example_annular_linear_interp.png', dpi=150)
    plt.close()
    
    print(f"Converged: {converged}, Iterations: {solver.iteration_count}")
    print("Saved: example_annular_linear_interp.png")


if __name__ == "__main__":
    example_rectangular_domain()
    example_circular_domain_linear_interp()
    example_adaptive_multigrid()
    example_live_convergence()
    example_annular_linear_interp()
    print("\nAll examples completed!")
