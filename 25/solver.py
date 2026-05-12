import numpy as np
from mesh import (
    generate_uniform_mesh, generate_non_uniform_mesh, UnstructuredMesh1D,
    generate_quadtree_mesh, QuadTreeMesh
)
from flux import create_flux_solver, create_2d_flux_solver, EulerFlux
from boundary import (
    create_boundary_condition, BoundaryManager,
    create_2d_boundary_manager, BoundaryManager2D
)
from timestepping import create_time_integrator, create_time_manager


class EulerSolver1D:
    def __init__(
        self,
        mesh,
        flux_solver_type='roe',
        time_scheme='rk3',
        left_bc='supersonic_outflow',
        right_bc='supersonic_outflow',
        gamma=1.4,
        cfl=0.8,
        left_bc_params=None,
        right_bc_params=None
    ):
        self.mesh = mesh
        self.gamma = gamma
        self.flux_solver = create_flux_solver(flux_solver_type, gamma=gamma)
        self.euler = EulerFlux(gamma=gamma)

        if left_bc_params is None:
            left_bc_params = {}
        if right_bc_params is None:
            right_bc_params = {}

        left_bc_obj = create_boundary_condition(left_bc, **left_bc_params)
        right_bc_obj = create_boundary_condition(right_bc, **right_bc_params)
        self.boundary_manager = BoundaryManager(left_bc_obj, right_bc_obj)

        self.time_integrator = create_time_integrator(time_scheme, cfl=cfl)

        self.U = np.zeros((3, mesh.n_cells))
        self.t = 0.0
        self.dt = 0.0
        self.n_steps = 0
        self.history = []

    def initialize(self, initial_condition_func):
        for i in range(self.mesh.n_cells):
            x = self.mesh.cell_centers[i]
            rho, u, p = initial_condition_func(x)
            self.U[:, i] = self.euler.conservative_from_primitive(rho, u, p)
        self.t = 0.0
        self.n_steps = 0
        self._save_history()

    def _save_history(self):
        self.history.append({
            't': self.t,
            'U': self.U.copy()
        })

    def get_primitive_variables(self):
        rho = np.zeros(self.mesh.n_cells)
        u = np.zeros(self.mesh.n_cells)
        p = np.zeros(self.mesh.n_cells)

        for i in range(self.mesh.n_cells):
            W = self.euler.primitive_from_conservative(self.U[:, i])
            rho[i], u[i], p[i] = W

        return rho, u, p

    def get_history_primitive(self):
        history_prim = []
        for entry in self.history:
            U = entry['U']
            rho = np.zeros(self.mesh.n_cells)
            u = np.zeros(self.mesh.n_cells)
            p = np.zeros(self.mesh.n_cells)
            for i in range(self.mesh.n_cells):
                W = self.euler.primitive_from_conservative(U[:, i])
                rho[i], u[i], p[i] = W
            history_prim.append({
                't': entry['t'],
                'rho': rho,
                'u': u,
                'p': p
            })
        return history_prim

    def compute_dt(self):
        self.dt = self.time_integrator.compute_dt(self.U, self.mesh, self.flux_solver)
        return self.dt

    def step(self, dt=None):
        if dt is None:
            dt = self.compute_dt()

        self.U = self.time_integrator.step(
            self.U,
            self.t,
            dt,
            self.flux_solver,
            self.mesh,
            self.boundary_manager
        )

        self.t += dt
        self.n_steps += 1
        self._save_history()

        return self.t

    def solve(self, t_end, save_interval=1, verbose=True):
        while self.t < t_end:
            dt = self.compute_dt()
            if self.t + dt > t_end:
                dt = t_end - self.t

            self.step(dt)

            if verbose and self.n_steps % 10 == 0:
                print(f"Step {self.n_steps}, t = {self.t:.4e}, dt = {dt:.4e}")

        return self.U

    def solve_for_steps(self, n_steps, save_interval=1, verbose=True):
        for _ in range(n_steps):
            dt = self.compute_dt()
            self.step(dt)

            if verbose and self.n_steps % 10 == 0:
                print(f"Step {self.n_steps}, t = {self.t:.4e}, dt = {dt:.4e}")

        return self.U


