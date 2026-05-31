import numpy as np


class MultiphaseLBM:
    def __init__(self, width=512, height=512, tau=0.6):
        self.width = width
        self.height = height
        self.tau = tau
        
        self.w = np.array([1/36, 1/9, 1/36, 1/9, 4/9, 1/9, 1/36, 1/9, 1/36], dtype=np.float32)
        self.cx = np.array([-1, 0, 1, -1, 0, 1, -1, 0, 1], dtype=np.int32)
        self.cy = np.array([-1, -1, -1, 0, 0, 0, 1, 1, 1], dtype=np.int32)
        self.opposite = [8, 7, 6, 5, 4, 3, 2, 1, 0]
        
        self.rho1 = 1.0
        self.rho2 = 0.1
        self.sigma = 0.01
        
        self.f1 = np.ones((height, width, 9), dtype=np.float32) * self.rho1 / 9.0
        self.f2 = np.ones((height, width, 9), dtype=np.float32) * self.rho2 / 9.0
        self.f1_eq = np.ones_like(self.f1)
        self.f2_eq = np.ones_like(self.f2)
        self.f_tmp = np.ones_like(self.f1)
        
        self.rho = np.ones((height, width), dtype=np.float32)
        self.u = np.zeros((height, width, 2), dtype=np.float32)
        self.phi = np.zeros((height, width), dtype=np.float32)
        
        self.phase1 = np.ones((height, width), dtype=np.float32)
        
        self.obstacles = np.zeros((height, width), dtype=bool)
        
        self.interface_thickness = 3.0
        self.relaxation_phi = 0.7
        
        self._initialize_phase()
    
    def _initialize_phase(self):
        y, x = np.ogrid[:self.height, :self.width]
        self.phase1 = (x < self.width // 2).astype(np.float32)
        self._update_phi()
    
    def _update_phi(self):
        self.phi = self.phase1 * (1 - self.phase1)
    
    def set_droplet(self, cx, cy, radius):
        y, x = np.ogrid[:self.height, :self.width]
        dist = np.sqrt((x - cx)**2 + (y - cy)**2)
        self.phase1[dist <= radius] = 0.0
        self._update_phi()
    
    def add_liquid_column(self, x0, x1):
        y, x = np.ogrid[:self.height, :self.width]
        mask = (x >= x0) & (x <= x1)
        self.phase1[mask] = 1.0
        self._update_phi()
    
    def reset(self):
        self._initialize_phase()
        self.f1 = np.ones((self.height, self.width, 9), dtype=np.float32) * self.rho1 / 9.0
        self.f2 = np.ones((self.height, self.width, 9), dtype=np.float32) * self.rho2 / 9.0
        self.u.fill(0)
    
    def step(self):
        self._compute_macroscopic()
        self._compute_equilibrium()
        self._collision()
        self._streaming()
        self._boundary_conditions()
        self._update_phase()
        self._update_phi()
    
    def _compute_macroscopic(self):
        rho1 = np.sum(self.f1, axis=2)
        rho2 = np.sum(self.f2, axis=2)
        
        self.rho = rho1 + rho2
        self.rho = np.clip(self.rho, 0.1, 10.0)
        
        ux1 = np.sum(self.f1 * self.cx[np.newaxis, np.newaxis, :], axis=2)
        uy1 = np.sum(self.f1 * self.cy[np.newaxis, np.newaxis, :], axis=2)
        ux2 = np.sum(self.f2 * self.cx[np.newaxis, np.newaxis, :], axis=2)
        uy2 = np.sum(self.f2 * self.cy[np.newaxis, np.newaxis, :], axis=2)
        
        self.u[:, :, 0] = (ux1 + ux2) / (self.rho + 1e-10)
        self.u[:, :, 1] = (uy1 + uy2) / (self.rho + 1e-10)
        
        vel_mag = np.sqrt(self.u[:, :, 0]**2 + self.u[:, :, 1]**2)
        mask = vel_mag > 0.5
        scale = np.ones_like(vel_mag)
        scale[mask] = 0.5 / (vel_mag[mask] + 1e-10)
        self.u[:, :, 0] *= scale
        self.u[:, :, 1] *= scale
        
        self.u[self.obstacles, :] = 0
    
    def _compute_equilibrium(self):
        u_sq = self.u[:, :, 0]**2 + self.u[:, :, 1]**2
        
        grad_x, grad_y = self._compute_surface_force()
        
        rho1 = self.phase1 * self.rho
        rho2 = (1 - self.phase1) * self.rho
        
        for i in range(9):
            cu = self.cx[i] * self.u[:, :, 0] + self.cy[i] * self.u[:, :, 1]
            
            Fx = self.sigma * self.phi * grad_x
            Fy = self.sigma * self.phi * grad_y
            
            cu += self.cx[i] * Fx + self.cy[i] * Fy
            
            self.f1_eq[:, :, i] = self.w[i] * rho1 * (1 + 3*cu + 4.5*cu**2 - 1.5*u_sq)
            self.f2_eq[:, :, i] = self.w[i] * rho2 * (1 + 3*cu + 4.5*cu**2 - 1.5*u_sq)
    
    def _compute_surface_force(self):
        grad_x = np.gradient(self.phase1, axis=1)
        grad_y = np.gradient(self.phase1, axis=0)
        
        mag = np.sqrt(grad_x**2 + grad_y**2) + 1e-10
        grad_x /= mag
        grad_y /= mag
        
        laplacian = np.gradient(np.gradient(self.phase1, axis=1), axis=1) + \
                    np.gradient(np.gradient(self.phase1, axis=0), axis=0)
        
        return laplacian * grad_x, laplacian * grad_y
    
    def _collision(self):
        omega = 1.0 / max(self.tau, 0.51)
        self.f1 = self.f1 - omega * (self.f1 - self.f1_eq)
        self.f2 = self.f2 - omega * (self.f2 - self.f2_eq)
    
    def _streaming(self):
        self.f_tmp[...] = self.f1
        for i in range(9):
            self.f1[:, :, i] = np.roll(np.roll(self.f_tmp[:, :, i], self.cx[i], axis=1), self.cy[i], axis=0)
        
        self.f_tmp[...] = self.f2
        for i in range(9):
            self.f2[:, :, i] = np.roll(np.roll(self.f_tmp[:, :, i], self.cx[i], axis=1), self.cy[i], axis=0)
    
    def _boundary_conditions(self):
        for i in range(9):
            self.f1[self.obstacles, i] = self.f1[self.obstacles, self.opposite[i]]
            self.f2[self.obstacles, i] = self.f2[self.obstacles, self.opposite[i]]
        
        for i in [0, 1, 2]:
            self.f1[0, :, i] = self.f1[0, :, self.opposite[i]]
            self.f2[0, :, i] = self.f2[0, :, self.opposite[i]]
        for i in [6, 7, 8]:
            self.f1[-1, :, i] = self.f1[-1, :, self.opposite[i]]
            self.f2[-1, :, i] = self.f2[-1, :, self.opposite[i]]
        
        for i in [0, 3, 6]:
            self.f1[:, 0, i] = self.f1[:, 0, self.opposite[i]]
            self.f2[:, 0, i] = self.f2[:, 0, self.opposite[i]]
        for i in [2, 5, 8]:
            self.f1[:, -1, i] = self.f1[:, -1, self.opposite[i]]
            self.f2[:, -1, i] = self.f2[:, -1, self.opposite[i]]
    
    def _update_phase(self):
        rho1 = np.sum(self.f1, axis=2)
        rho2 = np.sum(self.f2, axis=2)
        
        total = rho1 + rho2 + 1e-10
        new_phase1 = rho1 / total
        
        alpha = 0.5
        self.phase1 = alpha * self.phase1 + (1 - alpha) * new_phase1
        
        self.phase1 = np.clip(self.phase1, 0.0, 1.0)
        
        self.phase1[self.obstacles] = 0.5
    
    def get_phase(self):
        return self.phase1.copy()
    
    def get_velocity(self):
        return self.u.copy()
    
    def get_pressure(self):
        return self.rho.copy() / 3.0
    
    def get_interface(self):
        return self.phi.copy()
    
    def set_inflow(self, ux, uy, phase=1.0):
        self.u[:, 0, 0] = ux
        self.u[:, 0, 1] = uy
        self.phase1[:, 0] = phase
    
    def set_obstacles(self, obstacles):
        self.obstacles = obstacles.copy()
