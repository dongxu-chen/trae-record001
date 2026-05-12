import numpy as np
from flux import EulerFlux


class BoundaryCondition:
    def __init__(self, name):
        self.name = name

    def apply(self, U, mesh, flux_solver, side):
        raise NotImplementedError("Subclasses must implement apply method")


class PeriodicBoundary(BoundaryCondition):
    def __init__(self):
        super().__init__('periodic')

    def apply(self, U, mesh, flux_solver, side):
        if side == 'left':
            return U[:, -1]
        elif side == 'right':
            return U[:, 0]
        else:
            raise ValueError(f"Unknown side: {side}")


class ReflectiveBoundary(BoundaryCondition):
    def __init__(self):
        super().__init__('reflective')
        self._euler = None

    def apply(self, U, mesh, flux_solver, side):
        if self._euler is None:
            self._euler = EulerFlux(gamma=flux_solver.gamma)

        if side == 'left':
            U_inner = U[:, 0]
        elif side == 'right':
            U_inner = U[:, -1]
        else:
            raise ValueError(f"Unknown side: {side}")

        W_inner = self._euler.primitive_from_conservative(U_inner)
        rho, u, p = W_inner
        U_ghost = self._euler.conservative_from_primitive(rho, -u, p)

        return U_ghost


class SupersonicInflow(BoundaryCondition):
    def __init__(self, rho, u, p):
        super().__init__('supersonic_inflow')
        self.rho = rho
        self.u = u
        self.p = p
        self._euler = None

    def apply(self, U, mesh, flux_solver, side):
        if self._euler is None:
            self._euler = EulerFlux(gamma=flux_solver.gamma)

        return self._euler.conservative_from_primitive(self.rho, self.u, self.p)


class SupersonicOutflow(BoundaryCondition):
    def __init__(self):
        super().__init__('supersonic_outflow')

    def apply(self, U, mesh, flux_solver, side):
        if side == 'left':
            return U[:, 0]
        elif side == 'right':
            return U[:, -1]
        else:
            raise ValueError(f"Unknown side: {side}")


class SubsonicInflow(BoundaryCondition):
    def __init__(self, rho0, p0):
        super().__init__('subsonic_inflow')
        self.rho0 = rho0
        self.p0 = p0
        self._euler = None

    def apply(self, U, mesh, flux_solver, side):
        if self._euler is None:
            self._euler = EulerFlux(gamma=flux_solver.gamma)

        if side == 'left':
            U_inner = U[:, 0]
        elif side == 'right':
            U_inner = U[:, -1]
        else:
            raise ValueError(f"Unknown side: {side}")

        W_inner = self._euler.primitive_from_conservative(U_inner)
        rho, u, p = W_inner

        c_inner = self._euler.speed_of_sound(rho, p)
        gamma = flux_solver.gamma
        gamma1 = gamma - 1.0

        u_ghost = u
        p_ghost = self.p0
        rho_ghost = self.rho0 * (p_ghost / self.p0) ** (1.0 / gamma)

        return self._euler.conservative_from_primitive(rho_ghost, u_ghost, p_ghost)


class SubsonicOutflow(BoundaryCondition):
    def __init__(self, p_back):
        super().__init__('subsonic_outflow')
        self.p_back = p_back
        self._euler = None

    def apply(self, U, mesh, flux_solver, side):
        if self._euler is None:
            self._euler = EulerFlux(gamma=flux_solver.gamma)

        if side == 'left':
            U_inner = U[:, 0]
        elif side == 'right':
            U_inner = U[:, -1]
        else:
            raise ValueError(f"Unknown side: {side}")

        W_inner = self._euler.primitive_from_conservative(U_inner)
        rho, u, p = W_inner

        if p >= self.p_back:
            return U_inner
        else:
            gamma = flux_solver.gamma
            gamma1 = gamma - 1.0
            c_inner = self._euler.speed_of_sound(rho, p)

            rho_ghost = rho * (self.p_back / p) ** (1.0 / gamma)
            u_ghost = u
            p_ghost = self.p_back

            return self._euler.conservative_from_primitive(rho_ghost, u_ghost, p_ghost)