def sod_shock_tube(x, x_shock=0.5):
    if x < x_shock:
        return 1.0, 0.0, 1.0
    else:
        return 0.125, 0.0, 0.1


def moving_shock(x, x_shock=0.0, M=2.0, gamma=1.4):
    if x < x_shock:
        rho1 = 1.0
        u1 = 0.0
        p1 = 1.0

        beta = (gamma - 1.0) / (gamma + 1.0)
        M2 = (M**2 + 2.0 / (gamma - 1.0)) / (2.0 * gamma / (gamma - 1.0) * M**2 - 1.0)
        rho2 = rho1 * M / M2
        p2 = p1 * (1.0 + 2.0 * gamma / (gamma + 1.0) * (M**2 - 1.0))
        u2 = u1 + (1.0 - M2 / M) * (gamma * p1 / rho1)**0.5

        return rho2, u2, p2
    else:
        return 1.0, 0.0, 1.0


def isentropic_vortex(x, t=0.0, x0=0.0, u0=1.0, p0=1.0, rho0=1.0, alpha=1.0, gamma=1.4):
    x_rel = x - x0 - u0 * t
    theta = alpha * np.exp(-x_rel**2)

    gamma1 = gamma - 1.0
    R = 1.0

    T = 1.0 - gamma1 * alpha**2 / (8.0 * gamma * np.pi**2) * np.exp(-2.0 * x_rel**2)
    rho = rho0 * T ** (1.0 / gamma1)
    p = p0 * T ** (gamma / gamma1)
    u = u0 + alpha * np.exp(-x_rel**2)

    return rho, u, p


def rarefaction_wave(x, x0=0.5, t=0.0):
    if t == 0.0:
        if x < x0:
            return 2.0, 0.0, 2.0
        else:
            return 1.0, 0.0, 1.0
    else:
        gamma = 1.4
        gamma1 = gamma - 1.0
        a_left = np.sqrt(gamma * 2.0 / 2.0)
        a_right = np.sqrt(gamma * 1.0 / 1.0)

        if x < x0 - a_left * t:
            return 2.0, 0.0, 2.0
        elif x > x0 + a_right * t:
            return 1.0, 0.0, 1.0
        else:
            a_mid = (2.0 * a_left + gamma1 * (x0 - x) / t) / (gamma + 1.0)
            u_mid = 2.0 * (a_left - a_mid) / gamma1
            rho_mid = 2.0 * (a_mid / a_left) ** (2.0 / gamma1)
            p_mid = 2.0 * (a_mid / a_left) ** (2.0 * gamma / gamma1)
            return rho_mid, u_mid, p_mid


def test_solver():
    print("Testing EulerSolver1D with Sod shock tube...")

    mesh = generate_uniform_mesh(0.0, 1.0, 200)

    solver = EulerSolver1D(
        mesh=mesh,
        flux_solver_type='roe',
        time_scheme='rk3',
        left_bc='zero_gradient',
        right_bc='zero_gradient',
        cfl=0.8
    )

    def ic(x):
        return sod_shock_tube(x, x_shock=0.5)

    solver.initialize(ic)

    t_end = 0.2
    solver.solve(t_end, verbose=True)

    rho, u, p = solver.get_primitive_variables()

    print("\nFinal primitive variables (first and last 5 cells):")
    print(f"{'Cell':>6} {'x':>10} {'rho':>10} {'u':>10} {'p':>10}")
    for i in list(range(5)) + list(range(mesh.n_cells - 5, mesh.n_cells)):
        print(f"{i:>6} {mesh.cell_centers[i]:>10.4f} {rho[i]:>10.4f} {u[i]:>10.4f} {p[i]:>10.4f}")

    print(f"\nTotal steps: {solver.n_steps}")
    print(f"Final time: {solver.t:.6f}")

    return solver


