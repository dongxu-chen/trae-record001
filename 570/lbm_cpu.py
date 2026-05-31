import numpy as np
from fluid_simulator import FluidSimulator


class LBM_CPU(FluidSimulator):
    def __init__(self, width=512, height=512, tau=0.6):
        super().__init__(width, height, tau)
        
        self.opposite = [8, 7, 6, 5, 4, 3, 2, 1, 0]
        
        self.use_mrt = True
        self.tau_shear = tau
        self.tau_bulk = 1.0
        
        if self.use_mrt:
            self._init_mrt()
    
    def _init_mrt(self):
        self.M = np.array([
            [1, 1, 1, 1, 1, 1, 1, 1, 1],
            [-4, -1, -1, -1, -1, 2, 2, 2, 2],
            [4, -2, -2, -2, -2, 1, 1, 1, 1],
            [0, 1, 0, -1, 0, 1, -1, -1, 1],
            [0, -2, 0, 2, 0, 1, -1, -1, 1],
            [0, 0, 1, 0, -1, 1, 1, -1, -1],
            [0, 0, -2, 0, 2, 1, 1, -1, -1],
            [0, 1, -1, 1, -1, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 1, -1, 1, -1]
        ], dtype=np.float32)
        
        self.M_inv = np.linalg.inv(self.M)
        
        self.S = np.diag([0, 1.4, 1.4, 0, 1.2, 0, 1.2, 1.0/self.tau_shear, 1.0/self.tau_shear])
        self.S[0, 0] = 0
        self.S[3, 3] = 0
        self.S[5, 5] = 0
        self.S[1, 1] = 1.0 / max(self.tau, 0.51)
        self.S[2, 2] = 1.0 / max(self.tau, 0.51)
        self.S[4, 4] = 1.0 / max(self.tau, 0.51)
        self.S[6, 6] = 1.0 / max(self.tau, 0.51)
    
    def initialize(self):
        self.f = np.ones((self.height, self.width, 9), dtype=np.float32) * self.rho0 / 9.0
        self.f_eq = np.ones_like(self.f)
        self.f_tmp = np.ones_like(self.f)
        
        if self.use_mrt:
            self.m = np.zeros_like(self.f)
            self.m_eq = np.zeros_like(self.f)
    
    def _update_obstacles(self):
        pass
    
    def step(self):
        self.lock()
        try:
            self._compute_macroscopic()
            self._stabilize_macroscopic()
            
            if self.use_mrt:
                self._mrt_collision()
            else:
                self._bgk_collision()
            
            self._streaming()
            self._boundary_conditions()
            
            if self.enable_stabilization:
                self.f = self._stabilize_distribution(self.f)
        finally:
            self.unlock()
    
    def _compute_equilibrium(self):
        u_sq = self.u[:, :, 0]**2 + self.u[:, :, 1]**2
        for i in range(9):
            cu = self.cx[i] * self.u[:, :, 0] + self.cy[i] * self.u[:, :, 1]
            self.f_eq[:, :, i] = self.w[i] * self.rho * (1 + 3*cu + 4.5*cu**2 - 1.5*u_sq)
    
    def _bgk_collision(self):
        self._compute_equilibrium()
        omega = 1.0 / max(self.tau, 0.51)
        self.f = self.f - omega * (self.f - self.f_eq)
    
    def _mrt_collision(self):
        for y in range(self.height):
            for x in range(self.width):
                if not self.obstacles[y, x]:
                    self.m[y, x] = self.M @ self.f[y, x]
        
        self._compute_moments_equilibrium()
        
        for y in range(self.height):
            for x in range(self.width):
                if not self.obstacles[y, x]:
                    self.m[y, x] = self.m[y, x] - self.S @ (self.m[y, x] - self.m_eq[y, x])
                    self.f[y, x] = self.M_inv @ self.m[y, x]
    
    def _compute_moments_equilibrium(self):
        rho = self.rho
        ux = self.u[:, :, 0]
        uy = self.u[:, :, 1]
        u_sq = ux**2 + uy**2
        
        self.m_eq[:, :, 0] = rho
        self.m_eq[:, :, 1] = rho * (-2 + 3*u_sq)
        self.m_eq[:, :, 2] = rho * (1 - 3*u_sq)
        self.m_eq[:, :, 3] = rho * ux
        self.m_eq[:, :, 4] = rho * (-ux)
        self.m_eq[:, :, 5] = rho * uy
        self.m_eq[:, :, 6] = rho * (-uy)
        self.m_eq[:, :, 7] = rho * (ux**2 - uy**2)
        self.m_eq[:, :, 8] = rho * ux * uy
    
    def _streaming(self):
        self.f_tmp[...] = self.f
        for i in range(9):
            self.f[:, :, i] = np.roll(np.roll(self.f_tmp[:, :, i], self.cx[i], axis=1), self.cy[i], axis=0)
    
    def _boundary_conditions(self):
        self._subgrid_bounce_back()
        
        self.f[0, :, [0, 1, 2]] = self.f[0, :, [6, 7, 8]]
        self.f[-1, :, [6, 7, 8]] = self.f[-1, :, [0, 1, 2]]
        
        self.f[:, 0, [0, 3, 6]] = self.f[:, 0, [2, 5, 8]]
        self.f[:, -1, [2, 5, 8]] = self.f[:, -1, [0, 3, 6]]
    
    def _subgrid_bounce_back(self):
        if not self.enable_subgrid:
            for i in range(9):
                self.f[self.obstacles, i] = self.f[self.obstacles, self.opposite[i]]
            return
        
        boundary_mask = (self.obstacle_fraction > 0.0) & (self.obstacle_fraction < 1.0)
        solid_mask = self.obstacle_fraction >= 1.0
        
        for i in range(9):
            opp = self.opposite[i]
            
            self.f[solid_mask, i] = self.f[solid_mask, opp]
            
            if np.any(boundary_mask):
                delta = self.obstacle_fraction[boundary_mask]
                self.f[boundary_mask, i] = (1 - delta) * self.f[boundary_mask, i] + delta * self.f[boundary_mask, opp]
        
        boundary_cells = np.where(boundary_mask)
        for y, x in zip(*boundary_cells):
            delta = self.obstacle_fraction[y, x]
            if delta > 0 and delta < 1:
                neighbor_sum = 0.0
                count = 0
                for i in range(9):
                    nx = x + self.cx[i]
                    ny = y + self.cy[i]
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        if not self.obstacles[ny, nx]:
                            neighbor_sum += np.sum(self.f[ny, nx])
                            count += 1
                if count > 0:
                    rho_near = neighbor_sum / count / 9.0 * 9.0
                    self.rho[y, x] = rho_near
                    self.u[y, x, :] = 0.0
    
    def _compute_macroscopic(self):
        self.rho = np.sum(self.f, axis=2)
        self.rho = np.clip(self.rho, self.min_density, self.max_density)
        
        self.u[:, :, 0] = np.sum(self.f * self.cx[np.newaxis, np.newaxis, :], axis=2) / self.rho
        self.u[:, :, 1] = np.sum(self.f * self.cy[np.newaxis, np.newaxis, :], axis=2) / self.rho
        
        self.u[self.obstacles, :] = 0
        
        if self.enable_stabilization:
            self._stabilize_macroscopic()
    
    def get_velocity(self):
        self.lock()
        try:
            return self.u.copy()
        finally:
            self.unlock()
    
    def get_pressure(self):
        self.lock()
        try:
            return self.rho.copy() / 3.0
        finally:
            self.unlock()
    
    def get_vorticity(self):
        self.lock()
        try:
            ux = self.u[:, :, 0]
            uy = self.u[:, :, 1]
            vorticity = np.gradient(uy, axis=1) - np.gradient(ux, axis=0)
            return vorticity
        finally:
            self.unlock()
    
    def set_tau(self, tau):
        super().set_tau(tau)
        if self.use_mrt:
            omega = 1.0 / max(tau, 0.51)
            self.S[1, 1] = omega
            self.S[2, 2] = omega
            self.S[4, 4] = omega
            self.S[6, 6] = omega
            self.S[7, 7] = omega
            self.S[8, 8] = omega