class NonReflectiveBoundary(BoundaryCondition):
    def __init__(self, rho_far=1.0, u_far=0.0, p_far=1.0):
        super().__init__('non_reflective')
        self.rho_far = rho_far
        self.u_far = u_far
        self.p_far = p_far
        self._euler = None

    def apply(self, U, mesh, flux_solver, side):
        if self._euler is None:
            self._euler = EulerFlux(gamma=flux_solver.gamma)

        if side == 'left':
            U_inner = U[:, 0]
        elif side == 'right':
            U_inner = U[:, -1]
        else:
            raise ValueError(f"Unknown side: {side}")

        W_inner = self._euler.primitive_from_conservative(U_inner)
        rho, u, p = W_inner

        gamma = flux_solver.gamma
        gamma1 = gamma - 1.0

        c = self._euler.speed_of_sound(rho, p)
        c_far = self._euler.speed_of_sound(self.rho_far, self.p_far)

        if side == 'left':
            if u + c > 0.0:
                J_plus_inner = u + 2.0 * c / gamma1
                J_minus_far = self.u_far - 2.0 * c_far / gamma1

                J_plus = J_plus_inner
                J_minus = J_minus_far

                u_ghost = 0.5 * (J_plus + J_minus)
                c_ghost = gamma1 / 4.0 * (J_plus - J_minus)

                S_inner = p / (rho ** gamma)
                p_ghost = p
                rho_ghost = (p_ghost / S_inner) ** (1.0 / gamma)
            else:
                rho_ghost = self.rho_far
                u_ghost = self.u_far
                p_ghost = self.p_far

        elif side == 'right':
            if u - c < 0.0:
                J_minus_inner = u - 2.0 * c / gamma1
                J_plus_far = self.u_far + 2.0 * c_far / gamma1

                J_minus = J_minus_inner
                J_plus = J_plus_far

                u_ghost = 0.5 * (J_plus + J_minus)
                c_ghost = gamma1 / 4.0 * (J_plus - J_minus)

                S_inner = p / (rho ** gamma)
                p_ghost = p
                rho_ghost = (p_ghost / S_inner) ** (1.0 / gamma)
            else:
                rho_ghost = self.rho_far
                u_ghost = self.u_far
                p_ghost = self.p_far

        c_ghost = max(c_ghost, 1e-10)
        rho_ghost = max(rho_ghost, 1e-10)
        p_ghost = max(p_ghost, 1e-10)

        return self._euler.conservative_from_primitive(rho_ghost, u_ghost, p_ghost)