class EulerSolver2D:
    def __init__(
        self,
        mesh,
        flux_solver_type='roe',
        time_scheme='rk3',
        gamma=1.4,
        cfl=0.8,
        boundary_config=None,
        use_amr=False,
        use_lts=False
    ):
        self.mesh = mesh
        self.gamma = gamma
        self.cfl = cfl
        self.use_amr = use_amr

        self.flux_solver = create_2d_flux_solver(flux_solver_type, gamma=gamma)

        self.euler = EulerFlux(gamma=gamma, dim=2)

        if boundary_config is None:
            boundary_config = {'default': {'type': 'zero_gradient'}}
        self.boundary_manager = create_2d_boundary_manager(boundary_config)

        self.time_manager = create_time_manager(
            scheme=time_scheme, cfl=cfl, use_lts=use_lts
        )

        self.n_vars = 4
        self.U = np.zeros((self.n_vars, mesh.n_cells))
        self.t = 0.0
        self.dt = 0.0
        self.n_steps = 0
        self.history = []

        if use_amr:
            from amr import AMRManager, AMRMarker
            marker = AMRMarker(refine_threshold=0.3, coarsen_threshold=0.05)
            self.amr = AMRManager(mesh, marker)
        else:
            self.amr = None

    def initialize(self, initial_condition_func):
        leaves = self.mesh.get_leaves()
        for i, leaf in enumerate(leaves):
            x, y = leaf.center
            rho, u, v, p = initial_condition_func(x, y)
            self.U[:, i] = self.euler.conservative_from_primitive(rho, u, p, v)
        self.t = 0.0
        self.n_steps = 0
        self._save_history()

    def _save_history(self):
        self.history.append({
            't': self.t,
            'U': self.U.copy()
        })

    def get_primitive_variables(self):
        n_cells = self.U.shape[1]
        rho = np.zeros(n_cells)
        u = np.zeros(n_cells)
        v = np.zeros(n_cells)
        p = np.zeros(n_cells)

        for i in range(n_cells):
            W = self.euler.primitive_from_conservative(self.U[:, i])
            rho[i], u[i], v[i], p[i] = W

        return rho, u, v, p

    def get_cell_centers(self):
        leaves = self.mesh.get_leaves()
        centers = np.zeros((len(leaves), 2))
        for i, leaf in enumerate(leaves):
            centers[i] = leaf.center
        return centers

    def compute_dt(self):
        leaves = self.mesh.get_leaves()
        min_h = float('inf')
        max_speed = 0.0

        for i, leaf in enumerate(leaves):
            h = leaf.size
            if h < min_h:
                min_h = h

            W = self.euler.primitive_from_conservative(self.U[:, i])
            rho, u, v, p = W
            c = self.euler.speed_of_sound(rho, p)
            speed = np.sqrt(u**2 + v**2) + c
            if speed > max_speed:
                max_speed = speed

        if max_speed == 0.0:
            self.dt = 1.0
        else:
            self.dt = self.cfl * min_h / max_speed

        return self.dt

    def _compute_residual(self):
        n_cells = self.U.shape[1]
        dU_dt = np.zeros_like(self.U)

        leaves = self.mesh.get_leaves()

        for i, leaf in enumerate(leaves):
            geom = self.mesh.get_cell_geometry(i)
            center, area, edge_centers, edge_lengths, edge_normals, h, level = geom
            neighbor_ids = self.mesh.get_neighbor_cell_ids(i)

            residual = np.zeros(self.n_vars)

            for e in range(4):
                normal = edge_normals[e]
                length = edge_lengths[e]

                U_L = self.U[:, i]

                if neighbor_ids[e] >= 0:
                    U_R = self.U[:, neighbor_ids[e]]
                else:
                    U_ghost = self.boundary_manager.get_ghost_state(
                        U_L, normal, 'default', self.mesh, self.flux_solver, i, e
                    )
                    U_R = U_ghost

                F = self.flux_solver.solve_edge_flux(U_L, U_R, normal, length)
                residual += F

            dU_dt[:, i] = -residual / area if area > 0 else 0.0

        return dU_dt

    def _rk3_step(self, dt):
        U0 = self.U.copy()

        dU_dt = self._compute_residual()
        U1 = U0 + dt * dU_dt
        self.U = U1

        dU_dt = self._compute_residual()
        U2 = 0.75 * U0 + 0.25 * U1 + 0.25 * dt * dU_dt
        self.U = U2

        dU_dt = self._compute_residual()
        self.U = (1.0 / 3.0) * U0 + (2.0 / 3.0) * U2 + (2.0 / 3.0) * dt * dU_dt

    def step(self, dt=None):
        if dt is None:
            dt = self.compute_dt()

        self._rk3_step(dt)

        self.t += dt
        self.n_steps += 1
        self._save_history()

        if self.use_amr and self.amr is not None:
            if self.n_steps % 10 == 0:
                self.U = self.amr.adapt(self.U, self.euler, strategy='pressure')
                self.U = np.zeros((self.n_vars, self.mesh.n_cells)) if self.U.shape[1] != self.mesh.n_cells else self.U

        return self.t

    def solve(self, t_end, verbose=True):
        while self.t < t_end:
            dt = self.compute_dt()
            if self.t + dt > t_end:
                dt = t_end - self.t

            self.step(dt)

            if verbose and self.n_steps % 10 == 0:
                print(f"Step {self.n_steps}, t = {self.t:.4e}, dt = {dt:.4e}")
                print(f"  Cells: {self.mesh.n_cells}")

        return self.U

    def adapt_mesh(self, strategy='pressure'):
        if self.amr is None:
            raise ValueError("AMR is not enabled. Create solver with use_amr=True.")

        self.U = self.amr.adapt(self.U, self.euler, strategy=strategy)

        if self.U.shape[1] != self.mesh.n_cells:
            self.U = np.zeros((self.n_vars, self.mesh.n_cells))

        return self.U


