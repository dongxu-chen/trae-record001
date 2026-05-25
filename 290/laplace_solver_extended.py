import numpy as np
from scipy.ndimage import zoom, distance_transform_edt
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from typing import Optional, Tuple, Dict, Callable, List


class NonUniformGrid:
    def __init__(self, x_coords: np.ndarray, y_coords: np.ndarray):
        self.x_coords = np.array(x_coords, dtype=float)
        self.y_coords = np.array(y_coords, dtype=float)
        self.nx = len(self.x_coords)
        self.ny = len(self.y_coords)
        
        self.dx_right = np.diff(self.x_coords)
        self.dx_left = np.diff(self.x_coords)
        self.dy_bottom = np.diff(self.y_coords)
        self.dy_top = np.diff(self.y_coords)
        
        self.dx_e = np.zeros(self.nx)
        self.dx_w = np.zeros(self.nx)
        self.dy_n = np.zeros(self.ny)
        self.dy_s = np.zeros(self.ny)
        
        self.dx_e[:-1] = self.dx_right
        self.dx_e[-1] = self.dx_right[-1]
        self.dx_w[1:] = self.dx_left
        self.dx_w[0] = self.dx_left[0]
        
        self.dy_n[:-1] = self.dy_bottom
        self.dy_n[-1] = self.dy_bottom[-1]
        self.dy_s[1:] = self.dy_top
        self.dy_s[0] = self.dy_top[0]
        
        self.X, self.Y = np.meshgrid(self.x_coords, self.y_coords)

    @classmethod
    def create_uniform(cls, nx: int, ny: int, x_min: float = 0, x_max: float = 1,
                       y_min: float = 0, y_max: float = 1):
        x_coords = np.linspace(x_min, x_max, nx)
        y_coords = np.linspace(y_min, y_max, ny)
        return cls(x_coords, y_coords)

    @classmethod
    def create_stretched(cls, nx: int, ny: int, x_min: float = 0, x_max: float = 1,
                         y_min: float = 0, y_max: float = 1, 
                         stretch_x: float = 1, stretch_y: float = 1,
                         center_x: Optional[float] = None, center_y: Optional[float] = None):
        if center_x is None:
            center_x = (x_min + x_max) / 2
        if center_y is None:
            center_y = (y_min + y_max) / 2
        
        x_uniform = np.linspace(0, 1, nx)
        x_normalized = 2 * (x_uniform - 0.5)
        x_stretched = np.tanh(stretch_x * x_normalized) / np.tanh(stretch_x)
        x_coords = center_x + (x_max - x_min) / 2 * x_stretched
        
        y_uniform = np.linspace(0, 1, ny)
        y_normalized = 2 * (y_uniform - 0.5)
        y_stretched = np.tanh(stretch_y * y_normalized) / np.tanh(stretch_y)
        y_coords = center_y + (y_max - y_min) / 2 * y_stretched
        
        return cls(x_coords, y_coords)

    @classmethod
    def create_with_refinement(cls, nx: int, ny: int, x_min: float = 0, x_max: float = 1,
                               y_min: float = 0, y_max: float = 1,
                               refine_regions: Optional[List[Tuple[float, float, float, float, float]]] = None):
        x_coords = np.linspace(x_min, x_max, nx)
        y_coords = np.linspace(y_min, y_max, ny)
        
        if refine_regions is not None:
            for (x1, x2, y1, y2, factor) in refine_regions:
                x_mask = (x_coords >= x1) & (x_coords <= x2)
                x_center = (x1 + x2) / 2
                x_width = (x2 - x1) / 2
                
                t = np.clip((x_coords[x_mask] - x_center) / x_width, -1, 1)
                refinement = 1 + (factor - 1) * (1 - np.abs(t))
                
                new_x = x_center + x_width * np.sign(t) * (np.abs(t) ** refinement)
                x_coords[x_mask] = np.sort(new_x)
                
                y_mask = (y_coords >= y1) & (y_coords <= y2)
                y_center = (y1 + y2) / 2
                y_width = (y2 - y1) / 2
                
                t = np.clip((y_coords[y_mask] - y_center) / y_width, -1, 1)
                refinement = 1 + (factor - 1) * (1 - np.abs(t))
                
                new_y = y_center + y_width * np.sign(t) * (np.abs(t) ** refinement)
                y_coords[y_mask] = np.sort(new_y)
        
        return cls(np.unique(x_coords), np.unique(y_coords))

    def get_cell_volumes(self) -> np.ndarray:
        vol = np.zeros((self.ny, self.nx))
        for j in range(self.ny):
            for i in range(self.nx):
                dx = (self.dx_e[i] + self.dx_w[i]) / 2
                dy = (self.dy_n[j] + self.dy_s[j]) / 2
                vol[j, i] = dx * dy
        return vol

    def plot_grid(self, ax: Optional[plt.Axes] = None) -> plt.Axes:
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 8))
        
        for x in self.x_coords:
            ax.axvline(x, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
        for y in self.y_coords:
            ax.axhline(y, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
        
        ax.set_xlim(self.x_coords[0], self.x_coords[-1])
        ax.set_ylim(self.y_coords[0], self.y_coords[-1])
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.set_title('Non-Uniform Grid')
        ax.set_aspect('equal')
        return ax


class TransientHeatSolver:
    def __init__(self, grid: NonUniformGrid):
        self.grid = grid
        self.nx = grid.nx
        self.ny = grid.ny
        
        self.u = np.zeros((self.ny, self.nx))
        self.mask = np.ones((self.ny, self.nx), dtype=bool)
        
        self.rho = np.ones((self.ny, self.nx))
        self.cp = np.ones((self.ny, self.nx))
        self.k = np.ones((self.ny, self.nx))
        
        self.source = np.zeros((self.ny, self.nx))
        
        self.boundary_mask = np.zeros((self.ny, self.nx), dtype=bool)
        self.boundary_type = {}
        self.boundary_params = {}
        
        self.time_history = []
        self.temperature_snapshots = []
        self.current_time = 0.0

    def set_material_properties(self, rho: Optional[np.ndarray] = None, 
                                cp: Optional[np.ndarray] = None, 
                                k: Optional[np.ndarray] = None):
        if rho is not None:
            self.rho = np.broadcast_to(rho, (self.ny, self.nx)).copy()
        if cp is not None:
            self.cp = np.broadcast_to(cp, (self.ny, self.nx)).copy()
        if k is not None:
            self.k = np.broadcast_to(k, (self.ny, self.nx)).copy()

    def set_heat_source(self, source: np.ndarray):
        self.source = np.broadcast_to(source, (self.ny, self.nx)).copy()

    def set_region_mask(self, mask: np.ndarray):
        self.mask = mask.astype(bool)
        self.u[~self.mask] = np.nan

    def set_dirichlet_boundary(self, mask: np.ndarray, temperature: float):
        self.boundary_mask = self.boundary_mask | mask
        for j in range(self.ny):
            for i in range(self.nx):
                if mask[j, i]:
                    self.boundary_type[(j, i)] = 'dirichlet'
                    self.boundary_params[(j, i)] = {'T': temperature}
                    self.u[j, i] = temperature

    def set_convection_boundary(self, mask: np.ndarray, h: float, T_ambient: float):
        self.boundary_mask = self.boundary_mask | mask
        for j in range(self.ny):
            for i in range(self.nx):
                if mask[j, i]:
                    self.boundary_type[(j, i)] = 'convection'
                    self.boundary_params[(j, i)] = {'h': h, 'T_ambient': T_ambient}

    def set_radiation_boundary(self, mask: np.ndarray, epsilon: float, T_surroundings: float, 
                                sigma: float = 5.67e-8):
        self.boundary_mask = self.boundary_mask | mask
        for j in range(self.ny):
            for i in range(self.nx):
                if mask[j, i]:
                    self.boundary_type[(j, i)] = 'radiation'
                    self.boundary_params[(j, i)] = {'epsilon': epsilon, 'T_sur': T_surroundings, 'sigma': sigma}

    def set_mixed_boundary(self, mask: np.ndarray, h: float, T_ambient: float,
                           epsilon: float, T_surroundings: float, sigma: float = 5.67e-8):
        self.boundary_mask = self.boundary_mask | mask
        for j in range(self.ny):
            for i in range(self.nx):
                if mask[j, i]:
                    self.boundary_type[(j, i)] = 'mixed'
                    self.boundary_params[(j, i)] = {
                        'h': h, 'T_ambient': T_ambient,
                        'epsilon': epsilon, 'T_sur': T_surroundings, 'sigma': sigma
                    }

    def _compute_derivative_coefficients(self, j: int, i: int) -> Tuple[float, float, float, float, float, float]:
        dx_e = self.grid.dx_e[i]
        dx_w = self.grid.dx_w[i]
        dy_n = self.grid.dy_n[j]
        dy_s = self.grid.dy_s[j]
        
        a_w = 2.0 / (dx_w * (dx_e + dx_w))
        a_e = 2.0 / (dx_e * (dx_e + dx_w))
        a_p = -2.0 / (dx_e * dx_w)
        b_s = 2.0 / (dy_s * (dy_n + dy_s))
        b_n = 2.0 / (dy_n * (dy_n + dy_s))
        b_p = -2.0 / (dy_n * dy_s)
        
        return a_w, a_e, a_p, b_s, b_n, b_p

    def _apply_boundary_conditions(self, u: np.ndarray, dt: float) -> np.ndarray:
        u_new = u.copy()
        
        for (j, i), btype in self.boundary_type.items():
            if not self.mask[j, i]:
                continue
                
            params = self.boundary_params[(j, i)]
            
            if btype == 'dirichlet':
                u_new[j, i] = params['T']
                
            elif btype == 'convection':
                h, T_amb = params['h'], params['T_ambient']
                k_avg = self.k[j, i]
                
                neighbors = []
                dists = []
                for dj, di in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nj, ni = j + dj, i + di
                    if 0 <= nj < self.ny and 0 <= ni < self.nx and self.mask[nj, ni]:
                        neighbors.append(u[nj, ni])
                        if dj != 0:
                            dists.append((self.grid.dy_n[j] if dj > 0 else self.grid.dy_s[j]))
                        else:
                            dists.append((self.grid.dx_e[i] if di > 0 else self.grid.dx_w[i]))
                
                if neighbors:
                    avg_dist = np.mean(dists)
                    k_grad = k_avg / avg_dist
                    u_new[j, i] = (k_grad * np.mean(neighbors) + h * T_amb) / (k_grad + h)
                
            elif btype == 'radiation':
                eps, T_sur, sigma = params['epsilon'], params['T_sur'], params['sigma']
                k_avg = self.k[j, i]
                
                neighbors = []
                dists = []
                for dj, di in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nj, ni = j + dj, i + di
                    if 0 <= nj < self.ny and 0 <= ni < self.nx and self.mask[nj, ni]:
                        neighbors.append(u[nj, ni])
                        if dj != 0:
                            dists.append((self.grid.dy_n[j] if dj > 0 else self.grid.dy_s[j]))
                        else:
                            dists.append((self.grid.dx_e[i] if di > 0 else self.grid.dx_w[i]))
                
                if neighbors:
                    avg_dist = np.mean(dists)
                    k_grad = k_avg / avg_dist
                    T_old = u[j, i]
                    rad_flux = eps * sigma * (T_old**4 - T_sur**4)
                    u_new[j, i] = np.mean(neighbors) - (rad_flux / k_grad) * avg_dist
                
            elif btype == 'mixed':
                h, T_amb = params['h'], params['T_ambient']
                eps, T_sur, sigma = params['epsilon'], params['T_sur'], params['sigma']
                k_avg = self.k[j, i]
                
                neighbors = []
                dists = []
                for dj, di in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nj, ni = j + dj, i + di
                    if 0 <= nj < self.ny and 0 <= ni < self.nx and self.mask[nj, ni]:
                        neighbors.append(u[nj, ni])
                        if dj != 0:
                            dists.append((self.grid.dy_n[j] if dj > 0 else self.grid.dy_s[j]))
                        else:
                            dists.append((self.grid.dx_e[i] if di > 0 else self.grid.dx_w[i]))
                
                if neighbors:
                    avg_dist = np.mean(dists)
                    k_grad = k_avg / avg_dist
                    T_old = u[j, i]
                    rad_flux = eps * sigma * (T_old**4 - T_sur**4)
                    
                    conv_contrib = h * T_amb
                    rad_contrib = k_grad * np.mean(neighbors) - rad_flux * avg_dist
                    total_coeff = k_grad + h
                    
                    u_new[j, i] = (h * T_amb + k_grad * np.mean(neighbors) - rad_flux * avg_dist) / (h + k_grad)
        
        return u_new

    def step_explicit(self, dt: float) -> float:
        u_new = np.copy(self.u)
        
        rho_cp = self.rho * self.cp
        cell_volumes = self.grid.get_cell_volumes()
        
        interior = ~self.boundary_mask & self.mask
        
        for j in range(1, self.ny - 1):
            for i in range(1, self.nx - 1):
                if interior[j, i]:
                    a_w, a_e, a_p, b_s, b_n, b_p = self._compute_derivative_coefficients(j, i)
                    
                    k_w = 0.5 * (self.k[j, i] + self.k[j, max(0, i-1)])
                    k_e = 0.5 * (self.k[j, i] + self.k[j, min(self.nx-1, i+1)])
                    k_s = 0.5 * (self.k[j, i] + self.k[max(0, j-1), i])
                    k_n = 0.5 * (self.k[j, i] + self.k[min(self.ny-1, j+1), i])
                    
                    laplacian = (
                        k_w * a_w * self.u[j, max(0, i-1)] +
                        k_e * a_e * self.u[j, min(self.nx-1, i+1)] +
                        k_s * b_s * self.u[max(0, j-1), i] +
                        k_n * b_n * self.u[min(self.ny-1, j+1), i] +
                        (k_w + k_e) * a_p * self.u[j, i] +
                        (k_s + k_n) * b_p * self.u[j, i]
                    )
                    
                    dT_dt = (laplacian + self.source[j, i]) / (rho_cp[j, i] * cell_volumes[j, i])
                    u_new[j, i] = self.u[j, i] + dt * dT_dt
        
        u_new = self._apply_boundary_conditions(u_new, dt)
        
        max_change = np.max(np.abs(u_new[interior] - self.u[interior]))
        self.u = u_new
        self.current_time += dt
        
        return max_change

    def step_implicit(self, dt: float, max_iter: int = 100, tol: float = 1e-6) -> float:
        rho_cp = self.rho * self.cp
        cell_volumes = self.grid.get_cell_volumes()
        interior = ~self.boundary_mask & self.mask
        
        u_old = self.u.copy()
        
        for iteration in range(max_iter):
            u_new = np.copy(self.u)
            
            for j in range(1, self.ny - 1):
                for i in range(1, self.nx - 1):
                    if interior[j, i]:
                        a_w, a_e, a_p, b_s, b_n, b_p = self._compute_derivative_coefficients(j, i)
                        
                        k_w = 0.5 * (self.k[j, i] + self.k[j, max(0, i-1)])
                        k_e = 0.5 * (self.k[j, i] + self.k[j, min(self.nx-1, i+1)])
                        k_s = 0.5 * (self.k[j, i] + self.k[max(0, j-1), i])
                        k_n = 0.5 * (self.k[j, i] + self.k[min(self.ny-1, j+1), i])
                        
                        neighbor_sum = (
                            k_w * a_w * self.u[j, max(0, i-1)] +
                            k_e * a_e * self.u[j, min(self.nx-1, i+1)] +
                            k_s * b_s * self.u[max(0, j-1), i] +
                            k_n * b_n * self.u[min(self.ny-1, j+1), i]
                        )
                        
                        coeff_p = (k_w + k_e) * a_p + (k_s + k_n) * b_p
                        denom = rho_cp[j, i] * cell_volumes[j, i] / dt - coeff_p
                        
                        if abs(denom) > 1e-10:
                            u_new[j, i] = (
                                rho_cp[j, i] * cell_volumes[j, i] / dt * u_old[j, i] +
                                neighbor_sum + self.source[j, i]
                            ) / denom
            
            u_new = self._apply_boundary_conditions(u_new, dt)
            
            max_change = np.max(np.abs(u_new[interior] - self.u[interior]))
            self.u = u_new
            
            if max_change < tol:
                break
        
        self.current_time += dt
        return max_change

    def solve_transient(self, total_time: float, dt: float, method: str = 'explicit',
                        snapshot_interval: int = 10, verbose: bool = True) -> np.ndarray:
        self.time_history = [0.0]
        self.temperature_snapshots = [self.u.copy()]
        self.current_time = 0.0
        
        n_steps = int(total_time / dt)
        step_func = self.step_explicit if method == 'explicit' else self.step_implicit
        
        for step in range(n_steps):
            max_change = step_func(dt)
            
            if step % snapshot_interval == 0:
                self.time_history.append(self.current_time)
                self.temperature_snapshots.append(self.u.copy())
            
            if verbose and step % 100 == 0:
                avg_temp = np.mean(self.u[self.mask])
                print(f"Step {step}/{n_steps}, Time: {self.current_time:.4f}s, "
                      f"Avg Temp: {avg_temp:.2f}, Max Change: {max_change:.4e}")
        
        return np.array(self.temperature_snapshots)

    def get_solution(self) -> np.ndarray:
        return np.ma.masked_where(~self.mask, self.u)

    def plot_temperature(self, ax: Optional[plt.Axes] = None, cmap: str = 'viridis') -> plt.Axes:
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 8))
        
        u_masked = self.get_solution()
        im = ax.pcolormesh(self.grid.x_coords, self.grid.y_coords, u_masked, 
                          cmap=cmap, shading='auto')
        plt.colorbar(im, ax=ax, label='Temperature (K)')
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.set_title(f'Temperature Distribution (t = {self.current_time:.2f}s)')
        ax.set_aspect('equal')
        return ax

    def plot_time_series(self, points: List[Tuple[int, int]], ax: Optional[plt.Axes] = None) -> plt.Axes:
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))
        
        for (j, i) in points:
            temps = [snap[j, i] for snap in self.temperature_snapshots]
            ax.plot(self.time_history, temps, label=f'Point ({i}, {j})')
        
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Temperature (K)')
        ax.set_title('Temperature vs Time')
        ax.legend()
        ax.grid(True, alpha=0.3)
        return ax

    def create_animation(self, interval: int = 100) -> FuncAnimation:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        u_masked = np.ma.masked_where(~self.mask, self.temperature_snapshots[0])
        im = ax1.pcolormesh(self.grid.x_coords, self.grid.y_coords, u_masked, 
                           cmap='viridis', shading='auto')
        plt.colorbar(im, ax=ax1, label='Temperature (K)')
        ax1.set_xlabel('x')
        ax1.set_ylabel('y')
        ax1.set_aspect('equal')
        
        avg_temps = [np.mean(snap[self.mask]) for snap in self.temperature_snapshots]
        line, = ax2.plot([], [])
        ax2.set_xlabel('Time (s)')
        ax2.set_ylabel('Average Temperature (K)')
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim(0, max(self.time_history))
        ax2.set_ylim(min(avg_temps) * 0.9, max(avg_temps) * 1.1)
        
        title = fig.suptitle(f'Time = {self.time_history[0]:.4f}s')
        
        def update(frame):
            u_masked = np.ma.masked_where(~self.mask, self.temperature_snapshots[frame])
            im.set_array(u_masked.ravel())
            im.set_clim(vmin=np.min(u_masked), vmax=np.max(u_masked))
            
            line.set_data(self.time_history[:frame+1], avg_temps[:frame+1])
            title.set_text(f'Time = {self.time_history[frame]:.4f}s')
            return im, line, title
        
        ani = FuncAnimation(fig, update, frames=len(self.temperature_snapshots), 
                           interval=interval, blit=True)
        plt.tight_layout()
        return ani