class FarfieldCharacteristicBoundary(BoundaryCondition):
    def __init__(self, rho_far=1.0, u_far=0.0, p_far=1.0):
        super().__init__('farfield_characteristic')
        self.rho_far = rho_far
        self.u_far = u_far
        self.p_far = p_far
        self._euler = None

    def apply(self, U, mesh, flux_solver, side):
        if self._euler is None:
            self._euler = EulerFlux(gamma=flux_solver.gamma)

        if side == 'left':
            U_inner = U[:, 0]
            is_inlet = True
        elif side == 'right':
            U_inner = U[:, -1]
            is_inlet = False
        else:
            raise ValueError(f"Unknown side: {side}")

        W_inner = self._euler.primitive_from_conservative(U_inner)
        rho, u, p = W_inner

        gamma = flux_solver.gamma
        gamma1 = gamma - 1.0

        c = self._euler.speed_of_sound(rho, p)
        c_far = self._euler.speed_of_sound(self.rho_far, self.p_far)

        Mach_inner = u / c
        Mach_far = self.u_far / c_far

        if is_inlet:
            n_dot_u = u
            eigenvalues = np.array([u - c, u, u + c])
            outgoing = eigenvalues > 0
        else:
            n_dot_u = -u
            eigenvalues = np.array([-(u - c), -u, -(u + c)])
            outgoing = eigenvalues > 0

        n_outgoing = np.sum(outgoing)

        if abs(Mach_inner) >= 1.0:
            if is_inlet:
                if Mach_inner > 0:
                    rho_ghost = self.rho_far
                    u_ghost = self.u_far
                    p_ghost = self.p_far
                else:
                    rho_ghost = rho
                    u_ghost = u
                    p_ghost = p
            else:
                if Mach_inner < 0:
                    rho_ghost = self.rho_far
                    u_ghost = self.u_far
                    p_ghost = self.p_far
                else:
                    rho_ghost = rho
                    u_ghost = u
                    p_ghost = p

            return self._euler.conservative_from_primitive(rho_ghost, u_ghost, p_ghost)

        if n_outgoing == 2:
            if is_inlet:
                J_plus_inner = u + 2.0 * c / gamma1
                J_minus_far = self.u_far - 2.0 * c_far / gamma1

                J_plus = J_plus_inner
                J_minus = J_minus_far

                u_ghost = 0.5 * (J_plus + J_minus)
                c_ghost = gamma1 / 4.0 * (J_plus - J_minus)

                S_far = self.p_far / (self.rho_far ** gamma)
                rho_ghost = (self.p_far / S_far) ** (1.0 / gamma)
                p_ghost = self.p_far
            else:
                J_minus_inner = u - 2.0 * c / gamma1
                J_plus_far = self.u_far + 2.0 * c_far / gamma1

                J_minus = J_minus_inner
                J_plus = J_plus_far

                u_ghost = 0.5 * (J_plus + J_minus)
                c_ghost = gamma1 / 4.0 * (J_plus - J_minus)

                S_inner = p / (rho ** gamma)
                p_ghost = p
                rho_ghost = (p_ghost / S_inner) ** (1.0 / gamma)

        elif n_outgoing == 1:
            if is_inlet:
                J_plus_inner = u + 2.0 * c / gamma1
                J_minus_inner = u - 2.0 * c / gamma1

                c_ghost = c
                u_ghost = u

                S_inner = p / (rho ** gamma)
                p_ghost = p
                rho_ghost = (p_ghost / S_inner) ** (1.0 / gamma)
            else:
                J_plus_far = self.u_far + 2.0 * c_far / gamma1
                J_minus_inner = u - 2.0 * c / gamma1

                J_minus = J_minus_inner
                J_plus = J_plus_far

                u_ghost = 0.5 * (J_plus + J_minus)
                c_ghost = gamma1 / 4.0 * (J_plus - J_minus)

                S_far = self.p_far / (self.rho_far ** gamma)
                p_ghost = self.p_far
                rho_ghost = (p_ghost / S_far) ** (1.0 / gamma)

        else:
            rho_ghost = rho
            u_ghost = u
            p_ghost = p

        rho_ghost = max(rho_ghost, 1e-10)
        p_ghost = max(p_ghost, 1e-10)
        c_ghost = max(c_ghost, 1e-10)

        return self._euler.conservative_from_primitive(rho_ghost, u_ghost, p_ghost)


class ZeroGradientBoundary(BoundaryCondition):
    def __init__(self):
        super().__init__('zero_gradient')

    def apply(self, U, mesh, flux_solver, side):
        if side == 'left':
            return U[:, 0]
        elif side == 'right':
            return U[:, -1]
        else:
            raise ValueError(f"Unknown side: {side}")


class WallBoundary(BoundaryCondition):
    def __init__(self, temperature_wall=None):
        super().__init__('wall')
        self.T_wall = temperature_wall
        self._euler = None

    def apply(self, U, mesh, flux_solver, side):
        if self._euler is None:
            self._euler = EulerFlux(gamma=flux_solver.gamma)

        if side == 'left':
            U_inner = U[:, 0]
        elif side == 'right':
            U_inner = U[:, -1]
        else:
            raise ValueError(f"Unknown side: {side}")

        W_inner = self._euler.primitive_from_conservative(U_inner)
        rho, u, p = W_inner

        if self.T_wall is not None:
            gamma = flux_solver.gamma
            gamma1 = gamma - 1.0
            R_specific = 1.0
            T_inner = p / (rho * R_specific)
            p_ghost = p
            rho_ghost = rho * (self.T_wall / T_inner)
            u_ghost = -u
        else:
            rho_ghost = rho
            u_ghost = -u
            p_ghost = p

        return self._euler.conservative_from_primitive(rho_ghost, u_ghost, p_ghost)