def riemann_problem_2d(x, y, x0=0.5, y0=0.5):
    quadrant = int(x >= x0) + 2 * int(y >= y0)

    states = [
        (1.0, 0.0, 0.0, 1.0),
        (0.5313, 0.0, 0.0, 0.4),
        (0.8, 0.0, 0.0, 1.0),
        (1.0, 0.0, 0.0, 1.0),
    ]

    return states[quadrant]


def uniform_flow_2d(x, y, rho=1.0, u=0.0, v=0.0, p=1.0):
    return rho, u, v, p


def density_perturbation_2d(x, y, x0=0.5, y0=0.5, amplitude=0.5, sigma=0.1):
    r2 = (x - x0)**2 + (y - y0)**2
    rho = 1.0 + amplitude * np.exp(-r2 / (2 * sigma**2))
    return rho, 0.0, 0.0, 1.0


def test_2d_solver():
    print("Testing EulerSolver2D with QuadTree mesh...")

    from mesh import generate_quadtree_mesh

    mesh = generate_quadtree_mesh(0.0, 1.0, 0.0, 1.0, base_level=2, max_level=5)
    print(f"Initial mesh: {mesh.n_cells} cells")
    print(f"Level distribution: {mesh.get_level_distribution()}")

    solver = EulerSolver2D(
        mesh=mesh,
        flux_solver_type='hllc',
        time_scheme='rk3',
        cfl=0.5,
        use_amr=True,
        boundary_config={'default': {'type': 'zero_gradient'}}
    )

    def ic(x, y):
        return density_perturbation_2d(x, y, x0=0.5, y0=0.5, amplitude=0.3, sigma=0.1)

    solver.initialize(ic)

    rho, u, v, p = solver.get_primitive_variables()
    print(f"\nInitial state:")
    print(f"  Density range: [{rho.min():.4f}, {rho.max():.4f}]")
    print(f"  Pressure range: [{p.min():.4f}, {p.max():.4f}]")

    t_end = 0.01
    solver.solve(t_end, verbose=True)

    rho, u, v, p = solver.get_primitive_variables()
    print(f"\nFinal state:")
    print(f"  Density range: [{rho.min():.4f}, {rho.max():.4f}]")
    print(f"  Pressure range: [{p.min():.4f}, {p.max():.4f}]")
    print(f"Final mesh: {mesh.n_cells} cells")
    print(f"Level distribution: {mesh.get_level_distribution()}")
    print(f"\nTotal steps: {solver.n_steps}")
    print(f"Final time: {solver.t:.6f}")

    return solver


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '2d':
        test_2d_solver()
    else:
        test_solver()
