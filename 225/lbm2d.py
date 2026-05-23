import numpy as np
import threading
import copy


class ThermalLBM2D:
    def __init__(self, nx=400, ny=100, tau=0.6, force=1e-6, 
                 cfl_max=0.9, auto_adjust=True,
                 enable_temperature=True, tau_T=0.7,
                 prandtl=0.71, rayleigh=1000):
        self.nx = nx
        self.ny = ny
        self.tau = max(tau, 0.51)
        self.force = force
        
        self.cfl_max = cfl_max
        self.auto_adjust = auto_adjust
        self.dt = 1.0
        self.stable = True
        
        self.enable_temperature = enable_temperature
        self.tau_T = max(tau_T, 0.51)
        self.prandtl = prandtl
        self.rayleigh = rayleigh
        self.gravity = 1e-6
        
        self.q = 9
        self.c = np.array([[0, 0],
                           [1, 0], [-1, 0], [0, 1], [0, -1],
                           [1, 1], [-1, -1], [1, -1], [-1, 1]])
        
        self.w = np.array([4/9,
                           1/9, 1/9, 1/9, 1/9,
                           1/36, 1/36, 1/36, 1/36])
        
        self.opposite = [0, 2, 1, 4, 3, 6, 5, 8, 7]
        
        self.f = np.zeros((self.q, self.ny, self.nx))
        self.feq = np.zeros((self.q, self.ny, self.nx))
        self.f_temp = np.zeros((self.q, self.ny, self.nx))
        
        self.rho = np.ones((self.ny, self.nx))
        self.u = np.zeros((2, self.ny, self.nx))
        
        self.obstacle = np.zeros((self.ny, self.nx), dtype=bool)
        self.obstacle_temp = None
        
        if self.enable_temperature:
            self.g = np.zeros((self.q, self.ny, self.nx))
            self.geq = np.zeros((self.q, self.ny, self.nx))
            self.g_temp = np.zeros((self.q, self.ny, self.nx))
            self.T = np.ones((self.ny, self.nx)) * 0.5
        
        self.step_count = 0
        self.lock = threading.Lock()
        
        self.initialize()
    
    def initialize(self):
        for i in range(self.q):
            self.f[i] = self.w[i] * self.rho
        
        if self.enable_temperature:
            for i in range(self.q):
                self.g[i] = self.w[i] * self.T
    
    def equilibrium(self):
        u_sq = self.u[0]**2 + self.u[1]**2
        for i in range(self.q):
            cu = 3 * (self.c[i, 0] * self.u[0] + self.c[i, 1] * self.u[1])
            self.feq[i] = self.rho * self.w[i] * (1 + cu + 0.5 * cu**2 - 1.5 * u_sq)
    
    def equilibrium_T(self):
        u_sq = self.u[0]**2 + self.u[1]**2
        for i in range(self.q):
            cu = 3 * (self.c[i, 0] * self.u[0] + self.c[i, 1] * self.u[1])
            self.geq[i] = self.T * self.w[i] * (1 + cu + 0.5 * cu**2 - 1.5 * u_sq)
    
    def collision(self):
        self.equilibrium()
        self.f = (1 - 1/self.tau) * self.f + (1/self.tau) * self.feq
        
        if self.enable_temperature:
            buoyancy = self.gravity * (self.T - 0.5)
            self.u[1] += buoyancy * (1 - 0.5/self.tau) / self.rho
        
        self.u[0] += self.force * (1 - 0.5/self.tau) / self.rho
    
    def collision_T(self):
        if not self.enable_temperature:
            return
        self.equilibrium_T()
        self.g = (1 - 1/self.tau_T) * self.g + (1/self.tau_T) * self.geq
    
    def stream_and_bounce(self):
        np.copyto(self.f_temp, self.f)
        
        for i in range(1, self.q):
            dx, dy = self.c[i]
            
            rolled = np.roll(self.f_temp[i], (dy, dx), axis=(0, 1))
            
            mask_fluid = ~self.obstacle
            self.f[i, mask_fluid] = rolled[mask_fluid]
            
            if dx != 0 or dy != 0:
                mask_bounce = np.roll(self.obstacle, (-dy, -dx), axis=(0, 1))
                self.f[self.opposite[i], mask_bounce] = self.f_temp[i, mask_bounce]
    
    def stream_and_bounce_T(self):
        if not self.enable_temperature:
            return
        
        np.copyto(self.g_temp, self.g)
        
        for i in range(1, self.q):
            dx, dy = self.c[i]
            
            rolled = np.roll(self.g_temp[i], (dy, dx), axis=(0, 1))
            
            mask_fluid = ~self.obstacle
            self.g[i, mask_fluid] = rolled[mask_fluid]
            
            if dx != 0 or dy != 0:
                mask_bounce = np.roll(self.obstacle, (-dy, -dx), axis=(0, 1))
                self.g[self.opposite[i], mask_bounce] = self.g_temp[i, mask_bounce]
    
    def boundaries(self):
        self.f[:, 0, :] = self.f[:, 1, :]
        self.f[:, -1, :] = self.f[:, -2, :]
        
        if self.enable_temperature:
            self.g[:, 0, :] = self.g[:, 1, :]
            self.g[:, -1, :] = self.g[:, -2, :]
    
    def compute_macroscopic(self):
        self.rho = np.sum(self.f, axis=0)
        
        self.u[0] = np.sum(self.c[:, 0].reshape(-1, 1, 1) * self.f, axis=0) / self.rho
        self.u[1] = np.sum(self.c[:, 1].reshape(-1, 1, 1) * self.f, axis=0) / self.rho
        
        self.u[:, 0, :] = 0
        self.u[:, -1, :] = 0
        
        self.u[:, self.obstacle] = 0
        
        if self.enable_temperature:
            self.T = np.sum(self.g, axis=0)
            self.T[self.obstacle] = 0
            if self.obstacle_temp is not None:
                self.T[self.obstacle] = self.obstacle_temp
    
    def check_cfl(self):
        max_u = np.max(np.sqrt(self.u[0]**2 + self.u[1]**2))
        cfl = max_u * self.dt
        
        self.stable = cfl <= self.cfl_max
        
        if self.auto_adjust and not self.stable and max_u > 0:
            self.dt = self.cfl_max / max_u
            self.stable = True
        
        return cfl, self.stable
    
    def check_tau_stability(self):
        min_tau = 0.51
        max_tau = 2.0
        
        if self.tau < min_tau:
            self.tau = min_tau
            return False
        elif self.tau > max_tau:
            self.tau = max_tau
            return False
        return True
    
    def step(self):
        with self.lock:
            self.collision()
            if self.enable_temperature:
                self.collision_T()
            
            self.stream_and_bounce()
            if self.enable_temperature:
                self.stream_and_bounce_T()
            
            self.boundaries()
            self.compute_macroscopic()
            
            cfl, cfl_ok = self.check_cfl()
            tau_ok = self.check_tau_stability()
            
            self.step_count += 1
            
            return {
                'step': self.step_count,
                'cfl': cfl,
                'dt': self.dt,
                'tau_ok': tau_ok,
                'stable': cfl_ok and tau_ok
            }
    
    def get_field_data(self):
        with self.lock:
            data = {
                'u': copy.deepcopy(self.u),
                'rho': copy.deepcopy(self.rho),
                'obstacle': copy.deepcopy(self.obstacle),
                'step': self.step_count,
                'dt': self.dt
            }
            if self.enable_temperature:
                data['T'] = copy.deepcopy(self.T)
            return data
    
    def get_velocity(self):
        with self.lock:
            return self.u.copy()
    
    def get_temperature(self):
        if not self.enable_temperature:
            return None
        with self.lock:
            return self.T.copy()
    
    def get_vorticity(self):
        with self.lock:
            u, v = self.u[0], self.u[1]
        dvdx = np.gradient(v, axis=1)
        dudy = np.gradient(u, axis=0)
        return dvdx - dudy
    
    def add_circle(self, cx, cy, r, temperature=None):
        y, x = np.mgrid[0:self.ny, 0:self.nx]
        mask = (x - cx)**2 + (y - cy)**2 < r**2
        self.obstacle[mask] = True
        
        if temperature is not None and self.enable_temperature:
            if self.obstacle_temp is None:
                self.obstacle_temp = np.zeros((self.ny, self.nx))
            self.obstacle_temp[mask] = temperature
    
    def add_rectangle(self, x0, y0, width, height, temperature=None):
        self.obstacle[y0:y0+height, x0:x0+width] = True
        
        if temperature is not None and self.enable_temperature:
            if self.obstacle_temp is None:
                self.obstacle_temp = np.zeros((self.ny, self.nx))
            self.obstacle_temp[y0:y0+height, x0:x0+width] = temperature
    
    def set_temperature_boundary(self, bottom_temp=None, top_temp=None):
        if not self.enable_temperature:
            return
        if bottom_temp is not None:
            self.T[0, :] = bottom_temp
        if top_temp is not None:
            self.T[-1, :] = top_temp
    
    def set_reynolds(self, re, char_length):
        re_max = 5000.0
        re_safe = min(re, re_max)
        
        if re > re_max:
            print(f"Warning: Reynolds {re:.1f} exceeds stability limit {re_max}.")
            print(f"Clamped to {re_safe:.1f} for numerical stability.")
        
        u_avg = re_safe * self.get_viscosity() / char_length
        self.force = u_avg * self.rho.mean() * 8 * self.tau / (self.ny**2)
    
    def get_viscosity(self):
        return (self.tau - 0.5) / 3.0
    
    def get_thermal_diffusivity(self):
        if not self.enable_temperature:
            return 0
        return (self.tau_T - 0.5) / 3.0
    
    def get_prandtl(self):
        return self.get_viscosity() / max(self.get_thermal_diffusivity(), 1e-10)
    
    def get_reynolds(self, char_length):
        u_avg = np.sqrt(np.mean(self.u[0]**2 + self.u[1]**2))
        return u_avg * char_length / self.get_viscosity()