class AdvancedHeatSolver(TransientHeatSolver):
    def __init__(self, grid: NonUniformGrid):
        super().__init__(grid)
        self.steady_state_residuals = []

    def solve_steady_state(self, max_iter: int = 10000, tol: float = 1e-6, 
                           omega: float = 1.8, verbose: bool = True) -> Tuple[np.ndarray, bool]:
        self.steady_state_residuals = []
        converged = False
        
        rho_cp = self.rho * self.cp
        cell_volumes = self.grid.get_cell_volumes()
        interior = ~self.boundary_mask & self.mask
        
        for iteration in range(max_iter):
            u_old = self.u.copy()
            
            for j in range(1, self.ny - 1):
                for i in range(1, self.nx - 1):
                    if interior[j, i]:
                        a_w, a_e, a_p, b_s, b_n, b_p = self._compute_derivative_coefficients(j, i)
                        
                        k_w = 0.5 * (self.k[j, i] + self.k[j, max(0, i-1)])
                        k_e = 0.5 * (self.k[j, i] + self.k[j, min(self.nx-1, i+1)])
                        k_s = 0.5 * (self.k[j, i] + self.k[max(0, j-1), i])
                        k_n = 0.5 * (self.k[j, i] + self.k[min(self.ny-1, j+1), i])
                        
                        laplacian = (
                            k_w * a_w * self.u[j, max(0, i-1)] +
                            k_e * a_e * self.u[j, min(self.nx-1, i+1)] +
                            k_s * b_s * self.u[max(0, j-1), i] +
                            k_n * b_n * self.u[min(self.ny-1, j+1), i] +
                            (k_w + k_e) * a_p * self.u[j, i] +
                            (k_s + k_n) * b_p * self.u[j, i]
                        )
                        
                        coeff_p = (k_w + k_e) * a_p + (k_s + k_n) * b_p
                        if abs(coeff_p) > 1e-10:
                            new_val = (-laplacian - coeff_p * self.u[j, i] - self.source[j, i]) / coeff_p
                            self.u[j, i] = self.u[j, i] + omega * (new_val - self.u[j, i])
            
            self.u = self._apply_boundary_conditions(self.u, 0)
            
            residual = np.max(np.abs(self.u[interior] - u_old[interior]))
            self.steady_state_residuals.append(residual)
            
            if residual < tol:
                converged = True
                if verbose:
                    print(f"Steady state converged after {iteration+1} iterations. Residual: {residual:.2e}")
                break
            
            if verbose and (iteration + 1) % 100 == 0:
                print(f"Iteration {iteration+1}, Residual: {residual:.2e}")
        
        return self.u, converged

    def plot_steady_convergence(self, ax: Optional[plt.Axes] = None) -> plt.Axes:
        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 5))
        
        ax.semilogy(self.steady_state_residuals, linewidth=2)
        ax.set_xlabel('Iteration')
        ax.set_ylabel('Max Residual')
        ax.set_title('Steady State Convergence')
        ax.grid(True, alpha=0.3, which='both')
        return ax


