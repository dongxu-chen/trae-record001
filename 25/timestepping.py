import numpy as np


class TimeIntegrator:
    def __init__(self, cfl=0.8):
        self.cfl = cfl

    def compute_dt(self, U, mesh, flux_solver):
        W = np.zeros_like(U)
        for i in range(mesh.n_cells):
            W[:, i] = flux_solver.primitive_from_conservative(U[:, i])

        max_speed = 0.0
        for i in range(mesh.n_cells):
            rho, u, p = W[:, i]
            c = flux_solver.speed_of_sound(rho, p)
            speed = abs(u) + c
            if speed > max_speed:
                max_speed = speed

        if max_speed == 0.0:
            return 1.0

        min_h = np.min(mesh.cell_lengths)
        dt = self.cfl * min_h / max_speed

        return dt

    def step(self, U, t, dt, flux_solver, mesh, boundary_manager):
        raise NotImplementedError("Subclasses must implement step method")


class ForwardEuler(TimeIntegrator):
    def __init__(self, cfl=0.8):
        super().__init__(cfl)

    def step(self, U, t, dt, flux_solver, mesh, boundary_manager):
        dU_dt = self._compute_rhs(U, flux_solver, mesh, boundary_manager)
        return U + dt * dU_dt

    def _compute_rhs(self, U, flux_solver, mesh, boundary_manager):
        n_cells = mesh.n_cells
        dU_dt = np.zeros_like(U)

        U_ghost_left = boundary_manager.get_ghost_state(U, mesh, flux_solver, 'left')
        U_ghost_right = boundary_manager.get_ghost_state(U, mesh, flux_solver, 'right')

        F = np.zeros((3, n_cells + 1))

        F[:, 0] = flux_solver.solve(U_ghost_left, U[:, 0])

        for i in range(1, n_cells):
            F[:, i] = flux_solver.solve(U[:, i - 1], U[:, i])

        F[:, n_cells] = flux_solver.solve(U[:, n_cells - 1], U_ghost_right)

        for i in range(n_cells):
            face_area = mesh.get_face_area(i)
            dU_dt[:, i] = -(F[:, i + 1] - F[:, i]) * face_area / mesh.cell_lengths[i]

        return dU_dt


class RungeKutta2(TimeIntegrator):
    def __init__(self, cfl=0.8):
        super().__init__(cfl)

    def step(self, U, t, dt, flux_solver, mesh, boundary_manager):
        U1 = self._forward_euler_step(U, dt, flux_solver, mesh, boundary_manager)

        k1 = self._compute_rhs(U, flux_solver, mesh, boundary_manager)
        k2 = self._compute_rhs(U1, flux_solver, mesh, boundary_manager)

        return U + dt * 0.5 * (k1 + k2)

    def _forward_euler_step(self, U, dt, flux_solver, mesh, boundary_manager):
        dU_dt = self._compute_rhs(U, flux_solver, mesh, boundary_manager)
        return U + dt * dU_dt

    def _compute_rhs(self, U, flux_solver, mesh, boundary_manager):
        n_cells = mesh.n_cells
        dU_dt = np.zeros_like(U)

        U_ghost_left = boundary_manager.get_ghost_state(U, mesh, flux_solver, 'left')
        U_ghost_right = boundary_manager.get_ghost_state(U, mesh, flux_solver, 'right')

        F = np.zeros((3, n_cells + 1))

        F[:, 0] = flux_solver.solve(U_ghost_left, U[:, 0])

        for i in range(1, n_cells):
            F[:, i] = flux_solver.solve(U[:, i - 1], U[:, i])

        F[:, n_cells] = flux_solver.solve(U[:, n_cells - 1], U_ghost_right)

        for i in range(n_cells):
            face_area = mesh.get_face_area(i)
            dU_dt[:, i] = -(F[:, i + 1] - F[:, i]) * face_area / mesh.cell_lengths[i]

        return dU_dt