LBM2D = ThermalLBM2D


class ParticleTracer:
    def __init__(self, lbm, n_particles=500):
        self.lbm = lbm
        self.n_particles = n_particles
        self.positions = np.zeros((n_particles, 2))
        self.velocities = np.zeros((n_particles, 2))
        self.history = []
        self.max_history = 200
        self.lock = threading.Lock()
        self.initialize_particles()
    
    def initialize_particles(self):
        with self.lbm.lock:
            fluid_mask = ~self.lbm.obstacle
            fluid_y, fluid_x = np.where(fluid_mask)
            
            if len(fluid_x) < self.n_particles:
                idx = np.random.choice(len(fluid_x), self.n_particles, replace=True)
            else:
                idx = np.random.choice(len(fluid_x), self.n_particles, replace=False)
            
            self.positions[:, 0] = fluid_x[idx]
            self.positions[:, 1] = fluid_y[idx]
            
            for i in range(self.n_particles):
                x, y = int(self.positions[i, 0]), int(self.positions[i, 1])
                x = np.clip(x, 0, self.lbm.nx - 1)
                y = np.clip(y, 0, self.lbm.ny - 1)
                self.velocities[i, 0] = self.lbm.u[0, y, x]
                self.velocities[i, 1] = self.lbm.u[1, y, x]
    
    def advect(self, dt=1.0):
        with self.lbm.lock:
            for i in range(self.n_particles):
                x, y = self.positions[i]
                
                x0 = int(np.floor(x))
                y0 = int(np.floor(y))
                x1 = x0 + 1
                y1 = y0 + 1
                
                x0 = np.clip(x0, 0, self.lbm.nx - 1)
                x1 = np.clip(x1, 0, self.lbm.nx - 1)
                y0 = np.clip(y0, 0, self.lbm.ny - 1)
                y1 = np.clip(y1, 0, self.lbm.ny - 1)
                
                fx = x - np.floor(x)
                fy = y - np.floor(y)
                
                u00 = self.lbm.u[0, y0, x0]
                u10 = self.lbm.u[0, y0, x1]
                u01 = self.lbm.u[0, y1, x0]
                u11 = self.lbm.u[0, y1, x1]
                
                v00 = self.lbm.u[1, y0, x0]
                v10 = self.lbm.u[1, y0, x1]
                v01 = self.lbm.u[1, y1, x0]
                v11 = self.lbm.u[1, y1, x1]
                
                u = (1-fx)*(1-fy)*u00 + fx*(1-fy)*u10 + (1-fx)*fy*u01 + fx*fy*u11
                v = (1-fx)*(1-fy)*v00 + fx*(1-fy)*v10 + (1-fx)*fy*v01 + fx*fy*v11
                
                self.positions[i, 0] += u * dt
                self.positions[i, 1] += v * dt
                
                self.velocities[i, 0] = u
                self.velocities[i, 1] = v
                
                if self.positions[i, 0] < 0:
                    self.positions[i, 0] = self.lbm.nx - 1 + self.positions[i, 0]
                elif self.positions[i, 0] >= self.lbm.nx:
                    self.positions[i, 0] = self.positions[i, 0] - self.lbm.nx
                
                if self.positions[i, 1] < 0:
                    self.positions[i, 1] = 1
                elif self.positions[i, 1] >= self.lbm.ny:
                    self.positions[i, 1] = self.lbm.ny - 2
                
                px, py = int(self.positions[i, 0]), int(self.positions[i, 1])
                px = np.clip(px, 0, self.lbm.nx - 1)
                py = np.clip(py, 0, self.lbm.ny - 1)
                
                if self.lbm.obstacle[py, px]:
                    self.reset_particle(i)
    
    def reset_particle(self, i):
        fluid_mask = ~self.lbm.obstacle
        fluid_y, fluid_x = np.where(fluid_mask)
        if len(fluid_x) > 0:
            idx = np.random.choice(len(fluid_x))
            self.positions[i, 0] = fluid_x[idx]
            self.positions[i, 1] = fluid_y[idx]
    
    def update(self, dt=1.0):
        with self.lock:
            self.advect(dt)
            
            self.history.append(self.positions.copy())
            if len(self.history) > self.max_history:
                self.history.pop(0)
    
    def get_positions(self):
        with self.lock:
            return self.positions.copy()
    
    def get_history(self):
        with self.lock:
            if len(self.history) == 0:
                return None
            return np.array(self.history)