def example_nonuniform_grid():
    print("=== Example 1: Non-Uniform Grid with Local Refinement ===")
    
    refine_regions = [
        (0.3, 0.7, 0.4, 0.6, 4.0),
    ]
    
    grid = NonUniformGrid.create_with_refinement(
        nx=50, ny=50, x_min=0, x_max=1, y_min=0, y_max=1,
        refine_regions=refine_regions
    )
    
    fig, ax = plt.subplots(figsize=(10, 8))
    grid.plot_grid(ax=ax)
    ax.set_title('Non-Uniform Grid with Center Refinement')
    plt.tight_layout()
    plt.savefig('example_nonuniform_grid.png', dpi=150)
    plt.close()
    
    print(f"Grid size: {grid.nx}x{grid.ny}")
    print("Saved: example_nonuniform_grid.png")
    
    return grid


def example_transient_heating():
    print("\n=== Example 2: Transient Heating with Convection Boundary ===")
    
    grid = NonUniformGrid.create_uniform(nx=30, ny=30, x_min=0, x_max=0.1, y_min=0, y_max=0.1)
    solver = TransientHeatSolver(grid)
    
    solver.set_material_properties(rho=8960, cp=385, k=401)
    
    source = np.zeros((30, 30))
    source[10:20, 10:20] = 1e7
    solver.set_heat_source(source)
    
    edge_mask = np.zeros((30, 30), dtype=bool)
    edge_mask[0, :] = True
    edge_mask[-1, :] = True
    edge_mask[:, 0] = True
    edge_mask[:, -1] = True
    
    solver.set_convection_boundary(edge_mask, h=100, T_ambient=300)
    
    center_mask = np.zeros((30, 30), dtype=bool)
    center_mask[15, 15] = True
    solver.set_dirichlet_boundary(center_mask, temperature=350)
    
    snapshots = solver.solve_transient(
        total_time=10.0, dt=0.01, method='implicit',
        snapshot_interval=10, verbose=True
    )
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    solver.plot_temperature(ax=ax1)
    solver.plot_time_series([(5, 5), (15, 15), (25, 25)], ax=ax2)
    plt.tight_layout()
    plt.savefig('example_transient_heating.png', dpi=150)
    plt.close()
    
    print("Saved: example_transient_heating.png")
    return solver