def create_boundary_condition(bc_type, **kwargs):
    if bc_type == 'periodic':
        return PeriodicBoundary()
    elif bc_type == 'reflective':
        return ReflectiveBoundary()
    elif bc_type == 'supersonic_inflow':
        return SupersonicInflow(kwargs['rho'], kwargs['u'], kwargs['p'])
    elif bc_type == 'supersonic_outflow':
        return SupersonicOutflow()
    elif bc_type == 'subsonic_inflow':
        return SubsonicInflow(kwargs['rho0'], kwargs['p0'])
    elif bc_type == 'subsonic_outflow':
        return SubsonicOutflow(kwargs['p_back'])
    elif bc_type == 'non_reflective':
        rho_far = kwargs.get('rho_far', 1.0)
        u_far = kwargs.get('u_far', 0.0)
        p_far = kwargs.get('p_far', 1.0)
        return NonReflectiveBoundary(rho_far=rho_far, u_far=u_far, p_far=p_far)
    elif bc_type == 'farfield_characteristic':
        rho_far = kwargs.get('rho_far', 1.0)
        u_far = kwargs.get('u_far', 0.0)
        p_far = kwargs.get('p_far', 1.0)
        return FarfieldCharacteristicBoundary(rho_far=rho_far, u_far=u_far, p_far=p_far)
    elif bc_type == 'zero_gradient':
        return ZeroGradientBoundary()
    elif bc_type == 'wall':
        temperature_wall = kwargs.get('temperature_wall', None)
        return WallBoundary(temperature_wall)
    else:
        raise ValueError(f"Unknown boundary condition type: {bc_type}")


class BoundaryManager:
    def __init__(self, left_bc, right_bc):
        self.left_bc = left_bc
        self.right_bc = right_bc

    def get_ghost_state(self, U, mesh, flux_solver, side):
        if side == 'left':
            return self.left_bc.apply(U, mesh, flux_solver, side)
        elif side == 'right':
            return self.right_bc.apply(U, mesh, flux_solver, side)
        else:
            raise ValueError(f"Unknown side: {side}")


class BoundaryCondition2D:
    def __init__(self, name):
        self.name = name

    def apply(self, U_inner, edge_normal, mesh, flux_solver, cell_id=-1, edge_idx=-1):
        raise NotImplementedError("Subclasses must implement apply method")


class ZeroGradientBC2D(BoundaryCondition2D):
    def __init__(self):
        super().__init__('zero_gradient_2d')

    def apply(self, U_inner, edge_normal, mesh, flux_solver, cell_id=-1, edge_idx=-1):
        return U_inner.copy()


class SlipWallBC2D(BoundaryCondition2D):
    def __init__(self):
        super().__init__('slip_wall_2d')
        self._euler = None

    def apply(self, U_inner, edge_normal, mesh, flux_solver, cell_id=-1, edge_idx=-1):
        if self._euler is None:
            self._euler = flux_solver

        nx, ny = edge_normal

        W = self._euler.primitive_from_conservative(U_inner)
        rho, u, v, p = W

        u_n = u * nx + v * ny
        u_ghost = u - 2.0 * u_n * nx
        v_ghost = v - 2.0 * u_n * ny

        return self._euler.conservative_from_primitive(rho, u_ghost, p, v_ghost)


class InflowBC2D(BoundaryCondition2D):
    def __init__(self, rho, u, v, p):
        super().__init__('inflow_2d')
        self.rho = rho
        self.u = u
        self.v = v
        self.p = p

    def apply(self, U_inner, edge_normal, mesh, flux_solver, cell_id=-1, edge_idx=-1):
        return flux_solver.conservative_from_primitive(self.rho, self.u, self.p, self.v)


class OutflowBC2D(BoundaryCondition2D):
    def __init__(self, p_back=None):
        super().__init__('outflow_2d')
        self.p_back = p_back
        self._euler = None

    def apply(self, U_inner, edge_normal, mesh, flux_solver, cell_id=-1, edge_idx=-1):
        if self._euler is None:
            self._euler = flux_solver

        if self.p_back is None:
            return U_inner.copy()

        W = self._euler.primitive_from_conservative(U_inner)
        rho, u, v, p = W

        if p < self.p_back:
            rho_ghost = rho * (self.p_back / p) ** (1.0 / flux_solver.gamma)
            return self._euler.conservative_from_primitive(rho_ghost, u, self.p_back, v)
        else:
            return U_inner.copy()