class RungeKutta3(TimeIntegrator):
    def __init__(self, cfl=0.8):
        super().__init__(cfl)
        self.a = [1.0, 3.0 / 4.0, 1.0 / 3.0]
        self.b = [0.0, 1.0 / 4.0, 2.0 / 3.0]
        self.c = [1.0, 1.0 / 4.0, 2.0 / 3.0]

    def step(self, U, t, dt, flux_solver, mesh, boundary_manager):
        U0 = U.copy()

        for stage in range(3):
            k = self._compute_rhs(U, flux_solver, mesh, boundary_manager)
            U = self.a[stage] * U0 + self.b[stage] * U + self.c[stage] * dt * k

        return U

    def _compute_rhs(self, U, flux_solver, mesh, boundary_manager):
        n_cells = mesh.n_cells
        dU_dt = np.zeros_like(U)

        U_ghost_left = boundary_manager.get_ghost_state(U, mesh, flux_solver, 'left')
        U_ghost_right = boundary_manager.get_ghost_state(U, mesh, flux_solver, 'right')

        F = np.zeros((3, n_cells + 1))

        F[:, 0] = flux_solver.solve(U_ghost_left, U[:, 0])

        for i in range(1, n_cells):
            F[:, i] = flux_solver.solve(U[:, i - 1], U[:, i])

        F[:, n_cells] = flux_solver.solve(U[:, n_cells - 1], U_ghost_right)

        for i in range(n_cells):
            face_area = mesh.get_face_area(i)
            dU_dt[:, i] = -(F[:, i + 1] - F[:, i]) * face_area / mesh.cell_lengths[i]

        return dU_dt


class RungeKutta4(TimeIntegrator):
    def __init__(self, cfl=0.8):
        super().__init__(cfl)

    def step(self, U, t, dt, flux_solver, mesh, boundary_manager):
        k1 = self._compute_rhs(U, flux_solver, mesh, boundary_manager)

        U2 = U + dt / 2.0 * k1
        k2 = self._compute_rhs(U2, flux_solver, mesh, boundary_manager)

        U3 = U + dt / 2.0 * k2
        k3 = self._compute_rhs(U3, flux_solver, mesh, boundary_manager)

        U4 = U + dt * k3
        k4 = self._compute_rhs(U4, flux_solver, mesh, boundary_manager)

        return U + dt / 6.0 * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

    def _compute_rhs(self, U, flux_solver, mesh, boundary_manager):
        n_cells = mesh.n_cells
        dU_dt = np.zeros_like(U)

        U_ghost_left = boundary_manager.get_ghost_state(U, mesh, flux_solver, 'left')
        U_ghost_right = boundary_manager.get_ghost_state(U, mesh, flux_solver, 'right')

        F = np.zeros((3, n_cells + 1))

        F[:, 0] = flux_solver.solve(U_ghost_left, U[:, 0])

        for i in range(1, n_cells):
            F[:, i] = flux_solver.solve(U[:, i - 1], U[:, i])

        F[:, n_cells] = flux_solver.solve(U[:, n_cells - 1], U_ghost_right)

        for i in range(n_cells):
            face_area = mesh.get_face_area(i)
            dU_dt[:, i] = -(F[:, i + 1] - F[:, i]) * face_area / mesh.cell_lengths[i]

        return dU_dt


class MUSCLReconstructor:
    def __init__(self, kappa=-1.0, limit='minmod'):
        self.kappa = kappa
        self.limit = limit
        self._euler = None

    def _limit_slope(self, delta_left, delta_right):
        if self.limit == 'none':
            return delta_right
        elif self.limit == 'minmod':
            return self._minmod(delta_left, delta_right)
        elif self.limit == 'van_leer':
            return self._van_leer(delta_left, delta_right)
        else:
            raise ValueError(f"Unknown limiter: {self.limit}")

    def _minmod(self, a, b):
        if a * b <= 0:
            return 0.0
        elif abs(a) < abs(b):
            return a
        else:
            return b

    def _van_leer(self, a, b):
        if a * b <= 0:
            return 0.0
        else:
            return 2.0 * a * b / (a + b)

    def reconstruct(self, U, flux_solver):
        if self._euler is None:
            self._euler = flux_solver

        n_cells = U.shape[1]
        U_L = np.zeros_like(U)
        U_R = np.zeros_like(U)

        for var in range(3):
            for i in range(n_cells):
                if i == 0:
                    delta_left = U[var, i + 1] - U[var, i]
                    delta_right = U[var, i + 1] - U[var, i]
                elif i == n_cells - 1:
                    delta_left = U[var, i] - U[var, i - 1]
                    delta_right = U[var, i] - U[var, i - 1]
                else:
                    delta_left = U[var, i] - U[var, i - 1]
                    delta_right = U[var, i + 1] - U[var, i]

                slope = self._limit_slope(delta_left, delta_right)

                U_L[var, i] = U[var, i] - 0.25 * (1.0 + self.kappa) * slope
                U_R[var, i] = U[var, i] + 0.25 * (1.0 - self.kappa) * slope

        return U_L, U_R