def example_radiation_cooling():
    print("\n=== Example 3: Radiation Cooling ===")
    
    grid = NonUniformGrid.create_stretched(
        nx=40, ny=40, x_min=-0.05, x_max=0.05, y_min=-0.05, y_max=0.05,
        stretch_x=2, stretch_y=2
    )
    
    solver = AdvancedHeatSolver(grid)
    
    solver.set_material_properties(rho=7850, cp=450, k=50)
    
    X, Y = grid.X, grid.Y
    radius = np.sqrt(X**2 + Y**2)
    circular_mask = radius <= 0.04
    solver.set_region_mask(circular_mask)
    
    solver.u[:] = 800
    
    boundary_mask = np.zeros((grid.ny, grid.nx), dtype=bool)
    for j in range(grid.ny):
        for i in range(grid.nx):
            if circular_mask[j, i]:
                has_outside_neighbor = False
                for dj, di in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nj, ni = j + dj, i + di
                    if 0 <= nj < grid.ny and 0 <= ni < grid.nx:
                        if not circular_mask[nj, ni]:
                            has_outside_neighbor = True
                            break
                if has_outside_neighbor:
                    boundary_mask[j, i] = True
    
    solver.set_radiation_boundary(boundary_mask, epsilon=0.8, T_surroundings=300)
    
    snapshots = solver.solve_transient(
        total_time=5.0, dt=0.02, method='implicit',
        snapshot_interval=5, verbose=True
    )
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    solver.plot_temperature(ax=ax1)
    solver.plot_time_series([(20, 20), (30, 30)], ax=ax2)
    plt.tight_layout()
    plt.savefig('example_radiation_cooling.png', dpi=150)
    plt.close()
    
    print("Saved: example_radiation_cooling.png")
    return solver