class FarfieldBC2D(BoundaryCondition2D):
    def __init__(self, rho_far=1.0, u_far=0.0, v_far=0.0, p_far=1.0):
        super().__init__('farfield_2d')
        self.rho_far = rho_far
        self.u_far = u_far
        self.v_far = v_far
        self.p_far = p_far
        self._euler = None

    def apply(self, U_inner, edge_normal, mesh, flux_solver, cell_id=-1, edge_idx=-1):
        if self._euler is None:
            self._euler = flux_solver

        nx, ny = edge_normal

        W = self._euler.primitive_from_conservative(U_inner)
        rho, u, v, p = W

        gamma = flux_solver.gamma
        gamma1 = gamma - 1.0

        c = flux_solver.speed_of_sound(rho, p)
        c_far = flux_solver.speed_of_sound(self.rho_far, self.p_far)

        u_n_inner = u * nx + v * ny
        u_n_far = self.u_far * nx + self.v_far * ny

        Mach_inner = u_n_inner / c

        if abs(Mach_inner) >= 1.0:
            if u_n_inner < 0:
                return flux_solver.conservative_from_primitive(
                    self.rho_far, self.u_far, self.p_far, self.v_far
                )
            else:
                return U_inner.copy()

        R_plus_inner = u_n_inner + 2.0 * c / gamma1
        R_minus_far = u_n_far - 2.0 * c_far / gamma1

        u_n_star = 0.5 * (R_plus_inner + R_minus_far)
        c_star = gamma1 / 4.0 * (R_plus_inner - R_minus_far)

        if u_n_star >= 0:
            rho_ghost = rho
            p_ghost = p
        else:
            rho_ghost = self.rho_far
            p_ghost = self.p_far

        u_ghost = u
        v_ghost = v

        return flux_solver.conservative_from_primitive(rho_ghost, u_ghost, p_ghost, v_ghost)


class PeriodicBC2D(BoundaryCondition2D):
    def __init__(self, offset=np.array([1.0, 0.0])):
        super().__init__('periodic_2d')
        self.offset = np.array(offset)

    def apply(self, U_inner, edge_normal, mesh, flux_solver, cell_id=-1, edge_idx=-1):
        return U_inner.copy()


class HangingNodeBC2D(BoundaryCondition2D):
    def __init__(self):
        super().__init__('hanging_node_2d')

    def apply(self, U_inner, edge_normal, mesh, flux_solver, cell_id=-1, edge_idx=-1):
        return U_inner.copy()


class BoundaryManager2D:
    def __init__(self, boundary_regions=None):
        self.regions = boundary_regions if boundary_regions is not None else {}
        self.default_bc = ZeroGradientBC2D()

    def register_boundary(self, name, boundary_condition):
        self.regions[name] = boundary_condition

    def get_ghost_state(self, U_inner, edge_normal, boundary_name, mesh, flux_solver,
                         cell_id=-1, edge_idx=-1):
        if boundary_name in self.regions:
            bc = self.regions[boundary_name]
        else:
            bc = self.default_bc

        return bc.apply(U_inner, edge_normal, mesh, flux_solver, cell_id, edge_idx)


def create_2d_boundary_manager(config=None):
    bm = BoundaryManager2D()

    if config is None:
        return bm

    for name, bc_config in config.items():
        bc_type = bc_config.get('type', 'zero_gradient')

        if bc_type == 'zero_gradient':
            bc = ZeroGradientBC2D()
        elif bc_type == 'slip_wall':
            bc = SlipWallBC2D()
        elif bc_type == 'inflow':
            bc = InflowBC2D(
                bc_config['rho'], bc_config['u'],
                bc_config.get('v', 0.0), bc_config['p']
            )
        elif bc_type == 'outflow':
            bc = OutflowBC2D(bc_config.get('p_back', None))
        elif bc_type == 'farfield':
            bc = FarfieldBC2D(
                bc_config.get('rho_far', 1.0),
                bc_config.get('u_far', 0.0),
                bc_config.get('v_far', 0.0),
                bc_config.get('p_far', 1.0)
            )
        elif bc_type == 'periodic':
            bc = PeriodicBC2D(bc_config.get('offset', [1.0, 0.0]))
        else:
            bc = ZeroGradientBC2D()

        bm.register_boundary(name, bc)

    return bm