class MUSCLTimeIntegrator(TimeIntegrator):
    def __init__(self, base_integrator, kappa=-1.0, limit='minmod', cfl=0.8):
        super().__init__(cfl)
        self.base_integrator = base_integrator
        self.reconstructor = MUSCLReconstructor(kappa=kappa, limit=limit)

    def compute_dt(self, U, mesh, flux_solver):
        return self.base_integrator.compute_dt(U, mesh, flux_solver)

    def step(self, U, t, dt, flux_solver, mesh, boundary_manager):
        return self.base_integrator.step(U, t, dt, flux_solver, mesh, boundary_manager)


def create_time_integrator(scheme='rk3', cfl=0.8, use_muscl=False, kappa=-1.0, limit='minmod'):
    if scheme == 'euler':
        integrator = ForwardEuler(cfl=cfl)
    elif scheme == 'rk2':
        integrator = RungeKutta2(cfl=cfl)
    elif scheme == 'rk3':
        integrator = RungeKutta3(cfl=cfl)
    elif scheme == 'rk4':
        integrator = RungeKutta4(cfl=cfl)
    else:
        raise ValueError(f"Unknown time integration scheme: {scheme}")

    if use_muscl:
        return MUSCLTimeIntegrator(integrator, kappa=kappa, limit=limit, cfl=cfl)
    else:
        return integrator