def example_mixed_boundary():
    print("\n=== Example 4: Mixed Boundary Conditions (Convection + Radiation) ===")
    
    grid = NonUniformGrid.create_uniform(nx=40, ny=40, x_min=0, x_max=0.2, y_min=0, y_max=0.2)
    solver = AdvancedHeatSolver(grid)
    
    solver.set_material_properties(rho=2700, cp=900, k=205)
    
    solver.u[:] = 500
    
    left_mask = np.zeros((40, 40), dtype=bool)
    left_mask[:, 0] = True
    solver.set_convection_boundary(left_mask, h=200, T_ambient=400)
    
    right_mask = np.zeros((40, 40), dtype=bool)
    right_mask[:, -1] = True
    solver.set_dirichlet_boundary(right_mask, temperature=600)
    
    bottom_mask = np.zeros((40, 40), dtype=bool)
    bottom_mask[0, :] = True
    solver.set_mixed_boundary(bottom_mask, h=50, T_ambient=300, epsilon=0.5, T_surroundings=300)
    
    top_mask = np.zeros((40, 40), dtype=bool)
    top_mask[-1, :] = True
    solver.set_radiation_boundary(top_mask, epsilon=0.7, T_surroundings=298)
    
    u, converged = solver.solve_steady_state(max_iter=5000, tol=1e-5, omega=1.5)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    solver.plot_temperature(ax=ax1)
    solver.plot_steady_convergence(ax=ax2)
    
    ax1.set_title('Steady State with Mixed Boundary Conditions')
    ax1.text(0.01, 1.02, 'Left: Convection (h=200, T=400K)', transform=ax1.transAxes, fontsize=8)
    ax1.text(0.01, 1.0, 'Right: Dirichlet (T=600K)', transform=ax1.transAxes, fontsize=8)
    ax1.text(0.6, 1.02, 'Bottom: Mixed', transform=ax1.transAxes, fontsize=8)
    ax1.text(0.6, 1.0, 'Top: Radiation', transform=ax1.transAxes, fontsize=8)
    
    plt.tight_layout()
    plt.savefig('example_mixed_boundary.png', dpi=150)
    plt.close()
    
    print(f"Converged: {converged}")
    print("Saved: example_mixed_boundary.png")
    return solver


def example_local_heat_source():
    print("\n=== Example 5: Local Heat Source with Grid Refinement ===")
    
    refine_regions = [
        (0.4, 0.6, 0.4, 0.6, 5.0),
    ]
    
    grid = NonUniformGrid.create_with_refinement(
        nx=60, ny=60, x_min=0, x_max=0.1, y_min=0, y_max=0.1,
        refine_regions=refine_regions
    )
    
    solver = AdvancedHeatSolver(grid)
    
    solver.set_material_properties(rho=8000, cp=500, k=50)
    
    X, Y = grid.X, grid.Y
    source = np.zeros_like(X)
    source_mask = (X > 0.045) & (X < 0.055) & (Y > 0.045) & (Y < 0.055)
    source[source_mask] = 1e8
    solver.set_heat_source(source)
    
    edge_mask = np.zeros((grid.ny, grid.nx), dtype=bool)
    edge_mask[0, :] = True
    edge_mask[-1, :] = True
    edge_mask[:, 0] = True
    edge_mask[:, -1] = True
    solver.set_convection_boundary(edge_mask, h=100, T_ambient=300)
    
    u, converged = solver.solve_steady_state(max_iter=3000, tol=1e-5, omega=1.6)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    grid.plot_grid(ax=ax1)
    u_masked = solver.get_solution()
    im = ax1.contourf(grid.x_coords, grid.y_coords, u_masked, levels=30, cmap='hot', alpha=0.7)
    plt.colorbar(im, ax=ax1, label='Temperature (K)')
    ax1.set_title('Temperature on Non-Uniform Grid')
    
    solver.plot_steady_convergence(ax=ax2)
    
    plt.tight_layout()
    plt.savefig('example_local_source.png', dpi=150)
    plt.close()
    
    max_temp = np.max(u[solver.mask])
    print(f"Max temperature: {max_temp:.1f} K")
    print(f"Converged: {converged}")
    print("Saved: example_local_source.png")
    return solver


if __name__ == "__main__":
    example_nonuniform_grid()
    example_transient_heating()
    example_radiation_cooling()
    example_mixed_boundary()
    example_local_heat_source()
    print("\nAll extended examples completed!")