class LocalTimeStepping:
    def __init__(self, base_integrator, cfl=0.8, max_level=10):
        self.base_integrator = base_integrator
        self.cfl = cfl
        self.max_level = max_level

    def compute_cell_dt(self, U, mesh, flux_solver, cell_idx, normal=None):
        if hasattr(mesh, 'get_cell_geometry'):
            result = mesh.get_cell_geometry(cell_idx)
            if len(result) >= 7:
                center, area, edge_centers, edge_lengths, edge_normals, h, level = result
            elif len(result) == 4:
                center, area, edge_lengths, edge_normals = result
                h = np.sqrt(area)
                level = 0
            else:
                h = np.sqrt(area)
                level = 0
        elif hasattr(mesh, 'cell_lengths'):
            h = mesh.cell_lengths[cell_idx]
            level = 0
        else:
            h = 1.0
            level = 0

        W = flux_solver.primitive_from_conservative(U[:, cell_idx])

        if flux_solver.dim == 1:
            rho, u, p = W
            c = flux_solver.speed_of_sound(rho, p)
            max_speed = abs(u) + c
        else:
            rho, u, v, p = W
            c = flux_solver.speed_of_sound(rho, p)
            max_speed = np.sqrt(u**2 + v**2) + c

        if max_speed == 0.0:
            return 1.0, level

        dt = self.cfl * h / max_speed
        return dt, level

    def compute_all_dt(self, U, mesh, flux_solver):
        n_cells = mesh.n_cells
        cell_dt = np.zeros(n_cells)
        cell_level = np.zeros(n_cells, dtype=np.int32)

        for i in range(n_cells):
            cell_dt[i], cell_level[i] = self.compute_cell_dt(U, mesh, flux_solver, i)

        return cell_dt, cell_level

    def _group_by_level(self, cell_level, n_levels):
        groups = {}
        for i, level in enumerate(cell_level):
            if level not in groups:
                groups[level] = []
            groups[level].append(i)
        return groups

    def step_with_lts(self, U, t, flux_solver, mesh, boundary_manager, n_subcycles=1):
        n_vars = U.shape[0]
        n_cells = mesh.n_cells

        cell_dt, cell_level = self.compute_all_dt(U, mesh, flux_solver)

        min_dt = np.min(cell_dt)
        max_dt = np.max(cell_dt)
        dt_ratio = max_dt / min_dt if min_dt > 0 else 1.0

        n_subcycles = int(max(1, min(np.log2(dt_ratio) + 1, 10)))

        U_new = U.copy()
        U_stage = U.copy()

        dU_dt_global = np.zeros_like(U)
        for i in range(n_cells):
            dU_dt_global[:, i] = self._compute_cell_residual(
                U, i, flux_solver, mesh, boundary_manager
            )

        for sc in range(n_subcycles):
            for i in range(n_cells):
                level_dt = cell_dt[i] / n_subcycles
                U_new[:, i] = U[:, i] + level_dt * dU_dt_global[:, i]

        return U_new

    def _compute_cell_residual(self, U, cell_idx, flux_solver, mesh, boundary_manager):
        n_vars = U.shape[0]
        residual = np.zeros(n_vars)

        if flux_solver.dim == 1:
            neighbors = mesh.neighbors[cell_idx]

            if neighbors[0] >= 0:
                U_L = U[:, neighbors[0]]
                U_R = U[:, cell_idx]
                F = flux_solver.solve(U_L, U_R)
                residual += F

            if neighbors[1] >= 0:
                U_L = U[:, cell_idx]
                U_R = U[:, neighbors[1]]
                F = flux_solver.solve(U_L, U_R)
                residual -= F
        else:
            if hasattr(mesh, 'get_neighbor_cell_ids'):
                neighbor_ids = mesh.get_neighbor_cell_ids(cell_idx)
            else:
                neighbor_ids = []

            geom = mesh.get_cell_geometry(cell_idx)

            if len(geom) >= 7:
                center, area, edge_centers, edge_lengths, edge_normals, h, level = geom
                n_edges = len(edge_normals)
            elif len(geom) == 4:
                center, area, edge_lengths, edge_normals = geom
                n_edges = len(edge_normals)
            else:
                return residual

            for e in range(n_edges):
                normal = edge_normals[e]
                length = edge_lengths[e]

                U_L = U[:, cell_idx]

                if e < len(neighbor_ids) and neighbor_ids[e] >= 0:
                    U_R = U[:, neighbor_ids[e]]
                else:
                    U_R = U[:, cell_idx]

                F = flux_solver.solve_edge_flux(U_L, U_R, normal, length)
                residual += F

        return residual / area if area > 0 else residual


class TimeSteppingManager:
    def __init__(self, base_integrator, use_lts=False, cfl=0.8):
        self.base = base_integrator
        self.use_lts = use_lts
        self.cfl = cfl

        if use_lts:
            self.lts = LocalTimeStepping(base_integrator, cfl=cfl)

    def step(self, U, t, flux_solver, mesh, boundary_manager, dt=None):
        if dt is None:
            dt = self.base.compute_dt(U, mesh, flux_solver)

        if self.use_lts and hasattr(flux_solver, 'dim') and flux_solver.dim == 2:
            return self.lts.step_with_lts(U, t, flux_solver, mesh, boundary_manager)
        else:
            return self.base.step(U, t, dt, flux_solver, mesh, boundary_manager)

    def compute_dt(self, U, mesh, flux_solver):
        return self.base.compute_dt(U, mesh, flux_solver)


def create_time_manager(scheme='rk3', cfl=0.8, use_muscl=False, use_lts=False,
                        kappa=-1.0, limit='minmod'):
    base = create_time_integrator(
        scheme=scheme, cfl=cfl, use_muscl=use_muscl,
        kappa=kappa, limit=limit
    )
    return TimeSteppingManager(base, use_lts=use_lts, cfl=cfl)
